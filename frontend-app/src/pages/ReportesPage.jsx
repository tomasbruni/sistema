import { useEffect, useState } from 'react'
import './AccesoriosPage.css'
import { api } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'

export default function ReportesPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()

  const hoy       = new Date().toISOString().slice(0, 10)
  const primerDia = new Date(new Date().getFullYear(), new Date().getMonth(), 1)
    .toISOString().slice(0, 10)

  const [locales,   setLocales]   = useState([])
  const [usuarios,  setUsuarios]  = useState([])
  const [localId,   setLocalId]   = useState('')
  const [usuarioId, setUsuarioId] = useState('')
  const [desde,     setDesde]     = useState(primerDia)
  const [hasta,     setHasta]     = useState(hoy)
  const [loading,   setLoading]   = useState(false)

  // Resumen de facturación: rango propio y local opcional (vacío = todos)
  const [localFact, setLocalFact] = useState('')
  const [desdeFact, setDesdeFact] = useState(primerDia)
  const [hastaFact, setHastaFact] = useState(hoy)
  const [loadingFact, setLoadingFact] = useState(false)

  useEffect(() => {
    api.listarLocales({ tipo: 'LOCAL' }).then(setLocales).catch(() => {})
    api.listarUsuarios().then(data => setUsuarios(data.filter(u => u.rol === 'usuario'))).catch(() => {})
  }, [])

  const validarRango = (d, h) => {
    if (!d || !h) return 'Seleccioná un rango de fechas.'
    if (d > h)    return 'La fecha de inicio no puede ser posterior a la fecha de fin.'
    return null
  }

  /** Descarga el xlsx de una Response cruda, usando el filename del backend. */
  const descargar = async (res, fallback) => {
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Error ${res.status}`)
    }
    const blob = await res.blob()
    const cd   = res.headers.get('Content-Disposition') ?? ''
    const url  = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href     = url
    link.download = cd.match(/filename="?([^"]+)"?/)?.[1] ?? fallback
    link.click()
    URL.revokeObjectURL(url)
  }

  const handleGenerar = async () => {
    if (!localId || !usuarioId) {
      mostrarAlerta('warning', 'Seleccioná un local y una vendedora.')
      return
    }
    const error = validarRango(desde, hasta)
    if (error) {
      mostrarAlerta('warning', error)
      return
    }

    setLoading(true)
    try {
      const res = await api.descargarReporteComisiones({
        local_id:   localId,
        usuario_id: usuarioId,
        desde,
        hasta,
      })
      const nombre = usuarios.find(u => u.usuario_id === Number(usuarioId))?.nombre ?? usuarioId
      await descargar(res, `comisiones_${nombre}_${desde}_${hasta}.xlsx`)
      mostrarAlerta('success', 'Reporte generado correctamente.')
    } catch (err) {
      mostrarAlerta('error', `Error al generar el reporte: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerarFacturacion = async () => {
    const error = validarRango(desdeFact, hastaFact)
    if (error) {
      mostrarAlerta('warning', error)
      return
    }

    setLoadingFact(true)
    try {
      const res = await api.descargarReporteFacturacion({
        desde:    desdeFact,
        hasta:    hastaFact,
        local_id: localFact || null,
      })
      await descargar(res, `facturacion_${desdeFact}_${hastaFact}.xlsx`)
      mostrarAlerta('success', 'Reporte generado correctamente.')
    } catch (err) {
      mostrarAlerta('error', `Error al generar el reporte: ${err.message}`)
    } finally {
      setLoadingFact(false)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Reportes</h2>
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          {alerta.msg}
          <button className="alerta-cerrar" onClick={cerrarAlerta}>&times;</button>
        </div>
      )}

      <div className="form-card">
        <h3>Comisiones por vendedora</h3>
        <div className="acc-form">

          <div className="form-row">
            <div className="form-group">
              <label>Local *</label>
              <select value={localId} onChange={e => setLocalId(e.target.value)}>
                <option value="">Seleccionar local...</option>
                {locales.map(l => (
                  <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Vendedora *</label>
              <select value={usuarioId} onChange={e => setUsuarioId(e.target.value)}>
                <option value="">Seleccionar vendedora...</option>
                {usuarios.map(u => (
                  <option key={u.usuario_id} value={u.usuario_id}>{u.nombre}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Fecha desde *</label>
              <input type="date" value={desde} max={hasta || hoy}
                onChange={e => setDesde(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Fecha hasta *</label>
              <input type="date" value={hasta} min={desde}
                onChange={e => setHasta(e.target.value)} />
            </div>
          </div>

          <div className="form-actions">
            <button className="btn btn-primary" onClick={handleGenerar} disabled={loading}>
              {loading ? 'Generando...' : 'Generar Excel'}
            </button>
          </div>

        </div>
      </div>

      <div className="form-card">
        <h3>Resumen de facturación</h3>
        <div className="acc-form">

          <div className="form-row">
            <div className="form-group">
              <label>Local</label>
              <select value={localFact} onChange={e => setLocalFact(e.target.value)}>
                <option value="">Todos los locales</option>
                {locales.map(l => (
                  <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Fecha desde *</label>
              <input type="date" value={desdeFact} max={hastaFact || hoy}
                onChange={e => setDesdeFact(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Fecha hasta *</label>
              <input type="date" value={hastaFact} min={desdeFact}
                onChange={e => setHastaFact(e.target.value)} />
            </div>
          </div>

          <p className="form-hint">
            Incluye una tabla por cada local y vendedora con actividad, el resumen general,
            IVA, gastos, impuestos y el balance final. Los gastos cargados son globales:
            se listan enteros aunque filtres por local.
          </p>

          <div className="form-actions">
            <button className="btn btn-primary" onClick={handleGenerarFacturacion}
              disabled={loadingFact}>
              {loadingFact ? 'Generando...' : 'Generar Excel'}
            </button>
          </div>

        </div>
      </div>
    </div>
  )
}
