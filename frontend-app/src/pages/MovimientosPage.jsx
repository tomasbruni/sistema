import { useState, useEffect, useRef } from 'react'
import { api, LIMIT} from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import './AccesoriosPage.css'
import './MovimientosPage.css'

// ─── CONSTANTES ──────────────────────────────────────────────────────────────
const TIPOS_MOVIMIENTO = [
  { valor: 'ENTRADA', label: '⬆ Entrada' },
  { valor: 'SALIDA',  label: '⬇ Salida'  },
  { valor: 'AJUSTE',  label: '⚖ Ajuste'  },
  { valor: 'VENTA',   label: '🛒 Venta'   },
]

const CLASE_TIPO = {
  ENTRADA: 'tipo-entrada',
  SALIDA:  'tipo-salida',
  AJUSTE:  'tipo-ajuste',
  VENTA:   'tipo-venta',
}

const formatFecha = (fechaStr) => {
  if (!fechaStr) return '—'
  return new Date(fechaStr).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

// ─── COMPONENTE PRINCIPAL ────────────────────────────────────────────────────
export default function MovimientosPage() {
  const { alerta, mostrarAlerta } = useAlerta()

  const [movimientos, setMovimientos]     = useState([])
  const [total, setTotal]                 = useState(0)
  const [loadingLista, setLoadingLista]   = useState(false)
  const [loadingExport, setLoadingExport] = useState(false)

  const [pagina, setPagina] = useState(0)
  const [hayMas, setHayMas] = useState(false)

  const [filtroTipo, setFiltroTipo]       = useState(null)
  const [filtroLocalId, setFiltroLocalId] = useState(null)
  const [fechaDesde, setFechaDesde]       = useState('')
  const [fechaHasta, setFechaHasta]       = useState('')
  const [locales, setLocales]             = useState([])

  const debounceRef = useRef(null)

  useEffect(() => {
    fetchMovimientos(0)
    api.listarLocales().then(setLocales).catch(() => {})
  }, [])

  const fetchMovimientos = async (pag, overrides = {}) => {
    setLoadingLista(true)
    const params = {
      skip:            pag * LIMIT,
      limit:           LIMIT + 1,
      local_id:        filtroLocalId,
      tipo_movimiento: filtroTipo,
      fecha_desde:     fechaDesde || null,
      fecha_hasta:     fechaHasta || null,
      ...overrides,
    }
    try {
      const data = await api.listarMovimientos(params)
      const items = data.items ?? data
      setHayMas(items.length > LIMIT)
      setMovimientos(items.slice(0, LIMIT))
      if (data.total !== undefined) setTotal(data.total)
    } catch (err) {
      mostrarAlerta('error', `Error al cargar movimientos: ${err.message}`)
    } finally {
      setLoadingLista(false)
    }
  }

  const irAPagina = (nueva) => { setPagina(nueva); fetchMovimientos(nueva) }

  const aplicarFiltros = (overrides = {}) => { setPagina(0); fetchMovimientos(0, overrides) }

  const handleFiltroTipo = (tipo) => {
    const nuevo = filtroTipo === tipo ? null : tipo
    setFiltroTipo(nuevo)
    aplicarFiltros({ tipo_movimiento: nuevo })
  }

  const handleFiltroLocal = (localId) => {
    const nuevo = filtroLocalId === localId ? null : localId
    setFiltroLocalId(nuevo)
    aplicarFiltros({ local_id: nuevo })
  }

  const handleFechaDesde = (e) => {
    const val = e.target.value
    setFechaDesde(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => aplicarFiltros({ fecha_desde: val || null }), 400)
  }

  const handleFechaHasta = (e) => {
    const val = e.target.value
    setFechaHasta(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => aplicarFiltros({ fecha_hasta: val || null }), 400)
  }

  const limpiarFiltros = () => {
    setFiltroTipo(null); setFiltroLocalId(null); setFechaDesde(''); setFechaHasta('')
    setPagina(0)
    fetchMovimientos(0, { local_id: null, tipo_movimiento: null, fecha_desde: null, fecha_hasta: null })
  }

  const hayFiltrosActivos = filtroTipo || filtroLocalId || fechaDesde || fechaHasta

  const handleExportar = async () => {
    setLoadingExport(true)
    try {
      const blob = await api.exportarMovimientos({
        local_id: filtroLocalId, tipo_movimiento: filtroTipo,
        fecha_desde: fechaDesde || null, fecha_hasta: fechaHasta || null,
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `movimientos${fechaDesde ? `_${fechaDesde}` : ''}${fechaHasta ? `_a_${fechaHasta}` : ''}.xlsx`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      mostrarAlerta('error', `Error al exportar: ${err.message}`)
    } finally {
      setLoadingExport(false)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Historial de movimientos</h2>
        {total > 0 && <span className="total-badge">{total.toLocaleString()} registros</span>}
      </div>

      {alerta && <div className={`alerta alerta-${alerta.tipo}`}>{alerta.msg}</div>}

      <div className="lista-toolbar">
        <button className="btn btn-export" onClick={handleExportar} disabled={loadingExport}>
          {loadingExport ? 'Exportando...' : '⬇ Exportar Excel'}
        </button>
      </div>

      <div className="filtros-panel">
        <span className="filtros-label">Filtrar por:</span>

        <div className="filtros-row">
          <span className="filtros-sublabel">Tipo:</span>
          <div className="filtros-chips">
            {TIPOS_MOVIMIENTO.map(({ valor, label }) => (
              <button
                key={valor}
                className={`filtro-chip filtro-chip-mov-${valor.toLowerCase()} ${filtroTipo === valor ? 'filtro-chip-activo' : ''}`}
                onClick={() => handleFiltroTipo(valor)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {locales.length > 0 && (
          <div className="filtros-row">
            <span className="filtros-sublabel">Local:</span>
            <div className="filtros-chips">
              {locales.map(l => (
                <button
                  key={l.local_id}
                  className={`filtro-chip ${filtroLocalId === l.local_id ? 'filtro-chip-activo' : ''}`}
                  onClick={() => handleFiltroLocal(l.local_id)}
                >
                  {l.nombre}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="filtros-row filtros-fechas">
          <span className="filtros-sublabel">Fecha:</span>
          <div className="fecha-inputs">
            <div className="fecha-group">
              <label className="fecha-label">Desde</label>
              <input type="date" className="fecha-input" value={fechaDesde} onChange={handleFechaDesde} />
            </div>
            <span className="fecha-separador">—</span>
            <div className="fecha-group">
              <label className="fecha-label">Hasta</label>
              <input type="date" className="fecha-input" value={fechaHasta} onChange={handleFechaHasta} />
            </div>
          </div>
        </div>

        {hayFiltrosActivos && (
          <button className="btn-limpiar-filtros" onClick={limpiarFiltros}>✕ Limpiar filtros</button>
        )}
      </div>

      {loadingLista ? (
        <p className="empty-msg">Cargando...</p>
      ) : movimientos.length === 0 ? (
        <p className="empty-msg">No hay movimientos para los filtros seleccionados.</p>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="acc-table">
              <thead>
                <tr>
                  <th>ID</th><th>Fecha</th><th>SKU</th><th>Accesorio</th>
                  <th>Local</th><th>Tipo</th><th>Cantidad</th><th>Motivo</th>
                </tr>
              </thead>
              <tbody>
                {movimientos.map(mov => (
                  <tr key={mov.id} className={`mov-row-${mov.tipo_movimiento.toLowerCase()}`}>
                    <td className="mov-id">#{mov.id}</td>
                    <td className="mov-fecha">{formatFecha(mov.fecha)}</td>
                    <td>{mov.accesorio_sku ? <span className="sku-badge">{mov.accesorio_sku}</span> : '—'}</td>
                    <td>{mov.accesorio_nombre ?? '—'}</td>
                    <td>{mov.local_nombre ?? '—'}</td>
                    <td><span className={`tipo-badge ${CLASE_TIPO[mov.tipo_movimiento]}`}>{mov.tipo_movimiento}</span></td>
                    <td>
                      <span className={`cantidad-mov ${mov.cantidad > 0 ? 'cantidad-positiva' : 'cantidad-negativa'}`}>
                        {mov.cantidad > 0 ? `+${mov.cantidad}` : mov.cantidad}
                      </span>
                    </td>
                    <td className="mov-motivo" title={mov.motivo ?? ''}>{mov.motivo ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="paginacion">
            <button className="btn btn-secondary btn-sm" onClick={() => irAPagina(pagina - 1)} disabled={pagina === 0}>← Anterior</button>
            <span className="pagina-info">Página {pagina + 1}</span>
            <button className="btn btn-secondary btn-sm" onClick={() => irAPagina(pagina + 1)} disabled={!hayMas}>Siguiente →</button>
          </div>
        </>
      )}
    </div>
  )
}