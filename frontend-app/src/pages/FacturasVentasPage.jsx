import { useState, useEffect } from 'react'
import { api, LIMIT } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import { descargarResponse } from '../helpers/descargar'
import { hoyAR } from '../helpers/fechas'
import InputFecha from '../components/InputFecha/InputFecha'
import './AccesoriosPage.css'
import './MovimientosPage.css'

// `fecha` viene como 'YYYY-MM-DD' (sin hora): se formatea sin pasar por Date para no correr el día.
const formatFecha = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : '—')

const formatMonto = (monto) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', minimumFractionDigits: 2 }).format(monto || 0)

const num = (v) => (v === '' || v === null || v === undefined ? null : parseFloat(v))
// Sumas en centavos enteros para que la diferencia contra el total no arrastre errores de float.
const centavos = (v) => Math.round((num(v) || 0) * 100)
const deCentavos = (c) => (c / 100).toFixed(2)

// Fechas siempre en hora argentina (no la del navegador), igual que el backend.
const inicioMesActual = () => `${hoyAR().slice(0, 7)}-01`
const mesActual = () => hoyAR().slice(0, 7)

const ALICUOTA = 0.21

const FORM_VACIO = {
  tipo_factura: 'B',
  fecha: '',
  punto_venta: '',
  numero_comprobante: '',
  neto_21: '',
  iva_21: '',
  total: '',
  descripcion: '',
}

const TOTALES_VACIO = { neto_21: 0, iva_21: 0, total: 0, cantidad: 0 }

