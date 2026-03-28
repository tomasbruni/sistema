import { useState } from 'react'
import './AccesoriosPage.css' // reutiliza los estilos base del sistema

// ─── TIPOS DE REPORTE ────────────────────────────────────────────────────────
// Cada reporte define: label, endpoint de export, y un componente de filtros extra.
// Para agregar un reporte nuevo: agregar una entrada acá y su FiltrosExtra si corresponde.

const REPORTES = [
  {
    key:      'iva',
    label:    'IVA sobre pagos electrónicos',
    endpoint: '/reportes/iva/export',
    // Sin filtros adicionales por ahora
    FiltrosExtra: null,
  },
]

const BASE_URL = 'http://localhost:8000'

// ─── COMPONENTE PRINCIPAL ────────────────────────────────────────────────────
export default function ReportesPage() {
  const hoy       = new Date().toISOString().slice(0, 10)
  const primerDia = new Date(new Date().getFullYear(), new Date().getMonth(), 1)
    .toISOString().slice(0, 10)

  const [tipoReporte,  setTipoReporte]  = useState(REPORTES[0].key)
  const [fechaDesde,   setFechaDesde]   = useState(primerDia)
  const [fechaHasta,   setFechaHasta]   = useState(hoy)
  const [filtrosExtra, setFiltrosExtra] = useState({})
  const [loading,      setLoading]      = useState(false)
  const [alerta,       setAlerta]       = useState(null)

  const reporte = REPORTES.find(r => r.key === tipoReporte)

  const mostrarAlerta = (tipo, msg) => {
    setAlerta({ tipo, msg })
    setTimeout(() => setAlerta(null), 5000)
  }

  const handleGenerar = async () => {
    if (!fechaDesde || !fechaHasta) {
      mostrarAlerta('warning', 'Seleccioná un rango de fechas.')
      return
    }
    if (fechaDesde > fechaHasta) {
      mostrarAlerta('warning', 'La fecha de inicio no puede ser posterior a la fecha de fin.')
      return
    }

    setLoading(true)
    try {
      const params = new URLSearchParams({
        fecha_desde: fechaDesde,
        fecha_hasta: fechaHasta,
        ...filtrosExtra,
      })

      const res = await fetch(`${BASE_URL}${reporte.endpoint}?${params}`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Error ${res.status}`)
      }

      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href  = url

      // Nombre del archivo: tipo_reporte_desde_hasta.xlsx
      link.download = `${tipoReporte}_${fechaDesde}_${fechaHasta}.xlsx`
      link.click()
      URL.revokeObjectURL(url)

      mostrarAlerta('success', 'Reporte generado correctamente.')
    } catch (err) {
      mostrarAlerta('error', `Error al generar el reporte: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  // ─── RENDER ────────────────────────────────────────────────────────────────
  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Reportes</h2>
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>{alerta.msg}</div>
      )}

      <div className="form-card">
        <h3>Configurar reporte</h3>

        <div className="acc-form">

          {/* Tipo de reporte */}
          <div className="form-group">
            <label>Tipo de reporte</label>
            <select
              value={tipoReporte}
              onChange={e => {
                setTipoReporte(e.target.value)
                setFiltrosExtra({})
              }}
            >
              {REPORTES.map(r => (
                <option key={r.key} value={r.key}>{r.label}</option>
              ))}
            </select>
          </div>

          {/* Rango de fechas */}
          <div className="form-row">
            <div className="form-group">
              <label>Fecha desde</label>
              <input
                type="date"
                value={fechaDesde}
                max={fechaHasta || hoy}
                onChange={e => setFechaDesde(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Fecha hasta</label>
              <input
                type="date"
                value={fechaHasta}
                min={fechaDesde}
                max={hoy}
                onChange={e => setFechaHasta(e.target.value)}
              />
            </div>
          </div>

          {/* Filtros adicionales según el tipo de reporte */}
          {reporte.FiltrosExtra && (
            <reporte.FiltrosExtra
              valores={filtrosExtra}
              onChange={setFiltrosExtra}
            />
          )}

          {/* Botón generar */}
          <div className="form-actions">
            <button
              className="btn-export"
              onClick={handleGenerar}
              disabled={loading}
            >
              {loading ? 'Generando...' : '⬇ Generar reporte Excel'}
            </button>
          </div>

        </div>
      </div>
    </div>
  )
}
