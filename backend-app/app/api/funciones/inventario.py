"""
Lógica de inventario físico:
- parsear la planilla ID | Accesorio | Sistema | Fisico (la que baja /stock/export-por-exclusion)
- calcular discrepancias valorizadas (sobrante estimado)
- armar los Excel de reporte y de registro
"""
from dataclasses import dataclass, field
from io import BytesIO
from typing import Optional

import openpyxl
from fastapi import HTTPException, status
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlmodel import Session, select

from app.db.models import Accesorio


# ── Tipos ────────────────────────────────────────────────────────────────────

@dataclass
class FilaInventario:
    fila_excel: int
    accesorio_id: int
    sistema: int
    fisico: int


@dataclass
class Discrepancia:
    accesorio_id: int
    nombre: str
    precio: int
    sistema: int
    fisico: int

    @property
    def diferencia(self) -> int:
        """Delta a aplicar al stock (fisico - sistema)."""
        return self.fisico - self.sistema

    @property
    def faltan(self) -> int:
        return max(self.sistema - self.fisico, 0)

    @property
    def sobran(self) -> int:
        return max(self.fisico - self.sistema, 0)

    @property
    def sobrante_estimado(self) -> int:
        # Falta mercadería -> se espera ese dinero de más en caja (positivo).
        # Sobra mercadería -> se espera ese dinero de menos en caja (negativo).
        return (self.sistema - self.fisico) * self.precio


@dataclass
class ResultadoInventario:
    discrepancias: list[Discrepancia] = field(default_factory=list)
    productos_contados: int = 0
    sin_diferencias: int = 0

    @property
    def sobrante_estimado_total(self) -> int:
        return sum(d.sobrante_estimado for d in self.discrepancias)


# ── Parseo ───────────────────────────────────────────────────────────────────

def _a_entero(valor) -> Optional[int]:
    """Convierte una celda a int. None/'' -> None. Lanza ValueError si no es entero."""
    if valor is None:
        return None
    if isinstance(valor, bool):
        raise ValueError
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        if not valor.is_integer():
            raise ValueError
        return int(valor)
    texto = str(valor).strip()
    if texto == "":
        return None
    numero = float(texto.replace(",", "."))
    if not numero.is_integer():
        raise ValueError
    return int(numero)


def parsear_planilla(contenido: bytes) -> list[FilaInventario]:
    """
    Lee la planilla de inventario. Ubica la fila de encabezado buscando "ID" en
    la columna A y toma las columnas por nombre (Sistema / Fisico).
    Fisico vacío se considera 0. Junta todos los errores en un único 400.
    """
    try:
        wb = openpyxl.load_workbook(BytesIO(contenido), data_only=True, read_only=True)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No se pudo leer el archivo. Tiene que ser un .xlsx")

    ws = wb.worksheets[0]
    filas = list(ws.iter_rows(values_only=True))

    fila_header = None
    for idx, fila in enumerate(filas):
        if fila and fila[0] is not None and str(fila[0]).strip().upper() == "ID":
            fila_header = idx
            break
    if fila_header is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No se encontró el encabezado (celda 'ID' en la columna A)")

    encabezados = [str(c).strip().upper() if c is not None else "" for c in filas[fila_header]]
    try:
        col_sistema = encabezados.index("SISTEMA")
        col_fisico = encabezados.index("FISICO") if "FISICO" in encabezados else encabezados.index("FÍSICO")
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La planilla tiene que tener las columnas 'Sistema' y 'Fisico'")

    errores: list[str] = []
    resultado: list[FilaInventario] = []
    vistos: dict[int, int] = {}

    for idx in range(fila_header + 1, len(filas)):
        fila = filas[idx]
        num = idx + 1  # número de fila en Excel
        celdas = list(fila) + [None] * (max(col_sistema, col_fisico) + 1 - len(fila))
        raw_id, raw_sistema, raw_fisico = celdas[0], celdas[col_sistema], celdas[col_fisico]

        if all(c is None or str(c).strip() == "" for c in celdas):
            continue  # fila vacía

        try:
            accesorio_id = _a_entero(raw_id)
        except ValueError:
            accesorio_id = None
        if accesorio_id is None:
            errores.append(f"Fila {num}: ID inválido ({raw_id!r})")
            continue

        try:
            sistema = _a_entero(raw_sistema)
        except ValueError:
            sistema = None
        if sistema is None:
            errores.append(f"Fila {num}: Sistema vacío o inválido ({raw_sistema!r})")
            continue

        try:
            fisico = _a_entero(raw_fisico)
        except ValueError:
            errores.append(f"Fila {num}: Fisico inválido ({raw_fisico!r})")
            continue
        if fisico is None:
            fisico = 0
        if fisico < 0:
            errores.append(f"Fila {num}: Fisico no puede ser negativo ({fisico})")
            continue

        if accesorio_id in vistos:
            errores.append(f"Fila {num}: ID {accesorio_id} repetido (ya está en la fila {vistos[accesorio_id]})")
            continue
        vistos[accesorio_id] = num

        resultado.append(FilaInventario(num, accesorio_id, sistema, fisico))

    if errores:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Errores en la planilla:\n" + "\n".join(errores))
    if not resultado:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La planilla no tiene productos")

    return resultado


