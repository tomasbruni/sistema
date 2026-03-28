// ─── pdfLote.js ──────────────────────────────────────────────────────────────
// Genera PDFs para ingresos y transferencias de lote usando jsPDF + autotable
// npm install jspdf jspdf-autotable
// ─────────────────────────────────────────────────────────────────────────────

import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'

// ─── PALETA ──────────────────────────────────────────────────────────────────
const COLOR_HEADER  = [26, 26, 46]   // #1a1a2e
const COLOR_ALT_ROW = [245, 245, 255]
const COLOR_TEXT    = [30, 30, 30]

// ─── HELPERS ─────────────────────────────────────────────────────────────────
const formatFechaLocal = (iso) =>
  new Date(iso).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })

const formatPrecio = (n) => `$${Number(n).toLocaleString('es-AR')}`

// Encabezado genérico
function _encabezado(doc, { titulo, subtitulo, fecha }) {
  const pageW = doc.internal.pageSize.getWidth()

  // Banda superior
  doc.setFillColor(...COLOR_HEADER)
  doc.rect(0, 0, pageW, 28, 'F')

  // Marca
  doc.setFont('helvetica', 'bold').setFontSize(14)
  doc.setTextColor(255, 255, 255)
  doc.text('CELULANDIA', 14, 12)

  // Título y fecha
  doc.setFont('helvetica', 'normal').setFontSize(10)
  doc.text(titulo, 14, 21)
  doc.setFontSize(9)
  doc.text(fecha, pageW - 14, 21, { align: 'right' })

  // Subtítulo
  doc.setFont('helvetica', 'bold').setFontSize(10)
  doc.setTextColor(...COLOR_TEXT)
  doc.text(subtitulo, 14, 38)
}

// Pie de página genérico
function _pie(doc, texto) {
  const pageH = doc.internal.pageSize.getHeight()
  const pageW = doc.internal.pageSize.getWidth()
  doc.setFontSize(8).setTextColor(150, 150, 150)
  doc.text(texto, pageW / 2, pageH - 10, { align: 'center' })
}

// Genera tabla genérica
function _tabla(doc, head, body, startY) {
  autoTable(doc, {
    startY,
    head,
    body,
    theme: 'grid',
    headStyles: {
      fillColor: COLOR_HEADER,
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 8,
    },
    bodyStyles: { fontSize: 8, textColor: COLOR_TEXT },
    alternateRowStyles: { fillColor: COLOR_ALT_ROW },
    margin: { left: 14, right: 14 },
  })
  return doc.lastAutoTable.finalY
}

// ─── PDF INGRESO DE LOTE ──────────────────────────────────────────────────────
export function generarPdfIngreso(data) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
  const fechaStr = formatFechaLocal(data.fecha)

  _encabezado(doc, {
    titulo: `Ingreso de lote #${data.ingreso_lote_id}`,
    subtitulo: `Local: ${data.local_nombre}`,
    fecha: fechaStr,
  })

  let cursorY = 46
  if (data.observaciones) {
    doc.setFont('helvetica', 'italic').setFontSize(9).setTextColor(...COLOR_TEXT)
    doc.text(`Observaciones: ${data.observaciones}`, 14, cursorY)
    doc.setFont('helvetica', 'normal')
    cursorY += 7
  }

  const filas = data.items.map((item, i) => [
    i + 1,
    item.accesorio_sku,
    item.accesorio_nombre,
    item.cantidad_ingresada,
    item.stock_anterior,
    item.stock_nuevo,
  ])

  const finalY = _tabla(
    doc,
    [['#', 'SKU', 'Producto', 'Cant. ingresada', 'Stock anterior', 'Stock nuevo']],
    filas,
    cursorY + 2
  )

  // Total unidades
  const totalUnidades = data.items.reduce((s, i) => s + i.cantidad_ingresada, 0)
  doc.setFont('helvetica', 'bold').setFontSize(9).setTextColor(...COLOR_TEXT)
  doc.text(`Total unidades ingresadas: ${totalUnidades}`, 14, finalY + 6)

  _pie(doc, `Documento generado el ${formatFechaLocal(new Date().toISOString())} — CELULANDIA`)
  doc.save(`ingreso-lote-${data.ingreso_lote_id}.pdf`)
}

// ─── PDF TRANSFERENCIA DE LOTE ────────────────────────────────────────────────
export function generarPdfTransferencia(data) {
  const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' })
  const fechaStr = formatFechaLocal(data.fecha)

  _encabezado(doc, {
    titulo: `Transferencia #${data.transferencia_id}`,
    subtitulo: `Origen: ${data.local_origen_nombre}  →  Destino: ${data.local_destino_nombre}`,
    fecha: fechaStr,
  })

  let cursorY = 46
  if (data.observaciones) {
    doc.setFont('helvetica', 'italic').setFontSize(9).setTextColor(...COLOR_TEXT)
    doc.text(`Observaciones: ${data.observaciones}`, 14, cursorY)
    doc.setFont('helvetica', 'normal')
    cursorY += 7
  }

  const filas = data.items.map((item, i) => [
    i + 1,
    item.accesorio_sku,
    item.accesorio_nombre,
    item.cantidad_transferida,
    item.stock_origen_anterior,
    item.stock_origen_nuevo,
    item.stock_destino_anterior,
    item.stock_destino_nuevo,
  ])

  const head = [[
    '#', 'SKU', 'Producto', 'Cant. transferida',
    `Stock ${data.local_origen_nombre} (ant.)`,
    `Stock ${data.local_origen_nombre} (nuevo)`,
    `Stock ${data.local_destino_nombre} (ant.)`,
    `Stock ${data.local_destino_nombre} (nuevo)`,
  ]]

  const finalY = _tabla(doc, head, filas, cursorY + 2)

  const totalUnidades = data.items.reduce((s, i) => s + i.cantidad_transferida, 0)
  doc.setFont('helvetica', 'bold').setFontSize(9).setTextColor(...COLOR_TEXT)
  doc.text(`Total unidades transferidas: ${totalUnidades}`, 14, finalY + 6)

  _pie(doc, `Documento generado el ${formatFechaLocal(new Date().toISOString())} — CELULANDIA`)
  doc.save(`transferencia-${data.transferencia_id}.pdf`)
}