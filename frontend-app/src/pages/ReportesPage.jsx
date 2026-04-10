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

  useEffect(() => {
    api.listarLocales({ tipo: 'LOCAL' }).then(setLocales).catch(() => {})
    api.listarUsuarios().then(data => setUsuarios(data.filter(u => u.rol === 'usuario'))).catch(() => {})
  }, [])

  const handleGenerar = async () => {
    if (!localId || !usuarioId) {
      mostrarAlerta('warning', 'Seleccioná un local y una vendedora.')
      return
    }
    if (!desde || !hasta) {
      mostrarAlerta('warning', 'Seleccioná un rango de fechas.')
      return
    }
    if (desde > hasta) {
      mostrarAlerta('warning', 'La fecha de inicio no puede ser posterior a la fecha de fin.')
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
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Error ${res.status}`)
      }
      const blob    = await res.blob()
      const url     = URL.createObjectURL(blob)
      const link    = document.createElement('a')
      const nombre  = usuarios.find(u => u.usuario_id === Number(usuarioId))?.nombre ?? usuarioId
      link.href     = url
      link.download = `comisiones_${nombre}_${desde}_${hasta}.xlsx`
      link.click()
      URL.revokeObjectURL(url)
      mostrarAlerta('success', 'Reporte generado correctamente.')
    } catch (err) {
      mostrarAlerta('error', `Error al generar el reporte: ${err.message}`)
    } finally {
      setLoading(false)
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
              <input type="date" value={hasta} min={desde} max={hoy}
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
    </div>
  )
}