# ── Cálculo ──────────────────────────────────────────────────────────────────

def calcular_discrepancias(session: Session, filas: list[FilaInventario]) -> ResultadoInventario:
    """Trae los accesorios en una sola query y calcula las diferencias valorizadas. Ademas verifica que los ids existan"""
    ids = [f.accesorio_id for f in filas]
    accesorios = {
        a.accesorio_id: a
        for a in session.exec(select(Accesorio).where(Accesorio.accesorio_id.in_(ids))).all()  # type: ignore
    }

    inexistentes = [f"Fila {f.fila_excel}: ID {f.accesorio_id}" for f in filas if f.accesorio_id not in accesorios]
    if inexistentes:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Accesorios inexistentes:\n" + "\n".join(inexistentes),
        )

    resultado = ResultadoInventario(productos_contados=len(filas))
    for f in filas:
        if f.sistema == f.fisico:
            resultado.sin_diferencias += 1
            continue
        acc = accesorios[f.accesorio_id]
        resultado.discrepancias.append(Discrepancia(
            accesorio_id=f.accesorio_id,
            nombre=acc.nombre,
            precio=acc.precio,
            sistema=f.sistema,
            fisico=f.fisico,
        ))
    return resultado


# ── Excel ────────────────────────────────────────────────────────────────────

_DARK = "1A1A2E"
_THIN = Side(style="thin", color="BFBFBF")
_BORDE = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_CENTRO = Alignment(horizontal="center", vertical="center")
_FMT_MONEDA = '"$" #,##0;-"$" #,##0'

_FONT_HDR = Font(bold=True, color="FFFFFF")
_FILL_HDR = PatternFill("solid", fgColor=_DARK)
# Faltan en rojo, Sobran en azul
_FONT_FALTAN = Font(bold=True, color="C00000")
_FILL_FALTAN = PatternFill("solid", fgColor="FDE2E2")
_FILL_FALTAN_HDR = PatternFill("solid", fgColor="C00000")
_FONT_SOBRAN = Font(bold=True, color="1F4E9C")
_FILL_SOBRAN = PatternFill("solid", fgColor="DDEBF7")
_FILL_SOBRAN_HDR = PatternFill("solid", fgColor="1F4E9C")
_FILL_TOTAL = PatternFill("solid", fgColor="D9D9D9")


def _escribir_titulo_y_meta(ws, titulo: str, meta: list[tuple[str, object]], ancho: int) -> int:
    """Escribe título + metadatos. Devuelve la próxima fila libre."""
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ancho)
    c = ws.cell(row=1, column=1, value=titulo)
    c.font = Font(bold=True, size=14, color="FFFFFF")
    c.fill = _FILL_HDR
    c.alignment = _CENTRO
    ws.row_dimensions[1].height = 22

    r = 2
    for etiqueta, valor in meta:
        ws.cell(row=r, column=1, value=etiqueta).font = Font(bold=True)
        c = ws.cell(row=r, column=2, value=valor)
        if isinstance(valor, int) and "sobrante" in etiqueta.lower():
            c.number_format = _FMT_MONEDA
        r += 1
    return r + 1


def _encabezado(ws, fila: int, titulos: list[str], col_faltan: int, col_sobran: int) -> None:
    for col, titulo in enumerate(titulos, start=1):
        c = ws.cell(row=fila, column=col, value=titulo)
        c.font = _FONT_HDR
        c.alignment = _CENTRO
        c.border = _BORDE
        if col == col_faltan:
            c.fill = _FILL_FALTAN_HDR
        elif col == col_sobran:
            c.fill = _FILL_SOBRAN_HDR
        else:
            c.fill = _FILL_HDR


def _pintar_faltan_sobran(ws, fila: int, col_faltan: int, col_sobran: int) -> None:
    c = ws.cell(row=fila, column=col_faltan)
    c.font = _FONT_FALTAN
    c.fill = _FILL_FALTAN
    c = ws.cell(row=fila, column=col_sobran)
    c.font = _FONT_SOBRAN
    c.fill = _FILL_SOBRAN


