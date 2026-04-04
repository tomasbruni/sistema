import { useEffect, useState } from 'react'
import './AccesoriosPage.css'
import { api, LIMIT } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'

const ESTADOS = ['PENDIENTE_APROBACION', 'APROBADO', 'ENTREGADO', 'RECHAZADO', 'CANCELADO']

const ESTADO_LABELS = {
  PENDIENTE_APROBACION: 'Pendiente',
  APROBADO: 'Aprobado',
  ENTREGADO: 'Entregado',
  RECHAZADO: 'Rechazado',
  CANCELADO: 'Cancelado',
}

const ESTADO_CLASSES = {
  PENDIENTE_APROBACION: 'badge-pendiente',
  APROBADO: 'badge-aprobado',
  ENTREGADO: 'badge-entregado',
  RECHAZADO: 'badge-rechazado',
  CANCELADO: 'badge-cancelado',
}

export default function PedidosOnlinePage() {
  const { alerta, mostrarAlerta } = useAlerta()

  const [pedidos, setPedidos] = useState([])
  const [loadingLista, setLoadingLista] = useState(false)
  const [pagina, setPagina] = useState(0)
  const [hayMas, setHayMas] = useState(false)
  const [filtroEstado, setFiltroEstado] = useState(null)

  const [pedidoDetalle, setPedidoDetalle] = useState(null)
  const [loadingDetalle, setLoadingDetalle] = useState(false)
  const [loadingAccion, setLoadingAccion] = useState(false)

  // Para aprobación
  const [locales, setLocales] = useState([])
  const [localStockId, setLocalStockId] = useState('')
  const [notasAdmin, setNotasAdmin] = useState('')

  useEffect(() => {
    fetchPedidos(0, filtroEstado)
    api.listarLocales().then(setLocales).catch(() => {})
  }, [])

  const fetchPedidos = async (pag, estado) => {
    setLoadingLista(true)
    try {
      const data = await api.listarPedidosOnline({
        skip: pag * LIMIT,
        limit: LIMIT + 1,
        estado: estado || null,
      })
      setHayMas(data.length > LIMIT)
      setPedidos(data.slice(0, LIMIT))
      setPagina(pag)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoadingLista(false)
    }
  }

  const handleFiltroEstado = (estado) => {
    const nuevo = filtroEstado === estado ? null : estado
    setFiltroEstado(nuevo)
    fetchPedidos(0, nuevo)
  }

  const abrirDetalle = async (pedido) => {
    setLoadingDetalle(true)
    setPedidoDetalle(null)
    setNotasAdmin('')
    setLocalStockId('')
    try {
      const data = await api.obtenerPedidoOnline(pedido.pedido_id)
      setPedidoDetalle(data)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoadingDetalle(false)
    }
  }

  const cerrarDetalle = () => {
    setPedidoDetalle(null)
    setNotasAdmin('')
    setLocalStockId('')
  }

  const handleAprobar = async () => {
    if (!localStockId) {
      mostrarAlerta('error', 'Debe seleccionar el local desde donde sale el stock.')
      return
    }
    setLoadingAccion(true)
    try {
      await api.aprobarPedido(pedidoDetalle.pedido_id, {
        local_stock_id: parseInt(localStockId),
        notas_admin: notasAdmin || null,
      })
      mostrarAlerta('success', 'Pedido aprobado y stock reservado.')
      cerrarDetalle()
      fetchPedidos(pagina, filtroEstado)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoadingAccion(false)
    }
  }

  const handleRechazar = async () => {
    if (!window.confirm('¿Rechazar este pedido?')) return
    setLoadingAccion(true)
    try {
      await api.rechazarPedido(pedidoDetalle.pedido_id, { notas_admin: notasAdmin || null })
      mostrarAlerta('success', 'Pedido rechazado.')
      cerrarDetalle()
      fetchPedidos(pagina, filtroEstado)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoadingAccion(false)
    }
  }

  const handleEntregar = async () => {
    if (!window.confirm('¿Marcar este pedido como entregado?')) return
    setLoadingAccion(true)
    try {
      await api.entregarPedido(pedidoDetalle.pedido_id)
      mostrarAlerta('success', 'Pedido marcado como entregado.')
      cerrarDetalle()
      fetchPedidos(pagina, filtroEstado)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoadingAccion(false)
    }
  }

  const handleCancelar = async () => {
    if (!window.confirm('¿Cancelar este pedido? El stock reservado se revertirá.')) return
    setLoadingAccion(true)
    try {
      await api.cancelarPedido(pedidoDetalle.pedido_id, { notas_admin: notasAdmin || null })
      mostrarAlerta('success', 'Pedido cancelado y stock revertido.')
      cerrarDetalle()
      fetchPedidos(pagina, filtroEstado)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoadingAccion(false)
    }
  }

  const irAPagina = (pag) => {
    if (pag < 0) return
    fetchPedidos(pag, filtroEstado)
  }

  const nombreLocal = (id) => locales.find(l => l.local_id === id)?.nombre || `Local ${id}`

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Pedidos Online</h2>
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.msg}</span>
        </div>
      )}

      {/* Panel de detalle */}
      {pedidoDetalle && (
        <div className="form-card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Pedido #{pedidoDetalle.pedido_id}</h3>
            <button className="btn btn-secondary btn-sm" onClick={cerrarDetalle}>✕ Cerrar</button>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Estado</label>
              <span className={`filtro-chip filtro-chip-activo ${ESTADO_CLASSES[pedidoDetalle.estado]}`}>
                {ESTADO_LABELS[pedidoDetalle.estado] || pedidoDetalle.estado}
              </span>
            </div>
            <div className="form-group">
              <label>Modo de entrega</label>
              <span>{pedidoDetalle.modo_entrega}</span>
            </div>
            <div className="form-group">
              <label>Pago</label>
              <span>{pedidoDetalle.medio_de_pago} — {pedidoDetalle.estado_pago}</span>
            </div>
            <div className="form-group">
              <label>Total</label>
              <span>${pedidoDetalle.monto_total?.toLocaleString()}</span>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Cliente</label>
              <span>{pedidoDetalle.nombre_cliente}</span>
            </div>
            <div className="form-group">
              <label>Teléfono</label>
              <span>{pedidoDetalle.telefono_cliente}</span>
            </div>
            {pedidoDetalle.mail_cliente && (
              <div className="form-group">
                <label>Email</label>
                <span>{pedidoDetalle.mail_cliente}</span>
              </div>
            )}
            {pedidoDetalle.local_retiro_id && (
              <div className="form-group">
                <label>Local de retiro</label>
                <span>{nombreLocal(pedidoDetalle.local_retiro_id)}</span>
              </div>
            )}
            {pedidoDetalle.direccion_envio && (
              <div className="form-group">
                <label>Dirección de envío</label>
                <span>{pedidoDetalle.direccion_envio}</span>
              </div>
            )}
            {pedidoDetalle.referencia_pago && (
              <div className="form-group">
                <label>Referencia MP</label>
                <span>{pedidoDetalle.referencia_pago}</span>
              </div>
            )}
          </div>

          {pedidoDetalle.notas_cliente && (
            <div className="form-group" style={{ marginBottom: '0.75rem' }}>
              <label>Notas del cliente</label>
              <span>{pedidoDetalle.notas_cliente}</span>
            </div>
          )}

          {pedidoDetalle.notas_admin && (
            <div className="form-group" style={{ marginBottom: '0.75rem' }}>
              <label>Notas admin</label>
              <span>{pedidoDetalle.notas_admin}</span>
            </div>
          )}

          {/* Productos */}
          {pedidoDetalle.detalles?.accesorios?.length > 0 && (
            <div style={{ marginBottom: '0.75rem' }}>
              <strong>Accesorios</strong>
              <table className="acc-table" style={{ marginTop: '0.5rem' }}>
                <thead><tr><th>ID</th><th>Cantidad</th><th>Precio lista</th></tr></thead>
                <tbody>
                  {pedidoDetalle.detalles.accesorios.map(d => (
                    <tr key={d.detalle_id}>
                      <td>{d.accesorio_id}</td>
                      <td>{d.cantidad}</td>
                      <td>${d.precio_lista?.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {pedidoDetalle.detalles?.celulares?.length > 0 && (
            <div style={{ marginBottom: '0.75rem' }}>
              <strong>Celulares</strong>
              <table className="acc-table" style={{ marginTop: '0.5rem' }}>
                <thead><tr><th>ID</th><th>IMEI</th></tr></thead>
                <tbody>
                  {pedidoDetalle.detalles.celulares.map(d => (
                    <tr key={d.detalle_id}>
                      <td>{d.celular_id}</td>
                      <td>{d.imei}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {pedidoDetalle.detalles?.chips?.length > 0 && (
            <div style={{ marginBottom: '0.75rem' }}>
              <strong>Chips</strong>
              <table className="acc-table" style={{ marginTop: '0.5rem' }}>
                <thead><tr><th>ID</th><th>N° serie</th></tr></thead>
                <tbody>
                  {pedidoDetalle.detalles.chips.map(d => (
                    <tr key={d.detalle_id}>
                      <td>{d.chip_id}</td>
                      <td>{d.numero_serie}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Acciones */}
          {pedidoDetalle.estado === 'PENDIENTE_APROBACION' && (
            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div className="form-row">
                <div className="form-group">
                  <label>Local desde donde sale el stock *</label>
                  <select
                    value={localStockId}
                    onChange={e => setLocalStockId(e.target.value)}
                    className="form-input"
                  >
                    <option value="">Seleccionar local...</option>
                    {locales.filter(l => l.activo).map(l => (
                      <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Notas admin (opcional)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={notasAdmin}
                    onChange={e => setNotasAdmin(e.target.value)}
                    placeholder="Notas internas..."
                  />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn btn-primary" onClick={handleAprobar} disabled={loadingAccion}>
                  {loadingAccion ? 'Procesando...' : 'Aprobar'}
                </button>
                <button className="btn btn-danger" onClick={handleRechazar} disabled={loadingAccion}>
                  Rechazar
                </button>
              </div>
            </div>
          )}

          {pedidoDetalle.estado === 'APROBADO' && (
            <div style={{ marginTop: '1rem' }}>
              <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                <label>Notas admin (opcional)</label>
                <input
                  type="text"
                  className="form-input"
                  value={notasAdmin}
                  onChange={e => setNotasAdmin(e.target.value)}
                  placeholder="Notas internas..."
                />
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn btn-primary" onClick={handleEntregar} disabled={loadingAccion}>
                  {loadingAccion ? 'Procesando...' : 'Marcar como entregado'}
                </button>
                <button className="btn btn-danger" onClick={handleCancelar} disabled={loadingAccion}>
                  Cancelar pedido
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {loadingDetalle && <p className="empty-msg">Cargando detalle...</p>}

      {/* Filtros */}
      <div className="filtros-panel">
        <span className="filtros-label">Estado:</span>
        <div className="filtros-chips">
          {ESTADOS.map(e => (
            <button
              key={e}
              className={`filtro-chip ${filtroEstado === e ? 'filtro-chip-activo' : ''}`}
              onClick={() => handleFiltroEstado(e)}
            >
              {ESTADO_LABELS[e]}
            </button>
          ))}
          {filtroEstado && (
            <button className="btn-limpiar-filtros" onClick={() => handleFiltroEstado(filtroEstado)}>
              ✕ Limpiar
            </button>
          )}
        </div>
      </div>

      {/* Tabla */}
      {loadingLista ? (
        <p className="empty-msg">Cargando...</p>
      ) : pedidos.length === 0 ? (
        <p className="empty-msg">No hay pedidos.</p>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="acc-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Cliente</th>
                  <th>Teléfono</th>
                  <th>Entrega</th>
                  <th>Pago</th>
                  <th>Total</th>
                  <th>Estado</th>
                  <th>Fecha</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {pedidos.map(p => (
                  <tr key={p.pedido_id}>
                    <td>#{p.pedido_id}</td>
                    <td>{p.nombre_cliente}</td>
                    <td>{p.telefono_cliente}</td>
                    <td>{p.modo_entrega === 'RETIRO_LOCAL' ? 'Retiro' : 'Envío'}</td>
                    <td>{p.medio_de_pago}</td>
                    <td>${p.monto_total?.toLocaleString()}</td>
                    <td>
                      <span className={`filtro-chip filtro-chip-activo ${ESTADO_CLASSES[p.estado]}`}>
                        {ESTADO_LABELS[p.estado] || p.estado}
                      </span>
                    </td>
                    <td>{p.fecha_creacion ? new Date(p.fecha_creacion).toLocaleDateString('es-AR') : '-'}</td>
                    <td className="acciones-cell">
                      <button className="btn btn-sm btn-secondary" onClick={() => abrirDetalle(p)}>
                        Ver
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="paginacion">
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => irAPagina(pagina - 1)}
              disabled={pagina === 0}
            >
              ← Anterior
            </button>
            <span className="pagina-info">Página {pagina + 1}</span>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => irAPagina(pagina + 1)}
              disabled={!hayMas}
            >
              Siguiente →
            </button>
          </div>
        </>
      )}
    </div>
  )
}
