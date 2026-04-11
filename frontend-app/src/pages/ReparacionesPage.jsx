import React, { useEffect, useRef, useState } from 'react'
import './AccesoriosPage.css'
import { api } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import { useAuth } from '../hooks/useAuth'
import { useModalDetalle } from '../hooks/ventas/useModalDetalles'
import ModalHistorialReparaciones from '../components/reparaciones/ModalHistorialReparaciones'
import { formatFecha, formatPrecio } from '../helpers/formats'

const ESTADOS = ['EN_REPARACION', 'ENTREGADO', 'REPARACION_GARANTIA', 'ENTREGADO_GARANTIA']

const formCrearVacio = {
  celular:          '',
  nombre_cliente:   '',
  telefono_cliente: '',
  dni_cliente:      '',
  mail_cliente:     '',
  descripcion:      '',
  total:            '',
  adelanto:         '',
  local_id:         '',
  fecha_ingreso:    '',
  usuario_id:       '',
}

const formEditarVacio = {
  descripcion:      '',
  adelanto:         '',
  pago_reparador:   '',
  telefono_cliente: '',
  dni_cliente:      '',
  mail_cliente:     '',
}

export default function ReparacionesPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()
  const { rol }    = useAuth()
  const esAdmin    = rol === 'admin'

  const [reparaciones, setReparaciones]   = useState([])
  const [loadingLista, setLoadingLista]   = useState(false)
  const [locales, setLocales]             = useState([])
  const [usuarios, setUsuarios]           = useState([])

  // Filtros
  const [filtroLocalId, setFiltroLocalId]   = useState(null)
  const [filtroEstado, setFiltroEstado]     = useState(null)
  const [filtroUsuarioId, setFiltroUsuarioId] = useState(null)
  const [fechaDesde, setFechaDesde]         = useState('')
  const [fechaHasta, setFechaHasta]         = useState('')
  const [busqueda, setBusqueda]             = useState('')
  const debounceRef                         = useRef(null)

  // Formulario crear
  const [mostrarCrear, setMostrarCrear]   = useState(false)
  const [formCrear, setFormCrear]         = useState(formCrearVacio)
  const [loadingCrear, setLoadingCrear]   = useState(false)

  // Formulario editar
  const [editandoId, setEditandoId]       = useState(null)
  const [formEditar, setFormEditar]       = useState(formEditarVacio)
  const [loadingEditar, setLoadingEditar] = useState(false)

  // Modal agregar monto
  const [montoRepId, setMontoRepId]       = useState(null)
  const [montoAgregar, setMontoAgregar]   = useState('')
  const [montoObs, setMontoObs]           = useState('')
  const [montoFecha, setMontoFecha]       = useState('')
  const [montoUsuarioId, setMontoUsuarioId] = useState('')
  const [loadingMonto, setLoadingMonto]   = useState(false)

  // Modal transición (entregar / garantia / entregar-garantia)
  const [transRepId, setTransRepId]       = useState(null)
  const [transAccion, setTransAccion]     = useState(null) // 'entregar'|'garantia'|'entregar-garantia'
  const [transObs, setTransObs]           = useState('')
  const [transFecha, setTransFecha]       = useState('')
  const [transUsuarioId, setTransUsuarioId] = useState('')
  const [loadingTrans, setLoadingTrans]   = useState(false)

  // Historial
  const [historialRep, setHistorialRep] = useState(null) // reparacion completa para el modal
  const { modalItem: historial, loadingModal: loadingHistorial, abrirModal: abrirHistorial, cerrarModal: cerrarHistorial } =
    useModalDetalle((repId) => api.obtenerHistorialReparacion(repId))

  useEffect(() => {
    fetchReparaciones()
    api.listarLocales({tipo: 'LOCAL'}).then(setLocales).catch(() => {})
    api.listarUsuarios().then(setUsuarios).catch(() => {})
  }, [])

  // ── Fetch ─────────────────────────────────────────────────────────────────

  const fetchReparaciones = async (
    localId   = filtroLocalId,
    estado    = filtroEstado,
    usuarioId = filtroUsuarioId,
    dni       = busqueda,
    desde     = fechaDesde,
    hasta     = fechaHasta,
  ) => {
    setLoadingLista(true)
    try {
      const data = await api.listarReparaciones({
        local_id: localId, estado,
        usuario_id: usuarioId,
        dni_cliente: dni || null,
        fecha_desde: desde || null,
        fecha_hasta: hasta || null,
      })
      setReparaciones(data)
    } catch (err) {
      mostrarAlerta('error', `Error al cargar reparaciones: ${err.message}`)
    } finally {
      setLoadingLista(false)
    }
  }

  // ── Filtros ───────────────────────────────────────────────────────────────

  const handleBusqueda = (e) => {
    const val = e.target.value
    setBusqueda(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() =>
      fetchReparaciones(filtroLocalId, filtroEstado, filtroUsuarioId, val, fechaDesde, fechaHasta), 400)
  }

  const handleFiltroLocal = (localId) => {
    const nuevo = filtroLocalId === localId ? null : localId
    setFiltroLocalId(nuevo)
    fetchReparaciones(nuevo, filtroEstado, filtroUsuarioId, busqueda, fechaDesde, fechaHasta)
  }

  const handleFiltroEstado = (estado) => {
    const nuevo = filtroEstado === estado ? null : estado
    setFiltroEstado(nuevo)
    fetchReparaciones(filtroLocalId, nuevo, filtroUsuarioId, busqueda, fechaDesde, fechaHasta)
  }

  const handleFiltroUsuario = (usuarioId) => {
    const nuevo = filtroUsuarioId === usuarioId ? null : usuarioId
    setFiltroUsuarioId(nuevo)
    fetchReparaciones(filtroLocalId, filtroEstado, nuevo, busqueda, fechaDesde, fechaHasta)
  }

  const handleFechaDesde = (e) => {
    const val = e.target.value
    setFechaDesde(val)
    fetchReparaciones(filtroLocalId, filtroEstado, filtroUsuarioId, busqueda, val, fechaHasta)
  }

  const handleFechaHasta = (e) => {
    const val = e.target.value
    setFechaHasta(val)
    fetchReparaciones(filtroLocalId, filtroEstado, filtroUsuarioId, busqueda, fechaDesde, val)
  }

  const limpiarFiltros = () => {
    setFiltroLocalId(null); setFiltroEstado(null); setFiltroUsuarioId(null)
    setFechaDesde(''); setFechaHasta(''); setBusqueda('')
    fetchReparaciones(null, null, null, '', '', '')
  }

  // ── Crear ─────────────────────────────────────────────────────────────────

  const handleSubmitCrear = async (e) => {
    e.preventDefault()
    setLoadingCrear(true)
    try {
      await api.crearReparacion({
        celular:          formCrear.celular.trim(),
        nombre_cliente:   formCrear.nombre_cliente.trim(),
        telefono_cliente: formCrear.telefono_cliente.trim(),
        dni_cliente:      formCrear.dni_cliente.trim() || null,
        mail_cliente:     formCrear.mail_cliente.trim() || null,
        descripcion:      formCrear.descripcion.trim() || null,
        total:            Number(formCrear.total),
        adelanto:         Number(formCrear.adelanto),
        local_id:         Number(formCrear.local_id),
        ...(esAdmin && formCrear.fecha_ingreso ? { fecha_ingreso: formCrear.fecha_ingreso } : {}),
        ...(esAdmin && formCrear.usuario_id    ? { usuario_id: Number(formCrear.usuario_id) } : {}),
      })
      mostrarAlerta('success', 'Reparación creada correctamente.')
      setMostrarCrear(false)
      setFormCrear(formCrearVacio)
      fetchReparaciones()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingCrear(false)
    }
  }

  // ── Editar ────────────────────────────────────────────────────────────────

  const abrirEditar = (rep) => {
    cerrarTodo()
    setFormEditar({
      descripcion:      rep.descripcion ?? '',
      adelanto:         rep.adelanto,
      pago_reparador:   rep.pago_reparador ?? '',
      telefono_cliente: rep.telefono_cliente,
      dni_cliente:      rep.dni_cliente ?? '',
      mail_cliente:     rep.mail_cliente ?? '',
    })
    setEditandoId(rep.reparacion_id)
  }

  const handleSubmitEditar = async (e) => {
    e.preventDefault()
    setLoadingEditar(true)
    try {
      const body = {
        descripcion:      formEditar.descripcion || null,
        adelanto:         Number(formEditar.adelanto),
        telefono_cliente: formEditar.telefono_cliente.trim(),
        dni_cliente:      formEditar.dni_cliente.trim() || null,
        mail_cliente:     formEditar.mail_cliente.trim() || null,
      }
      if (esAdmin && formEditar.pago_reparador !== '') {
        body.pago_reparador = Number(formEditar.pago_reparador)
      }
      await api.actualizarReparacion(editandoId, body)
      mostrarAlerta('success', 'Reparación actualizada correctamente.')
      setEditandoId(null)
      fetchReparaciones()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingEditar(false)
    }
  }

  // ── Agregar monto ─────────────────────────────────────────────────────────

  const handleSubmitMonto = async (e) => {
    e.preventDefault()
    setLoadingMonto(true)
    try {
      await api.cambiarPrecioReparacion(montoRepId, {
        monto_agregado: Number(montoAgregar),
        observaciones:  montoObs.trim() || null,
        ...(esAdmin && montoFecha     ? { fecha: montoFecha } : {}),
        ...(esAdmin && montoUsuarioId ? { usuario_id: Number(montoUsuarioId) } : {}),
      })
      mostrarAlerta('success', 'Monto actualizado correctamente.')
      setMontoRepId(null); setMontoAgregar(''); setMontoObs(''); setMontoFecha(''); setMontoUsuarioId('')
      fetchReparaciones()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingMonto(false)
    }
  }

  // ── Transiciones ──────────────────────────────────────────────────────────

  const abrirTransicion = (repId, accion) => {
    cerrarTodo()
    setTransRepId(repId)
    setTransAccion(accion)
  }

  const handleSubmitTransicion = async (e) => {
    e.preventDefault()
    setLoadingTrans(true)
    const body = {
      observaciones: transObs.trim() || null,
      ...(esAdmin && transFecha     ? { fecha: transFecha } : {}),
      ...(esAdmin && transUsuarioId ? { usuario_id: Number(transUsuarioId) } : {}),
    }
    try {
      if (transAccion === 'entregar')          await api.entregarReparacion(transRepId, body)
      else if (transAccion === 'garantia')     await api.garantiaReparacion(transRepId, body)
      else if (transAccion === 'entregar-garantia') await api.entregarGarantiaReparacion(transRepId, body)
      mostrarAlerta('success', 'Reparación actualizada correctamente.')
      setTransRepId(null); setTransAccion(null)
      fetchReparaciones()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingTrans(false)
    }
  }

  // ── Historial ─────────────────────────────────────────────────────────────

  const verHistorial = (rep) => {
    cerrarTodo()
    setHistorialRep(rep)
    abrirHistorial(rep.reparacion_id)
  }

  // ── Cerrar todo ───────────────────────────────────────────────────────────

  const cerrarTodo = () => {
    setMostrarCrear(false)
    setFormCrear(formCrearVacio)
    setEditandoId(null)
    setMontoRepId(null); setMontoAgregar(''); setMontoObs(''); setMontoFecha(''); setMontoUsuarioId('')
    setTransRepId(null); setTransAccion(null); setTransObs(''); setTransFecha(''); setTransUsuarioId('')
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  const descargarPdf = async (apiFn, filename) => {
    try {
      const blob = await apiFn()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    }
  }

  const nombreUsuario = (id) => usuarios.find(u => u.usuario_id === id)?.nombre ?? id

  const estadoClase = (estado) => ({
    EN_REPARACION:     'activo',
    REPARACION_GARANTIA: 'activo',
    ENTREGADO:         'inactivo',
    ENTREGADO_GARANTIA: 'inactivo',
  }[estado] ?? '')

  const labelTransicion = (accion) => ({
    'entregar':          'Entregar',
    'garantia':          'Enviar a garantía',
    'entregar-garantia': 'Entregar garantía',
  }[accion] ?? accion)


  // ─── RENDER ───────────────────────────────────────────────────────────────
  return (
    <div className="page-container" style={{ maxWidth: '100%' }}>
      <div className="page-header">
        <h2>Reparaciones</h2>
        {!mostrarCrear && (
          <button className="btn btn-primary" onClick={() => { cerrarTodo(); setMostrarCrear(true) }}>+ Nueva reparacion</button>
        )}
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          {alerta.msg}
          <button className="alerta-cerrar" onClick={cerrarAlerta}>&times;</button>
        </div>
      )}

      {/* ── Formulario crear ── */}
      {mostrarCrear && (
        <div className="form-card">
          <h3>Nueva reparacion</h3>
          <form onSubmit={handleSubmitCrear} className="acc-form">
            <div className="form-row">
              <div className="form-group">
                <label>Celular (marca y modelo) *</label>
                <input name="celular" value={formCrear.celular}
                  onChange={e => setFormCrear(p => ({ ...p, celular: e.target.value }))}
                  required placeholder="Ej: Samsung Galaxy S24" />
              </div>
              <div className="form-group">
                <label>Local *</label>
                <select value={formCrear.local_id}
                  onChange={e => setFormCrear(p => ({ ...p, local_id: e.target.value }))} required>
                  <option value="">Seleccionar local...</option>
                  {locales.map(l => <option key={l.local_id} value={l.local_id}>{l.nombre}</option>)}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Nombre del cliente *</label>
                <input value={formCrear.nombre_cliente}
                  onChange={e => setFormCrear(p => ({ ...p, nombre_cliente: e.target.value }))}
                  required placeholder="Nombre completo" />
              </div>
              <div className="form-group">
                <label>Telefono del cliente *</label>
                <input value={formCrear.telefono_cliente}
                  onChange={e => setFormCrear(p => ({ ...p, telefono_cliente: e.target.value }))}
                  required placeholder="Ej: 11-1234-5678" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>DNI del cliente</label>
                <input value={formCrear.dni_cliente}
                  onChange={e => setFormCrear(p => ({ ...p, dni_cliente: e.target.value }))}
                  placeholder="Ej: 12345678" />
              </div>
              <div className="form-group">
                <label>Mail del cliente</label>
                <input type="email" value={formCrear.mail_cliente}
                  onChange={e => setFormCrear(p => ({ ...p, mail_cliente: e.target.value }))}
                  placeholder="cliente@mail.com" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group" style={{ flex: 1 }}>
                <label>Descripcion del arreglo</label>
                <input value={formCrear.descripcion}
                  onChange={e => setFormCrear(p => ({ ...p, descripcion: e.target.value }))}
                  placeholder="Ej: cambio de módulo" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Total *</label>
                <input type="number" value={formCrear.total}
                  onChange={e => setFormCrear(p => ({ ...p, total: e.target.value }))}
                  required min={0} placeholder="Monto total" />
              </div>
              <div className="form-group">
                <label>Adelanto *</label>
                <input type="number" value={formCrear.adelanto}
                  onChange={e => setFormCrear(p => ({ ...p, adelanto: e.target.value }))}
                  required min={0} placeholder="Monto adelanto" />
              </div>
            </div>
            {esAdmin && (
              <div className="form-row">
                <div className="form-group">
                  <label>Fecha de ingreso</label>
                  <input type="date" value={formCrear.fecha_ingreso}
                    onChange={e => setFormCrear(p => ({ ...p, fecha_ingreso: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Vendedor/a</label>
                  <select value={formCrear.usuario_id}
                    onChange={e => setFormCrear(p => ({ ...p, usuario_id: e.target.value }))}>
                    <option value="">Usuario actual</option>
                    {usuarios.map(u => (
                      <option key={u.usuario_id} value={u.usuario_id}>{u.nombre}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}
            <div className="form-actions">
              <button type="button" className="btn btn-secondary"
                onClick={() => { setMostrarCrear(false); setFormCrear(formCrearVacio) }}
                disabled={loadingCrear}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loadingCrear}>
                {loadingCrear ? 'Guardando...' : 'Crear reparacion'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Formulario editar (inline sobre la fila) ── */}
      {editandoId && (
        <div className="form-card">
          <h3>Editar reparacion #{editandoId}</h3>
          <form onSubmit={handleSubmitEditar} className="acc-form">
            <div className="form-row">
              <div className="form-group">
                <label>Telefono del cliente *</label>
                <input value={formEditar.telefono_cliente}
                  onChange={e => setFormEditar(p => ({ ...p, telefono_cliente: e.target.value }))}
                  required />
              </div>
              <div className="form-group">
                <label>DNI del cliente</label>
                <input value={formEditar.dni_cliente}
                  onChange={e => setFormEditar(p => ({ ...p, dni_cliente: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Mail del cliente</label>
                <input type="email" value={formEditar.mail_cliente}
                  onChange={e => setFormEditar(p => ({ ...p, mail_cliente: e.target.value }))} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group" style={{ flex: 1 }}>
                <label>Descripcion</label>
                <input value={formEditar.descripcion}
                  onChange={e => setFormEditar(p => ({ ...p, descripcion: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Adelanto</label>
                <input type="number" value={formEditar.adelanto} min={0}
                  onChange={e => setFormEditar(p => ({ ...p, adelanto: e.target.value }))} />
              </div>
              {esAdmin && (
                <div className="form-group">
                  <label>Pago al reparador</label>
                  <input type="number" value={formEditar.pago_reparador} min={0}
                    placeholder="Completar cuando este listo"
                    onChange={e => setFormEditar(p => ({ ...p, pago_reparador: e.target.value }))} />
                </div>
              )}
            </div>
            <div className="form-actions">
              <button type="button" className="btn btn-secondary"
                onClick={() => setEditandoId(null)} disabled={loadingEditar}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loadingEditar}>
                {loadingEditar ? 'Guardando...' : 'Guardar cambios'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Modal agregar monto ── */}
      {montoRepId && (
        <div className="form-card">
          <h3>Agregar monto — reparacion #{montoRepId}</h3>
          <form onSubmit={handleSubmitMonto} className="acc-form">
            <div className="form-row">
              <div className="form-group">
                <label>Monto a agregar *</label>
                <input type="number" value={montoAgregar} min={1} required
                  onChange={e => setMontoAgregar(e.target.value)} placeholder="Ej: 5000" />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Observaciones</label>
                <input value={montoObs}
                  onChange={e => setMontoObs(e.target.value)} placeholder="Motivo (opcional)" />
              </div>
            </div>
            {esAdmin && (
              <div className="form-row">
                <div className="form-group">
                  <label>Fecha</label>
                  <input type="date" value={montoFecha}
                    onChange={e => setMontoFecha(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Vendedor/a</label>
                  <select value={montoUsuarioId} onChange={e => setMontoUsuarioId(e.target.value)}>
                    <option value="">Usuario actual</option>
                    {usuarios.map(u => (
                      <option key={u.usuario_id} value={u.usuario_id}>{u.nombre}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}
            <div className="form-actions">
              <button type="button" className="btn btn-secondary"
                onClick={() => { setMontoRepId(null); setMontoAgregar(''); setMontoObs(''); setMontoFecha(''); setMontoUsuarioId('') }}
                disabled={loadingMonto}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loadingMonto}>
                {loadingMonto ? 'Guardando...' : 'Confirmar'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Modal transición ── */}
      {transRepId && (
        <div className="form-card">
          <h3>{labelTransicion(transAccion)} — reparacion #{transRepId}</h3>
          <form onSubmit={handleSubmitTransicion} className="acc-form">
            <div className="form-row">
              <div className="form-group" style={{ flex: 1 }}>
                <label>Observaciones</label>
                <input value={transObs}
                  onChange={e => setTransObs(e.target.value)} placeholder="Opcional" />
              </div>
            </div>
            {esAdmin && (
              <div className="form-row">
                <div className="form-group">
                  <label>Fecha</label>
                  <input type="date" value={transFecha}
                    onChange={e => setTransFecha(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Vendedor/a</label>
                  <select value={transUsuarioId} onChange={e => setTransUsuarioId(e.target.value)}>
                    <option value="">Usuario actual</option>
                    {usuarios.map(u => (
                      <option key={u.usuario_id} value={u.usuario_id}>{u.nombre}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}
            <div className="form-actions">
              <button type="button" className="btn btn-secondary"
                onClick={() => { setTransRepId(null); setTransAccion(null) }}
                disabled={loadingTrans}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loadingTrans}>
                {loadingTrans ? 'Guardando...' : labelTransicion(transAccion)}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Buscador y filtros ── */}
      {!mostrarCrear && !editandoId && !montoRepId && !transRepId && (
        <>
          <div className="lista-toolbar">
            <input className="buscador" type="search"
              placeholder="Buscar por DNI del cliente..."
              value={busqueda} onChange={handleBusqueda} />
          </div>
          <div className="filtros-panel">
            <span className="filtros-label">Filtrar por:</span>
            {locales.length > 0 && (
              <div className="filtros-row">
                <span className="filtros-sublabel">Local:</span>
                <div className="filtros-chips">
                  {locales.map(l => (
                    <button key={l.local_id}
                      className={`filtro-chip ${filtroLocalId === l.local_id ? 'filtro-chip-activo' : ''}`}
                      onClick={() => handleFiltroLocal(l.local_id)}>{l.nombre}</button>
                  ))}
                </div>
              </div>
            )}
            {esAdmin && usuarios.length > 0 && (
              <div className="filtros-row">
                <span className="filtros-sublabel">Vendedor/a:</span>
                <div className="filtros-chips">
                  {usuarios.map(u => (
                    <button key={u.usuario_id}
                      className={`filtro-chip ${filtroUsuarioId === u.usuario_id ? 'filtro-chip-activo' : ''}`}
                      onClick={() => handleFiltroUsuario(u.usuario_id)}>{u.nombre}</button>
                  ))}
                </div>
              </div>
            )}
            <div className="filtros-row">
              <span className="filtros-sublabel">Estado:</span>
              <div className="filtros-chips">
                {ESTADOS.map(e => (
                  <button key={e}
                    className={`filtro-chip filtro-chip-estado ${filtroEstado === e ? 'filtro-chip-activo' : ''}`}
                    onClick={() => handleFiltroEstado(e)}>{e.replace(/_/g, ' ')}</button>
                ))}
              </div>
            </div>
            <div className="filtros-row">
              <span className="filtros-sublabel">Fecha:</span>
              <div className="filtros-chips">
                <input type="date" value={fechaDesde} onChange={handleFechaDesde} />
                <input type="date" value={fechaHasta} onChange={handleFechaHasta} />
              </div>
            </div>
            {(filtroLocalId || filtroEstado || filtroUsuarioId || fechaDesde || fechaHasta || busqueda) && (
              <button className="btn-limpiar-filtros" onClick={limpiarFiltros}>Limpiar filtros</button>
            )}
          </div>
        </>
      )}

      {/* ── Tabla ── */}
      {loadingLista ? (
        <p className="empty-msg">Cargando...</p>
      ) : reparaciones.length === 0 ? (
        <p className="empty-msg">No hay reparaciones registradas.</p>
      ) : (
        <div className="table-wrapper">
          <table className="acc-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Fecha</th>
                <th>Celular</th>
                <th>Cliente</th>
                <th>Total</th>
                <th>Adelanto</th>
                {esAdmin && <th>Pago reparador</th>}
                <th>Estado</th>
                <th>Vendedor/a</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {reparaciones.map(rep => (
                <React.Fragment key={rep.reparacion_id}>
                  <tr>
                    <td>{rep.reparacion_id}</td>
                    <td>{formatFecha(rep.fecha_ingreso)}</td>
                    <td>{rep.celular}</td>
                    <td>{rep.nombre_cliente}</td>
                    <td>{formatPrecio(rep.total)}</td>
                    <td>{formatPrecio(rep.adelanto)}</td>
                    {esAdmin && <td>{rep.pago_reparador != null ? formatPrecio(rep.pago_reparador) : '-'}</td>}
                    <td>
                      <span className={`estado-badge ${estadoClase(rep.estado)}`}>
                        {rep.estado.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>{nombreUsuario(rep.usuario_id)}</td>
                    <td className="acciones-cell">
                      <button className="btn btn-sm btn-secondary"
                        onClick={() => abrirEditar(rep)}>Editar</button>

                      <button className="btn btn-sm btn-secondary"
                        onClick={() => { cerrarTodo(); setMontoRepId(rep.reparacion_id) }}>
                        + Monto
                      </button>

                      {rep.estado === 'EN_REPARACION' && (
                        <button className="btn btn-sm btn-primary"
                          onClick={() => abrirTransicion(rep.reparacion_id, 'entregar')}>
                          Entregar
                        </button>
                      )}

                      {rep.estado === 'REPARACION_GARANTIA' && (
                        <button className="btn btn-sm btn-primary"
                          onClick={() => abrirTransicion(rep.reparacion_id, 'entregar-garantia')}>
                          Entregar garantia
                        </button>
                      )}


                      {(rep.estado === 'ENTREGADO' || rep.estado === 'ENTREGADO_GARANTIA') && (
                        <>
                          <button className="btn btn-sm btn-secondary btn-danger"
                            onClick={() => abrirTransicion(rep.reparacion_id, 'garantia')}>
                            Devolucion
                          </button>
                          <button className="btn btn-sm btn-secondary"
                            onClick={() => descargarPdf(
                              () => api.descargarCertificadoGarantia(rep.reparacion_id),
                              `garantia_${String(rep.reparacion_id).padStart(4, '0')}.pdf`
                            )}>
                            Cert. Garantía
                          </button>
                        </>
                      )}

                      <button className="btn btn-sm btn-secondary"
                        onClick={() => descargarPdf(
                          () => api.descargarCertificadoRecepcion(rep.reparacion_id),
                          `recepcion_${String(rep.reparacion_id).padStart(4, '0')}.pdf`
                        )}>
                        Cert. Recepción
                      </button>


                      <button className="btn btn-sm btn-secondary"
                        onClick={() => verHistorial(rep)}>
                        Historial
                      </button>
                    </td>
                  </tr>
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ModalHistorialReparaciones
        reparacion={historialRep}
        historial={historial ?? []}
        nombreUsuario={nombreUsuario}
        onClose={() => { cerrarHistorial(); setHistorialRep(null) }}
      />
    </div>
  )
}
