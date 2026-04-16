import { useState, useEffect } from 'react'
import { api, LIMIT } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import { useAuth } from '../hooks/useAuth'
import { useModalDetalle } from '../hooks/ventas/useModalDetalles'
import { formatFecha } from '../helpers/formats'
import { descargarTransferenciaPdf } from '../helpers/pdf'
import ModalTransferencia from '../components/transferencias/ModalTransferencia'

export default function TransferenciasPage() {
  const { alerta, mostrarAlerta } = useAlerta()
  const { rol } = useAuth()

  const [transferencias, setTransferencias] = useState([])
  const [loadingLista, setLoadingLista]     = useState(false)
  const [pagina, setPagina]                 = useState(0)
  const [hayMas, setHayMas]                 = useState(false)

  const [locales, setLocales]               = useState([])
  const [usuarios, setUsuarios]             = useState([])

  const [fechaDesde, setFechaDesde]               = useState('')
  const [fechaHasta, setFechaHasta]               = useState('')
  const [filtroOrigenId, setFiltroOrigenId]       = useState('')
  const [filtroDestinoId, setFiltroDestinoId]     = useState('')
  const [filtroUsuarioId, setFiltroUsuarioId]     = useState('')

  const [loadingPdf, setLoadingPdf] = useState(null)

  const { modalAbierto, modalItem, loadingModal, abrirModal, cerrarModal } =
    useModalDetalle(api.getDetalleTransferencia)

  useEffect(() => {
    fetchTransferencias(0)
    if (rol === 'admin') {
      api.listarLocales().then(setLocales).catch(() => {})
    } else {
      api.listarLocales({tipo: 'LOCAL'}).then(setLocales).catch(() => {})
    } 
    if (rol === 'admin') api.listarUsuarios().then(setUsuarios).catch(() => {})
  }, [])

  const fetchTransferencias = async (pag, overrides = {}) => {
    setLoadingLista(true)
    const params = {
      skip:             pag * LIMIT,
      limit:            LIMIT + 1,
      fecha_desde:      fechaDesde || null,
      fecha_hasta:      fechaHasta || null,
      local_origen_id:  filtroOrigenId  || null,
      local_destino_id: filtroDestinoId || null,
      usuario_id:       filtroUsuarioId || null,
      ...overrides,
    }
    try {
      const data = await api.listarTransferencias(params)
      setHayMas(data.length > LIMIT)
      setTransferencias(data.slice(0, LIMIT))
    } catch (err) {
      mostrarAlerta('error', `Error al cargar transferencias: ${err.message}`)
    } finally {
      setLoadingLista(false)
    }
  }

  const irAPagina = (nueva) => { setPagina(nueva); fetchTransferencias(nueva) }

  const handleFiltro = (campo, valor) => {
    const overrides = { [campo]: valor || null }
    if (campo === 'fecha_desde')      setFechaDesde(valor)
    if (campo === 'fecha_hasta')      setFechaHasta(valor)
    if (campo === 'local_origen_id')  setFiltroOrigenId(valor)
    if (campo === 'local_destino_id') setFiltroDestinoId(valor)
    if (campo === 'usuario_id')       setFiltroUsuarioId(valor)
    setPagina(0)
    fetchTransferencias(0, overrides)
  }

  const handlePdf = async (transferencia_id) => {
    setLoadingPdf(transferencia_id)
    await descargarTransferenciaPdf(transferencia_id, (msg) => mostrarAlerta('error', msg))
    setLoadingPdf(null)
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Transferencias</h2>

        {/* Filtros */}
        <div className="form-row" style={{ padding: 5 }}>
          <div className="form-group" style={{ maxWidth: 200 }}>
            <label>Origen</label>
            <select
              value={filtroOrigenId}
              onChange={(e) => handleFiltro('local_origen_id', e.target.value)}
            >
              <option value="">Todos</option>
              {locales.map(l => (
                <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ maxWidth: 200 }}>
            <label>Destino</label>
            <select
              value={filtroDestinoId}
              onChange={(e) => handleFiltro('local_destino_id', e.target.value)}
            >
              <option value="">Todos</option>
              {locales.map(l => (
                <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
              ))}
            </select>
          </div>

          {rol === 'admin' && (
            <div className="form-group" style={{ maxWidth: 200 }}>
              <label>Usuario</label>
              <select
                value={filtroUsuarioId}
                onChange={(e) => handleFiltro('usuario_id', e.target.value)}
              >
                <option value="">Todos</option>
                {usuarios.map(u => (
                  <option key={u.usuario_id} value={u.usuario_id}>{u.nombre}</option>
                ))}
              </select>
            </div>
          )}

          <div className="form-group" style={{ maxWidth: 180 }}>
            <label>Desde</label>
            <input
              type="date"
              value={fechaDesde}
              onChange={(e) => handleFiltro('fecha_desde', e.target.value)}
            />
          </div>

          <div className="form-group" style={{ maxWidth: 180 }}>
            <label>Hasta</label>
            <input
              type="date"
              value={fechaHasta}
              onChange={(e) => handleFiltro('fecha_hasta', e.target.value)}
            />
          </div>
        </div>
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.msg}</span>
        </div>
      )}

      {loadingLista ? (
        <p className="empty-msg">Cargando...</p>
      ) : transferencias.length === 0 ? (
        <p className="empty-msg">No hay transferencias registradas.</p>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="acc-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Fecha</th>
                  <th>Emisor</th>
                  <th>Origen</th>
                  <th>Destino</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {transferencias.map(t => (
                  <tr key={t.transferencia_id}>
                    <td>{t.transferencia_id}</td>
                    <td>{formatFecha(t.fecha)}</td>
                    <td>{t.nombre_usuario ?? '—'}</td>
                    <td>{t.local_origen}</td>
                    <td>{t.local_destino}</td>
                    <td style={{ display: 'flex', gap: 6 }}>
                      <button
                        className="btn-ver-detalle"
                        onClick={() => abrirModal(t.transferencia_id)}
                        disabled={loadingModal}
                      >
                        {loadingModal ? 'Cargando...' : 'Ver detalle'}
                      </button>
                      <button
                        className="btn-ver-detalle"
                        onClick={() => handlePdf(t.transferencia_id)}
                        disabled={loadingPdf === t.transferencia_id}
                      >
                        {loadingPdf === t.transferencia_id ? 'Generando...' : 'PDF'}
                      </button>
                    </td>
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

      {modalAbierto && (
        <ModalTransferencia datos={modalItem} onClose={cerrarModal} />
      )}
    </div>
  )
}
