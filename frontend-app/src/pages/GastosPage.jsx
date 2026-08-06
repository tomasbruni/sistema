import { useState, useEffect } from 'react'
import { api, LIMIT } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import './AccesoriosPage.css'
import './MovimientosPage.css'

const formatFecha = (fechaStr) => {
  if (!fechaStr) return '—'
  return new Date(fechaStr).toLocaleDateString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  })
}

const formatMonto = (monto) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', minimumFractionDigits: 2 }).format(monto || 0)

const num = (v) => (v === '' || v === null || v === undefined ? null : parseFloat(v))

// Fecha local en formato YYYY-MM-DD (evita el corrimiento de día de toISOString, que usa UTC).
const isoLocal = (d) => {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
const inicioMesActual = () => { const d = new Date(); return isoLocal(new Date(d.getFullYear(), d.getMonth(), 1)) }
const hoyLocal = () => isoLocal(new Date())

const IVA_RATE = 0.21
const calcIva = (neto) => {
  const n = num(neto)
  if (n === null) return ''
  return (Math.round(n * IVA_RATE * 100) / 100).toFixed(2)
}

const FORM_VACIO = {
  tipo: 'REAL',
  tipo_factura: 'A',
  comprada: false,
  porcentaje_real: '',
  total: '',
  neto: '',
  iva: '',
  descripcion: '',
  fecha: '',
}

const TOTALES_VACIO = { total_real: 0, total_blanco: 0, iva_a_favor: 0, cantidad: 0 }

// Campos de monto que se resetean al cambiar de tipo de gasto / factura,
// para no arrastrar valores de un tipo a otro.
const MONTOS_VACIOS = { total: '', neto: '', iva: '', porcentaje_real: '', comprada: false }

export default function GastosPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()

  const [gastos, setGastos] = useState([])
  const [totales, setTotales] = useState(TOTALES_VACIO)
  const [loading, setLoading] = useState(false)
  const [pagina, setPagina] = useState(0)
  const [hayMas, setHayMas] = useState(false)

  const [filtroTipo, setFiltroTipo] = useState(null)          // REAL | FACTURA
  const [filtroFactura, setFiltroFactura] = useState(null)    // A | C
  // Por defecto acotamos al mes actual: los totales siempre son de un período, nunca de toda la historia.
  const [fechaDesde, setFechaDesde] = useState(inicioMesActual())
  const [fechaHasta, setFechaHasta] = useState(hoyLocal())

  const [form, setForm] = useState(FORM_VACIO)
  const [ivaManual, setIvaManual] = useState(false)  // el usuario editó el IVA a mano
  const [editando, setEditando] = useState(null)
  const [guardando, setGuardando] = useState(false)
  const [confirmBorrar, setConfirmBorrar] = useState(null)

  useEffect(() => {
    cargar(0, filtroTipo, filtroFactura, fechaDesde, fechaHasta)
  }, [])

  const filtrosActuales = (tipo, factura, desde, hasta) => ({
    tipo: tipo || null,
    tipo_factura: factura || null,
    fecha_desde: desde || null,
    fecha_hasta: hasta || null,
  })

  const cargar = async (pag, tipo, factura, desde, hasta) => {
    setLoading(true)
    try {
      const filtros = filtrosActuales(tipo, factura, desde, hasta)
      const [data, tot] = await Promise.all([
        api.listarGastos({ offset: pag * LIMIT, limit: LIMIT + 1, ...filtros }),
        api.totalesGastos(filtros),
      ])
      setHayMas(data.length > LIMIT)
      setGastos(data.slice(0, LIMIT))
      setTotales(tot)
      setPagina(pag)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoading(false)
    }
  }

  const aplicarFiltros = () => cargar(0, filtroTipo, filtroFactura, fechaDesde, fechaHasta)

  const handleFiltroTipo = (tipo) => {
    const nuevo = filtroTipo === tipo ? null : tipo
    const nuevaFactura = tipo === 'FACTURA' ? filtroFactura : null
    setFiltroTipo(nuevo)
    setFiltroFactura(nuevaFactura)
    cargar(0, nuevo, nuevaFactura, fechaDesde, fechaHasta)
  }

  const handleFiltroFactura = (f) => {
    const nuevo = filtroFactura === f ? null : f
    setFiltroFactura(nuevo)
    setFiltroTipo('FACTURA')
    cargar(0, 'FACTURA', nuevo, fechaDesde, fechaHasta)
  }

  // ── Preview en vivo de la factura A (total = neto + iva) y aporte real ──
  const netoNum = num(form.neto) || 0
  const ivaNum = num(form.iva) || 0
  const totalFacturaA = netoNum + ivaNum
  const aporteRealPreview = form.comprada ? (totalFacturaA * (num(form.porcentaje_real) || 0)) / 100 : 0

  const construirPayload = () => {
    const base = {
      tipo: form.tipo,
      descripcion: form.descripcion.trim(),
      fecha: form.fecha || null,
    }
    if (form.tipo === 'REAL') {
      return { ...base, total: num(form.total) }
    }
    if (form.tipo_factura === 'A') {
      return {
        ...base,
        tipo_factura: 'A',
        neto: num(form.neto),
        iva: num(form.iva),
        comprada: form.comprada,
        porcentaje_real: form.comprada ? num(form.porcentaje_real) : null,
      }
    }
    // Factura C
    return { ...base, tipo_factura: 'C', total: num(form.total) }
  }

  const validar = () => {
    if (!form.descripcion.trim()) return 'Completá la descripción'
    if (form.tipo === 'REAL') {
      if (!num(form.total)) return 'Ingresá el total del gasto'
    } else if (form.tipo_factura === 'A') {
      if (num(form.neto) === null || num(form.iva) === null) return 'Ingresá neto e IVA de la factura A'
      if (form.comprada) {
        const p = num(form.porcentaje_real)
        if (p === null) return 'Ingresá el porcentaje real de la factura comprada'
        if (p < 0 || p > 100) return 'El porcentaje debe estar entre 0 y 100'
      }
    } else if (form.tipo_factura === 'C') {
      if (!num(form.total)) return 'Ingresá el total de la factura C'
    }
    return null
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
        await api.actualizarGasto(editando, payload)
        mostrarAlerta('success', 'Gasto actualizado')
      } else {
        await api.crearGasto(payload)
        mostrarAlerta('success', 'Gasto registrado')
      }
      // Persistimos tipo de gasto y tipo de factura para cargar varios seguidos.
      setForm(f => ({ ...FORM_VACIO, tipo: f.tipo, tipo_factura: f.tipo_factura }))
      setIvaManual(false)
      setEditando(null)
      aplicarFiltros()
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setGuardando(false)
    }
  }

  const iniciarEdicion = (g) => {
    setEditando(g.id)
    setForm({
      tipo: g.tipo,
      tipo_factura: g.tipo_factura || 'A',
      comprada: g.comprada,
      porcentaje_real: g.porcentaje_real != null ? String(g.porcentaje_real) : '',
      total: g.total != null ? String(g.total) : '',
      neto: g.neto != null ? String(g.neto) : '',
      iva: g.iva != null ? String(g.iva) : '',
      descripcion: g.descripcion,
      fecha: g.fecha ? g.fecha.slice(0, 10) : '',
    })
    setIvaManual(true)  // preservamos el IVA guardado, no lo recalculamos
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const cancelarEdicion = () => {
    setEditando(null)
    setForm(f => ({ ...FORM_VACIO, tipo: f.tipo, tipo_factura: f.tipo_factura }))
    setIvaManual(false)
  }

  const confirmarBorrar = async (id) => {
    try {
      await api.eliminarGasto(id)
      mostrarAlerta('success', 'Gasto eliminado')
      setConfirmBorrar(null)
      aplicarFiltros()
    } catch (e) {
      mostrarAlerta('error', e.message)
    }
  }

  const descripcionTipo = (g) => {
    if (g.tipo === 'REAL') return 'Real'
    if (g.tipo_factura === 'A') return g.comprada ? `Factura A comprada (${g.porcentaje_real}%)` : 'Factura A'
    return 'Factura C'
  }

  const esFactura = form.tipo === 'FACTURA'
  const esFacturaA = esFactura && form.tipo_factura === 'A'
  const esFacturaC = esFactura && form.tipo_factura === 'C'

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Gastos</h2>
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.msg}</span>
          <button className="alerta-cerrar" onClick={cerrarAlerta}>&times;</button>
        </div>
      )}

      {/* ── Formulario ── */}
      <div className="form-card">
        <h3>{editando !== null ? 'Editar gasto' : 'Nuevo gasto'}</h3>
        <form className="acc-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label>Tipo de gasto</label>
              <select value={form.tipo} onChange={e => { setIvaManual(false); setForm(f => ({ ...f, ...MONTOS_VACIOS, tipo: e.target.value })) }}>
                <option value="REAL">Real (plata que salió)</option>
                <option value="FACTURA">Factura (en blanco)</option>
              </select>
            </div>
            {esFactura && (
              <div className="form-group">
                <label>Tipo de factura</label>
                <select value={form.tipo_factura} onChange={e => { setIvaManual(false); setForm(f => ({ ...f, ...MONTOS_VACIOS, tipo_factura: e.target.value })) }}>
                  <option value="A">Factura A</option>
                  <option value="C">Factura C</option>
                </select>
              </div>
            )}
          </div>

          {/* Gasto real: total */}
          {form.tipo === 'REAL' && (
            <div className="form-group">
              <label>Total ($)</label>
              <input
                type="number" step="0.01" min="0" placeholder="0.00"
                value={form.total}
                onChange={e => setForm(f => ({ ...f, total: e.target.value }))}
              />
            </div>
          )}

          {/* Factura A: neto + iva (+ comprada / porcentaje) */}
          {esFacturaA && (
            <>
              <div className="form-row">
                <div className="form-group">
                  <label>Neto / productos ($)</label>
                  <input
                    type="number" step="0.01" min="0" placeholder="0.00"
                    value={form.neto}
                    onChange={e => {
                      const neto = e.target.value
                      setForm(f => ({ ...f, neto, iva: ivaManual ? f.iva : calcIva(neto) }))
                    }}
                  />
                </div>
                <div className="form-group">
                  <label>IVA ($) <span style={{ color: '#888', fontWeight: 400 }}>· 21% auto, editable</span></label>
                  <input
                    type="number" step="0.01" min="0" placeholder="0.00"
                    value={form.iva}
                    onChange={e => { setIvaManual(true); setForm(f => ({ ...f, iva: e.target.value })) }}
                  />
                </div>
              </div>
              <div className="form-row" style={{ alignItems: 'center' }}>
                <div className="form-group" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <input
                    id="comprada" type="checkbox"
                    checked={form.comprada}
                    onChange={e => setForm(f => ({ ...f, comprada: e.target.checked }))}
                  />
                  <label htmlFor="comprada" style={{ margin: 0 }}>Factura comprada</label>
                </div>
                {form.comprada && (
                  <div className="form-group">
                    <label>% real sobre el total</label>
                    <input
                      type="number" step="1" min="0" max="100" placeholder="0"
                      value={form.porcentaje_real}
                      onChange={e => setForm(f => ({ ...f, porcentaje_real: e.target.value }))}
                    />
                  </div>
                )}
              </div>
              <p style={{ fontSize: '0.85rem', color: '#555', margin: '4px 0' }}>
                Total factura: <strong>{formatMonto(totalFacturaA)}</strong>
                {' · '}Aporta a blanco: <strong>{formatMonto(netoNum)}</strong>
                {' · '}IVA a favor: <strong>{formatMonto(ivaNum)}</strong>
                {form.comprada && <> {' · '}Aporta a real: <strong>{formatMonto(aporteRealPreview)}</strong></>}
              </p>
            </>
          )}

          {/* Factura C: total */}
          {esFacturaC && (
            <div className="form-group">
              <label>Total factura ($)</label>
              <input
                type="number" step="0.01" min="0" placeholder="0.00"
                value={form.total}
                onChange={e => setForm(f => ({ ...f, total: e.target.value }))}
              />
              <p style={{ fontSize: '0.85rem', color: '#555', margin: '4px 0' }}>
                Aporta todo a facturado en blanco.
              </p>
            </div>
          )}

          <div className="form-row">
            <div className="form-group" style={{ flex: 2 }}>
              <label>Descripción</label>
              <input
                type="text"
                placeholder="Ej: alquiler, proveedor, servicios..."
                value={form.descripcion}
                onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label>Fecha</label>
              <input
                type="date"
                value={form.fecha}
                onChange={e => setForm(f => ({ ...f, fecha: e.target.value }))}
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
        {['REAL', 'FACTURA'].map(t => (
          <button
            key={t}
            className={`filtro-chip ${filtroTipo === t ? 'filtro-chip-activo' : ''}`}
            onClick={() => handleFiltroTipo(t)}
          >
            {t === 'REAL' ? 'Reales' : 'Facturas'}
          </button>
        ))}
        {['A', 'C'].map(f => (
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
              const desde = inicioMesActual(), hasta = hoyLocal()
              setFechaDesde(desde); setFechaHasta(hasta); setFiltroTipo(null); setFiltroFactura(null)
              cargar(0, null, null, desde, hasta)
            }}
          >
            Mes actual
          </button>
        </div>
      </div>

      {/* ── Totales (según filtros) ── */}
      <div className="filtros-row" style={{ marginBottom: 12, gap: 16, flexWrap: 'wrap' }}>
        <span className="tipo-badge" style={{ background: '#e6f4ea', color: '#1e7e34' }}>
          Total real: {formatMonto(totales.total_real)}
        </span>
        <span className="tipo-badge" style={{ background: '#e8eefc', color: '#1a3fa8' }}>
          Facturado en blanco: {formatMonto(totales.total_blanco)}
        </span>
        <span className="tipo-badge" style={{ background: '#fdf0e6', color: '#a85a1a' }}>
          IVA a favor: {formatMonto(totales.iva_a_favor)}
        </span>
        <span className="tipo-badge" style={{ background: '#e8e8f0', color: '#1a1a2e' }}>
          {totales.cantidad} gasto(s)
        </span>
      </div>

      {/* ── Tabla ── */}
      {loading ? (
        <p>Cargando...</p>
      ) : gastos.length === 0 ? (
        <p style={{ color: '#888' }}>Sin gastos.</p>
      ) : (
        <div className="table-wrapper">
          <table className="acc-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Tipo</th>
                <th>Total</th>
                <th>→ Real</th>
                <th>→ Blanco</th>
                <th>→ IVA</th>
                <th>Descripción</th>
                <th>Fecha</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {gastos.map(g => (
                <tr key={g.id}>
                  <td className="mov-id">{g.id}</td>
                  <td><span className="tipo-badge">{descripcionTipo(g)}</span></td>
                  <td className="cantidad-mov">{formatMonto(g.total)}</td>
                  <td className="cantidad-mov">{Number(g.aporte_real) ? formatMonto(g.aporte_real) : '—'}</td>
                  <td className="cantidad-mov">{Number(g.aporte_blanco) ? formatMonto(g.aporte_blanco) : '—'}</td>
                  <td className="cantidad-mov">{Number(g.aporte_iva) ? formatMonto(g.aporte_iva) : '—'}</td>
                  <td className="mov-motivo" title={g.descripcion}>{g.descripcion}</td>
                  <td className="mov-fecha">{formatFecha(g.fecha)}</td>
                  <td>
                    {confirmBorrar === g.id ? (
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <button className="btn btn-danger" onClick={() => confirmarBorrar(g.id)}>Confirmar</button>
                        <button className="btn btn-secondary" onClick={() => setConfirmBorrar(null)}>No</button>
                      </span>
                    ) : (
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <button className="btn btn-secondary" onClick={() => iniciarEdicion(g)}>Editar</button>
                        <button className="btn btn-danger" onClick={() => setConfirmBorrar(g.id)}>Borrar</button>
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
        <button className="btn btn-secondary" disabled={pagina === 0} onClick={() => cargar(pagina - 1, filtroTipo, filtroFactura, fechaDesde, fechaHasta)}>
          Anterior
        </button>
        <span style={{ margin: '0 12px', fontSize: '0.9rem', color: '#555' }}>Pág. {pagina + 1}</span>
        <button className="btn btn-secondary" disabled={!hayMas} onClick={() => cargar(pagina + 1, filtroTipo, filtroFactura, fechaDesde, fechaHasta)}>
          Siguiente
        </button>
      </div>
    </div>
  )
}