def _a_bytes(wb) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_reporte_excel(resultado: ResultadoInventario, meta: list[tuple[str, object]]) -> bytes:
    """
    Reporte de discrepancias: solo productos con diferencia.
    Columnas: ID | Producto | Sistema | Fisico | Faltan | Sobran | Sobrante estimado
    Al final, fila SOBRANTE ESTIMADO TOTAL.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Discrepancias"  # type: ignore

    titulos = ["ID", "Producto", "Sistema", "Fisico", "Faltan", "Sobran", "Sobrante estimado"]
    COL_FALTAN, COL_SOBRAN, COL_SOBRANTE = 5, 6, 7

    meta_completa = list(meta) + [
        ("Productos contados:", resultado.productos_contados),
        ("Sin diferencias:", resultado.sin_diferencias),
        ("Con diferencias:", len(resultado.discrepancias)),
    ]
    r = _escribir_titulo_y_meta(ws, "REPORTE DE INVENTARIO", meta_completa, len(titulos))

    _encabezado(ws, r, titulos, COL_FALTAN, COL_SOBRAN)
    fila_header = r
    r += 1

    for d in sorted(resultado.discrepancias, key=lambda x: x.nombre):
        valores = [d.accesorio_id, d.nombre, d.sistema, d.fisico,
                   d.faltan or None, d.sobran or None, d.sobrante_estimado]
        for col, v in enumerate(valores, start=1):
            c = ws.cell(row=r, column=col, value=v)
            c.border = _BORDE
        ws.cell(row=r, column=COL_SOBRANTE).number_format = _FMT_MONEDA
        _pintar_faltan_sobran(ws, r, COL_FALTAN, COL_SOBRAN)
        r += 1

    # Totales
    ws.cell(row=r, column=1, value="SOBRANTE ESTIMADO TOTAL")
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    ws.cell(row=r, column=COL_FALTAN, value=sum(d.faltan for d in resultado.discrepancias))
    ws.cell(row=r, column=COL_SOBRAN, value=sum(d.sobran for d in resultado.discrepancias))
    ws.cell(row=r, column=COL_SOBRANTE, value=resultado.sobrante_estimado_total).number_format = _FMT_MONEDA
    for col in range(1, len(titulos) + 1):
        c = ws.cell(row=r, column=col)
        c.font = Font(bold=True)
        c.fill = _FILL_TOTAL
        c.border = _BORDE
    ws.cell(row=r, column=COL_FALTAN).font = _FONT_FALTAN
    ws.cell(row=r, column=COL_SOBRAN).font = _FONT_SOBRAN

    for col, ancho in enumerate([10, 45, 11, 11, 11, 11, 20], start=1):
        ws.column_dimensions[get_column_letter(col)].width = ancho
    ws.freeze_panes = f"A{fila_header + 1}"

    return _a_bytes(wb)


def build_registro_excel(
    movimientos: list[tuple[int, str, int, int, int]],
    meta: list[tuple[str, object]],
) -> bytes:
    """
    Registro de un inventario aplicado: un renglón por movimiento AJUSTE.
    movimientos: (accesorio_id, nombre, stock_anterior, cantidad, stock_nuevo)
    Columnas: ID | Producto | Stock anterior | Faltan | Sobran | Stock nuevo
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ajustes"  # type: ignore

    titulos = ["ID", "Producto", "Stock anterior", "Faltan", "Sobran", "Stock nuevo"]
    COL_FALTAN, COL_SOBRAN = 4, 5

    r = _escribir_titulo_y_meta(ws, "REGISTRO DE INVENTARIO", meta, len(titulos))
    _encabezado(ws, r, titulos, COL_FALTAN, COL_SOBRAN)
    fila_header = r
    r += 1

    total_faltan = total_sobran = 0
    for accesorio_id, nombre, anterior, cantidad, nuevo in movimientos:
        faltan = -cantidad if cantidad < 0 else 0
        sobran = cantidad if cantidad > 0 else 0
        total_faltan += faltan
        total_sobran += sobran
        valores = [accesorio_id, nombre, anterior, faltan or None, sobran or None, nuevo]
        for col, v in enumerate(valores, start=1):
            ws.cell(row=r, column=col, value=v).border = _BORDE
        _pintar_faltan_sobran(ws, r, COL_FALTAN, COL_SOBRAN)
        r += 1

    ws.cell(row=r, column=1, value="TOTAL")
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    ws.cell(row=r, column=COL_FALTAN, value=total_faltan)
    ws.cell(row=r, column=COL_SOBRAN, value=total_sobran)
    for col in range(1, len(titulos) + 1):
        c = ws.cell(row=r, column=col)
        c.font = Font(bold=True)
        c.fill = _FILL_TOTAL
        c.border = _BORDE
    ws.cell(row=r, column=COL_FALTAN).font = _FONT_FALTAN
    ws.cell(row=r, column=COL_SOBRAN).font = _FONT_SOBRAN

    for col, ancho in enumerate([10, 45, 15, 11, 11, 15], start=1):
        ws.column_dimensions[get_column_letter(col)].width = ancho
    ws.freeze_panes = f"A{fila_header + 1}"

    return _a_bytes(wb)
