import { useState, useEffect, useRef } from 'react'
import { api } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import { descargarResponse } from '../helpers/descargar'
import './AccesoriosPage.css'
import './MovimientosPage.css'

const formatMonto = (monto) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 }).format(monto || 0)

const formatFechaHora = (iso) =>
  iso
    ? new Date(iso).toLocaleString('es-AR', {
        timeZone: 'America/Argentina/Buenos_Aires',
        day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    : '—'

const colorSobrante = (monto) => (monto > 0 ? '#1e7e34' : monto < 0 ? '#c00000' : '#555')

export default function InventarioPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()

  const [locales, setLocales] = useState([])

  // ── Reporte ───────────────────────────────────────────────────────────────
  const [archivoReporte, setArchivoReporte] = useState(null)
  const [generandoReporte, setGenerandoReporte] = useState(false)
  const inputReporteRef = useRef(null)

  // ── Aplicar ───────────────────────────────────────────────────────────────
  const [archivoAplicar, setArchivoAplicar] = useState(null)
  const [localId, setLocalId] = useState('')
  const [observaciones, setObservaciones] = useState('')
  const [confirmando, setConfirmando] = useState(false)
  const [aplicando, setAplicando] = useState(false)
  const [resultado, setResultado] = useState(null)
  const inputAplicarRef = useRef(null)

  // ── Historial ─────────────────────────────────────────────────────────────
  const [inventarios, setInventarios] = useState([])
  const [loadingHistorial, setLoadingHistorial] = useState(false)
  const [detalle, setDetalle] = useState(null) // InventarioDetalle abierto
  const [descargandoId, setDescargandoId] = useState(null)

  useEffect(() => {
    api.listarLocales({ activo: true }).then(setLocales).catch(e => mostrarAlerta('error', e.message))
    cargarHistorial()
  }, [])

  const cargarHistorial = async () => {
    setLoadingHistorial(true)
    try {
      setInventarios(await api.listarInventarios())
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoadingHistorial(false)
    }
  }

  const generarReporte = async () => {
    if (!archivoReporte) {
      mostrarAlerta('warning', 'Elegí la planilla completa')
      return
    }
    setGenerandoReporte(true)
    try {
      const fd = new FormData()
      fd.append('archivo', archivoReporte)
      const res = await api.reporteInventario(fd)
      await descargarResponse(res, 'reporte_inventario.xlsx')
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setGenerandoReporte(false)
    }
  }

  const pedirConfirmacion = () => {
    if (!localId) {
      mostrarAlerta('warning', 'Elegí el local del inventario')
      return
    }
    if (!archivoAplicar) {
      mostrarAlerta('warning', 'Elegí la planilla completa')
      return
    }
    setConfirmando(true)
  }

  const aplicar = async () => {
    setAplicando(true)
    try {
      const fd = new FormData()
      fd.append('archivo', archivoAplicar)
      fd.append('local_id', localId)
      if (observaciones.trim()) fd.append('observaciones', observaciones.trim())
      const res = await api.aplicarInventario(fd)
      setResultado(res)
      mostrarAlerta('success', `Inventario #${res.inventario_id} aplicado: ${res.cantidad_ajustes} ajuste(s)`)
      setArchivoAplicar(null)
      setObservaciones('')
      if (inputAplicarRef.current) inputAplicarRef.current.value = ''
      cargarHistorial()
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setAplicando(false)
      setConfirmando(false)
    }
  }

  const verDetalle = async (id) => {
    if (detalle?.inventario_id === id) {
      setDetalle(null)
      return
    }
    try {
      setDetalle(await api.obtenerInventario(id))
    } catch (e) {
      mostrarAlerta('error', e.message)
    }
  }

  const descargarRegistro = async (id) => {
    setDescargandoId(id)
    try {
      const res = await api.descargarInventarioExcel(id)
      await descargarResponse(res, `inventario_${id}.xlsx`)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setDescargandoId(null)
    }
  }

  const nombreLocal = locales.find(l => String(l.local_id) === String(localId))?.nombre

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Inventario</h2>
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span style={{ whiteSpace: 'pre-line' }}>{alerta.msg}</span>
          <button className="alerta-cerrar" onClick={cerrarAlerta}>&times;</button>
        </div>
      )}

      <p className="field-hint" style={{ marginBottom: 16 }}>
        1) Bajá la planilla desde <strong>Stock → Planilla de inventario</strong> (elegí local y tipos a excluir).
        2) Completá la columna <strong>Fisico</strong> (vacío cuenta como 0).
        3) Generá el reporte de discrepancias y, si está bien, aplicá el inventario.
      </p>

      {/* ── Reporte ── */}
      <div className="form-card">
        <h3>Reporte de discrepancias</h3>
        <span className="field-hint">No modifica el stock. Lista solo los productos con diferencias y el sobrante estimado total.</span>
        <div className="form-row">
          <div className="form-group">
            <label>Planilla completa (.xlsx)</label>
            <input
              ref={inputReporteRef}
              type="file"
              accept=".xlsx"
              onChange={e => setArchivoReporte(e.target.files?.[0] ?? null)}
            />
          </div>
        </div>
        <div className="form-actions">
          <button className="btn btn-primary" onClick={generarReporte} disabled={generandoReporte || !archivoReporte}>
            {generandoReporte ? 'Generando...' : '⬇ Descargar reporte'}
          </button>
        </div>
      </div>

      {/* ── Aplicar ── */}
      <div className="form-card">
        <h3>Aplicar inventario</h3>
        <span className="field-hint">
          Por cada producto con diferencia se registra un movimiento AJUSTE de (Fisico − Sistema) sobre el stock actual.
        </span>
        <div className="form-row">
          <div className="form-group">
            <label>Local</label>
            <select value={localId} onChange={e => { setLocalId(e.target.value); setConfirmando(false) }}>
              <option value="">Elegí un local</option>
              {locales.map(l => (
                <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Planilla completa (.xlsx)</label>
            <input
              ref={inputAplicarRef}
              type="file"
              accept=".xlsx"
              onChange={e => { setArchivoAplicar(e.target.files?.[0] ?? null); setConfirmando(false) }}
            />
          </div>
          <div className="form-group" style={{ flex: 2 }}>
            <label>Observaciones</label>
            <input
              type="text"
              placeholder="Ej: inventario electrónica noviembre"
              value={observaciones}
              onChange={e => setObservaciones(e.target.value)}
            />
          </div>
        </div>
        <div className="form-actions" style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {confirmando ? (
            <>
              <span>¿Aplicar el inventario en <strong>{nombreLocal}</strong>? Se va a modificar el stock.</span>
              <button className="btn btn-danger" onClick={aplicar} disabled={aplicando}>
                {aplicando ? 'Aplicando...' : 'Confirmar'}
              </button>
              <button className="btn btn-secondary" onClick={() => setConfirmando(false)} disabled={aplicando}>
                Cancelar
              </button>
            </>
          ) : (
            <button className="btn btn-primary" onClick={pedirConfirmacion}>
              Aplicar inventario
            </button>
          )}
        </div>

        {resultado && (
          <div className="filtros-row" style={{ marginTop: 12, gap: 12, flexWrap: 'wrap' }}>
            <span className="tipo-badge" style={{ background: '#e8e8f0', color: '#1a1a2e' }}>
              #{resultado.inventario_id} · {resultado.local_nombre}
            </span>
            <span className="tipo-badge" style={{ background: '#e8e8f0', color: '#1a1a2e' }}>
              {resultado.productos_contados} contados · {resultado.sin_diferencias} sin diferencias
            </span>
            <span className="tipo-badge" style={{ background: '#fde2e2', color: '#c00000' }}>
              Faltan: {resultado.faltan}
            </span>
            <span className="tipo-badge" style={{ background: '#ddebf7', color: '#1f4e9c' }}>
              Sobran: {resultado.sobran}
            </span>
            <span className="tipo-badge" style={{ background: '#e6f4ea', color: colorSobrante(resultado.sobrante_estimado) }}>
              Sobrante estimado: {formatMonto(resultado.sobrante_estimado)}
            </span>
          </div>
        )}
      </div>

      {/* ── Historial ── */}
      <h3 style={{ marginTop: 24 }}>Historial</h3>
      {loadingHistorial ? (
        <p>Cargando...</p>
      ) : inventarios.length === 0 ? (
        <p style={{ color: '#888' }}>Todavía no hay inventarios aplicados.</p>
      ) : (
        <div className="table-wrapper">
          <table className="acc-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Fecha</th>
                <th>Local</th>
                <th>Usuario</th>
                <th>Ajustes</th>
                <th>Sobrante estimado</th>
                <th>Observaciones</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {inventarios.map(inv => (
                <tr key={inv.inventario_id}>
                  <td className="mov-id">{inv.inventario_id}</td>
                  <td className="mov-fecha">{formatFechaHora(inv.fecha)}</td>
                  <td>{inv.local_nombre}</td>
                  <td>{inv.usuario_nombre || '—'}</td>
                  <td>{inv.cantidad_ajustes}</td>
                  <td style={{ color: colorSobrante(inv.sobrante_estimado), fontWeight: 600 }}>
                    {formatMonto(inv.sobrante_estimado)}
                  </td>
                  <td className="mov-motivo" title={inv.observaciones || ''}>{inv.observaciones || '—'}</td>
                  <td>
                    <span style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-secondary" onClick={() => verDetalle(inv.inventario_id)}>
                        {detalle?.inventario_id === inv.inventario_id ? 'Ocultar' : 'Ver'}
                      </button>
                      <button
                        className="btn btn-secondary"
                        onClick={() => descargarRegistro(inv.inventario_id)}
                        disabled={descargandoId === inv.inventario_id}
                      >
                        {descargandoId === inv.inventario_id ? '...' : '⬇ Excel'}
                      </button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {detalle && (
        <div className="form-card" style={{ marginTop: 16 }}>
          <h3>Inventario #{detalle.inventario_id} · {detalle.local_nombre} · {formatFechaHora(detalle.fecha)}</h3>
          {detalle.ajustes.length === 0 ? (
            <p style={{ color: '#888' }}>Sin ajustes (todo coincidía).</p>
          ) : (
            <div className="table-wrapper">
              <table className="acc-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Producto</th>
                    <th>Stock anterior</th>
                    <th style={{ color: '#c00000' }}>Faltan</th>
                    <th style={{ color: '#1f4e9c' }}>Sobran</th>
                    <th>Stock nuevo</th>
                  </tr>
                </thead>
                <tbody>
                  {detalle.ajustes.map(a => (
                    <tr key={a.movimiento_id}>
                      <td className="mov-id">{a.accesorio_id}</td>
                      <td>{a.accesorio_nombre}</td>
                      <td>{a.stock_anterior ?? '—'}</td>
                      <td style={{ color: '#c00000', fontWeight: 600 }}>{a.cantidad < 0 ? -a.cantidad : ''}</td>
                      <td style={{ color: '#1f4e9c', fontWeight: 600 }}>{a.cantidad > 0 ? a.cantidad : ''}</td>
                      <td>{a.stock_nuevo ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