export default function FacturasVentasPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()

  const [facturas, setFacturas] = useState([])
  const [totales, setTotales] = useState(TOTALES_VACIO)
  const [loading, setLoading] = useState(false)
  const [pagina, setPagina] = useState(0)
  const [hayMas, setHayMas] = useState(false)

  const [filtroFactura, setFiltroFactura] = useState(null)    // A | B
  // Por defecto acotamos al mes actual: los totales siempre son de un período, nunca de toda la historia.
  const [fechaDesde, setFechaDesde] = useState(inicioMesActual())
  const [fechaHasta, setFechaHasta] = useState(hoyAR())
  const [periodoLibro, setPeriodoLibro] = useState(mesActual())
  const [descargando, setDescargando] = useState(false)

  const [form, setForm] = useState(FORM_VACIO)
  const [ivaManual, setIvaManual] = useState(false)  // el usuario editó el IVA a mano
  const [editando, setEditando] = useState(null)
  const [guardando, setGuardando] = useState(false)
  const [confirmBorrar, setConfirmBorrar] = useState(null)

  useEffect(() => {
    cargar(0, filtroFactura, fechaDesde, fechaHasta)
  }, [])

  const cargar = async (pag, factura, desde, hasta) => {
    setLoading(true)
    try {
      const filtros = { tipo_factura: factura || null, fecha_desde: desde || null, fecha_hasta: hasta || null }
      const [data, tot] = await Promise.all([
        api.listarFacturasVentas({ offset: pag * LIMIT, limit: LIMIT + 1, ...filtros }),
        api.totalesFacturasVentas(filtros),
      ])
      setHayMas(data.length > LIMIT)
      setFacturas(data.slice(0, LIMIT))
      setTotales(tot)
      setPagina(pag)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoading(false)
    }
  }

  const aplicarFiltros = () => cargar(0, filtroFactura, fechaDesde, fechaHasta)

  const handleFiltroFactura = (f) => {
    const nuevo = filtroFactura === f ? null : f
    setFiltroFactura(nuevo)
    cargar(0, nuevo, fechaDesde, fechaHasta)
  }

  const descargarIvaVentas = async () => {
    if (!periodoLibro) {
      mostrarAlerta('warning', 'Elegí el mes del libro')
      return
    }
    setDescargando(true)
    try {
      const res = await api.descargarIvaVentas({ periodo: periodoLibro })
      await descargarResponse(res, `iva_ventas_${periodoLibro}.xlsx`)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setDescargando(false)
    }
  }

  // ── Importes: el neto calcula IVA y total; el total (factura B) calcula neto e IVA ──
  const setNeto = (valor) => {
    setForm(f => {
      const iva = ivaManual ? f.iva_21 : (num(valor) === null ? '' : deCentavos(Math.round(centavos(valor) * ALICUOTA)))
      return { ...f, neto_21: valor, iva_21: iva, total: num(valor) === null ? '' : deCentavos(centavos(valor) + centavos(iva)) }
    })
  }

  const setIva = (valor) => {
    setIvaManual(true)
    setForm(f => ({ ...f, iva_21: valor, total: num(f.neto_21) === null ? f.total : deCentavos(centavos(f.neto_21) + centavos(valor)) }))
  }

  const setTotal = (valor) => {
    setIvaManual(false)
    setForm(f => {
      if (num(valor) === null) return { ...f, total: valor, neto_21: '', iva_21: '' }
      const neto = Math.round(centavos(valor) / (1 + ALICUOTA))
      return { ...f, total: valor, neto_21: deCentavos(neto), iva_21: deCentavos(centavos(valor) - neto) }
    })
  }

  const diferencia = centavos(form.total) - centavos(form.neto_21) - centavos(form.iva_21)   // > 0: falta | < 0: sobra

  const validar = () => {
    if (!form.fecha) return 'Completá la fecha de emisión de la factura'
    if (!form.punto_venta.trim() || !form.numero_comprobante.trim()) return 'Completá punto de venta y número de comprobante'
    if (!num(form.neto_21)) return 'Ingresá el neto gravado (o el total)'
    if (!num(form.total)) return 'Ingresá el total del comprobante tal como figura impreso'
    // La diferencia contra el total la valida el backend (422 con el detalle).
    return null
  }

  const construirPayload = () => ({
    tipo_factura: form.tipo_factura,
    fecha: form.fecha,
    punto_venta: form.punto_venta.trim(),
    numero_comprobante: form.numero_comprobante.trim(),
    neto_21: form.neto_21 || '0',
    iva_21: form.iva_21 || '0',
    total: form.total,
    descripcion: form.descripcion.trim() || null,
  })

  const resetForm = (f) => {
    // Persistimos el tipo de factura para cargar varias seguidas.
    setForm({ ...FORM_VACIO, tipo_factura: f.tipo_factura })
    setIvaManual(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const error = validar()
    if (error) {
      mostrarAlerta('warning', error)
      return
    }
    setGuardando(true)
    try {
      const payload = construirPayload()
      if (editando !== null) {
        await api.actualizarFacturaVenta(editando, payload)
        mostrarAlerta('success', 'Factura actualizada')
      } else {
        await api.crearFacturaVenta(payload)
        mostrarAlerta('success', 'Factura registrada')
      }
      resetForm(form)
      setEditando(null)
      aplicarFiltros()
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setGuardando(false)
    }
  }

  const iniciarEdicion = (fv) => {
    const str = (v) => (v != null && Number(v) !== 0 ? String(v) : '')
    setEditando(fv.id)
    setForm({
      tipo_factura: fv.tipo_factura,
      fecha: fv.fecha || '',
      punto_venta: fv.punto_venta || '',
      numero_comprobante: fv.numero_comprobante || '',
      neto_21: str(fv.neto_21),
      iva_21: str(fv.iva_21),
      total: str(fv.total),
      descripcion: fv.descripcion || '',
    })
    setIvaManual(true)  // preservamos el IVA guardado, no lo recalculamos
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const cancelarEdicion = () => {
    setEditando(null)
    resetForm(form)
  }

  const confirmarBorrar = async (id) => {
    try {
      await api.eliminarFacturaVenta(id)
      mostrarAlerta('success', 'Factura eliminada')
      setConfirmBorrar(null)
      aplicarFiltros()
    } catch (e) {
      mostrarAlerta('error', e.message)
    }
  }

  const inputMonto = (value, onChange) => (
    <input type="number" step="0.01" min="0" placeholder="0.00" value={value} onChange={e => onChange(e.target.value)} />
  )

  const ayudaStyle = { color: '#888', fontWeight: 400 }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Facturas de venta</h2>
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.msg}</span>
          <button className="alerta-cerrar" onClick={cerrarAlerta}>&times;</button>
        </div>
      )}

      {/* ── Formulario ── */}
      <div className="form-card">
        <h3>{editando !== null ? 'Editar factura' : 'Nueva factura'}</h3>
        <form className="acc-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label>Tipo de factura</label>
              <select value={form.tipo_factura} onChange={e => setForm(f => ({ ...f, tipo_factura: e.target.value }))}>
                <option value="A">Factura A</option>
                <option value="B">Factura B</option>
              </select>
            </div>
            <div className="form-group">
              <label>Fecha de emisión</label>
              <InputFecha value={form.fecha} onChange={fecha => setForm(f => ({ ...f, fecha }))} />
            </div>
            <div className="form-group">
              <label>Punto de venta</label>
              <input
                type="text" placeholder="Ej: 3"
                value={form.punto_venta}
                onChange={e => setForm(f => ({ ...f, punto_venta: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label>N° de comprobante</label>
              <input
                type="text" placeholder="Ej: 1520"
                value={form.numero_comprobante}
                onChange={e => setForm(f => ({ ...f, numero_comprobante: e.target.value }))}
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Neto gravado 21% ($)</label>
              {inputMonto(form.neto_21, setNeto)}
            </div>
            <div className="form-group">
              <label>IVA 21% ($) <span style={ayudaStyle}>· auto, editable</span></label>
              {inputMonto(form.iva_21, setIva)}
            </div>
            <div className="form-group">
              <label>Total del comprobante ($) <span style={ayudaStyle}>· si cargás el total se calcula el neto</span></label>
              {inputMonto(form.total, setTotal)}
            </div>
          </div>

          <p style={{ fontSize: '0.85rem', color: '#555', margin: '4px 0' }}>
            Neto + IVA: <strong>{formatMonto((centavos(form.neto_21) + centavos(form.iva_21)) / 100)}</strong>
            {' · '}Total declarado: <strong>{formatMonto(centavos(form.total) / 100)}</strong>
            {' · '}
            {form.total === '' ? (
              <span style={{ color: '#888' }}>cargá el total para comparar</span>
            ) : diferencia === 0 ? (
              <strong style={{ color: '#1e7e34' }}>✓ cierra</strong>
            ) : (
              <strong style={{ color: '#c0392b' }}>
                {diferencia > 0 ? 'falta' : 'sobra'} {formatMonto(Math.abs(diferencia) / 100)}
              </strong>
            )}
          </p>

          <div className="form-row">
            <div className="form-group" style={{ flex: 2 }}>
              <label>Concepto (opcional)</label>
              <input
                type="text"
                placeholder="Ej: venta celular, accesorios..."
                value={form.descripcion}
                onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button type="submit" className="btn btn-primary" disabled={guardando}>
              {guardando ? 'Guardando...' : editando !== null ? 'Guardar cambios' : 'Registrar'}
            </button>
            {editando !== null && (
              <button type="button" className="btn btn-secondary" onClick={cancelarEdicion}>
                Cancelar
              </button>
            )}
          </div>
        </form>
      </div>

      {/* ── Filtros ── */}
      <div className="filtros-row" style={{ marginBottom: 12, flexWrap: 'wrap' }}>
        {['A', 'B'].map(f => (
          <button
            key={f}
            className={`filtro-chip ${filtroFactura === f ? 'filtro-chip-activo' : ''}`}
            onClick={() => handleFiltroFactura(f)}
          >
            Factura {f}
          </button>
        ))}
        <div className="fecha-inputs">
          <div className="fecha-group">
            <span className="fecha-label">Desde</span>
            <input type="date" className="fecha-input" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} />
          </div>
          <span className="fecha-separador">—</span>
          <div className="fecha-group">
            <span className="fecha-label">Hasta</span>
            <input type="date" className="fecha-input" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} />
          </div>
          <button className="btn btn-secondary" style={{ marginTop: 16 }} onClick={aplicarFiltros}>Filtrar</button>
          <button
            className="btn btn-secondary" style={{ marginTop: 16 }}
            onClick={() => {
              const desde = inicioMesActual(), hasta = hoyAR()
              setFechaDesde(desde); setFechaHasta(hasta); setFiltroFactura(null)
              cargar(0, null, desde, hasta)
            }}
          >
            Mes actual
          </button>
        </div>
      </div>

      {/* ── Libro IVA ventas (por mes de emisión) ── */}
      <div className="filtros-row" style={{ marginBottom: 12, alignItems: 'flex-end', gap: 8 }}>
        <div className="fecha-group">
          <span className="fecha-label">Libro IVA Ventas</span>
          <input type="month" className="fecha-input" value={periodoLibro} onChange={e => setPeriodoLibro(e.target.value)} />
        </div>
        <button className="btn btn-primary" disabled={descargando} onClick={descargarIvaVentas}>
          {descargando ? 'Generando...' : 'Descargar IVA Ventas'}
        </button>
      </div>

      {/* ── Totales (según filtros) ── */}
      <div className="filtros-row" style={{ marginBottom: 12, gap: 16, flexWrap: 'wrap' }}>
        <span className="tipo-badge" style={{ background: '#e8eefc', color: '#1a3fa8' }}>
          Neto 21%: {formatMonto(totales.neto_21)}
        </span>
        <span className="tipo-badge" style={{ background: '#fdf0e6', color: '#a85a1a' }}>
          IVA débito: {formatMonto(totales.iva_21)}
        </span>
        <span className="tipo-badge" style={{ background: '#e6f4ea', color: '#1e7e34' }}>
          Total facturado: {formatMonto(totales.total)}
        </span>
        <span className="tipo-badge" style={{ background: '#e8e8f0', color: '#1a1a2e' }}>
          {totales.cantidad} factura(s)
        </span>
      </div>

      {/* ── Tabla ── */}
      {loading ? (
        <p>Cargando...</p>
      ) : facturas.length === 0 ? (
        <p style={{ color: '#888' }}>Sin facturas.</p>
      ) : (
        <div className="table-wrapper">
          <table className="acc-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Fecha</th>
                <th>Tipo</th>
                <th>Comprobante</th>
                <th>Neto 21%</th>
                <th>IVA 21%</th>
                <th>Total</th>
                <th>Concepto</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {facturas.map(fv => (
                <tr key={fv.id}>
                  <td className="mov-id">{fv.id}</td>
                  <td className="mov-fecha">{formatFecha(fv.fecha)}</td>
                  <td><span className="tipo-badge">Factura {fv.tipo_factura}</span></td>
                  <td>{`${fv.punto_venta}-${fv.numero_comprobante}`}</td>
                  <td className="cantidad-mov">{formatMonto(fv.neto_21)}</td>
                  <td className="cantidad-mov">{formatMonto(fv.iva_21)}</td>
                  <td className="cantidad-mov">{formatMonto(fv.total)}</td>
                  <td className="mov-motivo" title={fv.descripcion || ''}>{fv.descripcion || '—'}</td>
                  <td>
                    {confirmBorrar === fv.id ? (
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <button className="btn btn-danger" onClick={() => confirmarBorrar(fv.id)}>Confirmar</button>
                        <button className="btn btn-secondary" onClick={() => setConfirmBorrar(null)}>No</button>
                      </span>
                    ) : (
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <button className="btn btn-secondary" onClick={() => iniciarEdicion(fv)}>Editar</button>
                        <button className="btn btn-danger" onClick={() => setConfirmBorrar(fv.id)}>Borrar</button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Paginación ── */}
      <div className="paginacion" style={{ marginTop: 16 }}>
        <button className="btn btn-secondary" disabled={pagina === 0} onClick={() => cargar(pagina - 1, filtroFactura, fechaDesde, fechaHasta)}>
          Anterior
        </button>
        <span style={{ margin: '0 12px', fontSize: '0.9rem', color: '#555' }}>Pág. {pagina + 1}</span>
        <button className="btn btn-secondary" disabled={!hayMas} onClick={() => cargar(pagina + 1, filtroFactura, fechaDesde, fechaHasta)}>
          Siguiente
        </button>
      </div>
    </div>
  )
}
