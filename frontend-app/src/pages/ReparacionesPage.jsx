import React, { useEffect, useRef, useState } from 'react'
import './AccesoriosPage.css'
import { api, LIMIT } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import { useAuth } from '../hooks/useAuth'
import { useModalDetalle } from '../hooks/ventas/useModalDetalles'
import ModalHistorialReparaciones from '../components/reparaciones/ModalHistorialReparaciones'
import { formatFecha, formatFechaCorta, formatPrecio } from '../helpers/formats'

const ESTADOS = ['EN_REVISION', 'EN_REPARACION', 'ENTREGADO', 'CANCELADO', 'REPARACION_GARANTIA', 'ENTREGADO_GARANTIA']

const formCrearVacio = {
  estado_inicial:   'EN_REVISION',
  celular:          '',
  nombre_cliente:   '',
  telefono_cliente: '',
  dni_cliente:      '',
  mail_cliente:     '',
  descripcion:      '',
  total:            '',
  pago_parcial:     '',
  local_id:         '',
  fecha_ingreso:    '',
  usuario_id:       '',
}

const formEditarVacio = {
  descripcion:      '',
  pago_parcial:     '',
  pago_reparador:   '',
  pagado:           false,
  telefono_cliente: '',
  dni_cliente:      '',
  mail_cliente:     '',
}

export default function ReparacionesPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()
  const { rol, usuarioId } = useAuth()
  const esAdmin            = rol === 'admin'

  const [reparaciones, setReparaciones]   = useState([])
  const [loadingLista, setLoadingLista]   = useState(false)
  const [locales, setLocales]             = useState([])
  const [usuarios, setUsuarios]           = useState([])

  // Filtros
  const [filtroLocalId, setFiltroLocalId]     = useState(null)
  const [filtroEstado, setFiltroEstado]       = useState(null)
  const [filtroUsuarioId, setFiltroUsuarioId] = useState(null)
  const [filtroPagado, setFiltroPagado]       = useState(null)
  const [fechaDesde, setFechaDesde]           = useState('')
  const [fechaHasta, setFechaHasta]           = useState('')
  const [busqueda, setBusqueda]               = useState('')
  const debounceRef                           = useRef(null)

  // Paginación
  const [pagina, setPagina] = useState(0)
  const [hayMas, setHayMas] = useState(false)

  // Formulario crear
  const [mostrarCrear, setMostrarCrear] = useState(false)
  const [formCrear, setFormCrear]       = useState(formCrearVacio)
  const [loadingCrear, setLoadingCrear] = useState(false)

  // Formulario editar
  const [editandoId, setEditandoId]       = useState(null)
  const [formEditar, setFormEditar]       = useState(formEditarVacio)
  const [loadingEditar, setLoadingEditar] = useState(false)

  // Modal agregar monto
  const [montoRepId, setMontoRepId]     = useState(null)
  const [montoAgregar, setMontoAgregar] = useState('')
  const [montoObs, setMontoObs]         = useState('')
  const [loadingMonto, setLoadingMonto] = useState(false)

  // Modal cambio pago parcial
  const [cambioPagoRepId, setCambioPagoRepId]     = useState(null)
  const [cambioPagoMonto, setCambioPagoMonto]     = useState('')
  const [cambioPagoObs, setCambioPagoObs]         = useState('')
  const [loadingCambioPago, setLoadingCambioPago] = useState(false)

  // Modal aceptar (EN_REVISION → EN_REPARACION)
  const [aceptarRepId, setAceptarRepId]             = useState(null)
  const [aceptarTotal, setAceptarTotal]             = useState('')
  const [aceptarPagoParcial, setAceptarPagoParcial] = useState('')
  const [aceptarObs, setAceptarObs]                 = useState('')
  const [loadingAceptar, setLoadingAceptar]         = useState(false)

  // Modal cancelar
  const [cancelarRepId, setCancelarRepId]     = useState(null)
  const [cancelarMonto, setCancelarMonto]     = useState('')
  const [cancelarObs, setCancelarObs]         = useState('')
  const [loadingCancelar, setLoadingCancelar] = useState(false)

  // Modal transición (entregar / garantia / entregar-garantia)
  const [transRepId, setTransRepId]     = useState(null)
  const [transAccion, setTransAccion]   = useState(null)
  const [transObs, setTransObs]         = useState('')
  const [loadingTrans, setLoadingTrans] = useState(false)

  // Campos admin compartidos — solo un modal abierto a la vez
  const [adminFecha, setAdminFecha]         = useState('')
  const [adminUsuarioId, setAdminUsuarioId] = useState('')

  // Historial
  const [historialRep, setHistorialRep] = useState(null)
  const { modalItem: historial, abrirModal: abrirHistorial, cerrarModal: cerrarHistorial } =
    useModalDetalle((repId) => api.obtenerHistorialReparacion(repId))

  useEffect(() => {
    fetchReparaciones()
    api.listarLocales({tipo: 'LOCAL'}).then(setLocales).catch(() => {})
    api.listarUsuarios().then(setUsuarios).catch(() => {})
  }, [])

  // ── Fetch ─────────────────────────────────────────────────────────────────

  const fetchReparaciones = async (pag = pagina, overrides = {}) => {
    setLoadingLista(true)
    const params = {
      skip:        pag * LIMIT,
      limit:       LIMIT + 1,  // +1 para detectar si hay página siguiente
      local_id:    filtroLocalId,
      estado:      filtroEstado,
      usuario_id:  filtroUsuarioId,
      dni_cliente: busqueda || null,
      fecha_desde: fechaDesde || null,
      fecha_hasta: fechaHasta || null,
      pagado:      filtroPagado,
      ...overrides,
    }
    try {
      const data = await api.listarReparaciones(params)
      setHayMas(data.length > LIMIT)
      setReparaciones(data.slice(0, LIMIT))
    } catch (err) {
      mostrarAlerta('error', `Error al cargar reparaciones: ${err.message}`)
    } finally {
      setLoadingLista(false)
    }
  }

  // ── Filtros ───────────────────────────────────────────────────────────────

  const irAPagina = (nueva) => { setPagina(nueva); fetchReparaciones(nueva) }

  // Al cambiar un filtro siempre se vuelve a la primera página
  const aplicarFiltros = (overrides = {}) => { setPagina(0); fetchReparaciones(0, overrides) }

  const handleBusqueda = (e) => {
    const val = e.target.value
    setBusqueda(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => aplicarFiltros({ dni_cliente: val || null }), 400)
  }

  const handleFiltroLocal = (localId) => {
    const nuevo = filtroLocalId === localId ? null : localId
    setFiltroLocalId(nuevo)
    aplicarFiltros({ local_id: nuevo })
  }

  const handleFiltroEstado = (estado) => {
    const nuevo = filtroEstado === estado ? null : estado
    setFiltroEstado(nuevo)
    aplicarFiltros({ estado: nuevo })
  }

  const handleFiltroUsuario = (usuarioId) => {
    const nuevo = filtroUsuarioId === usuarioId ? null : usuarioId
    setFiltroUsuarioId(nuevo)
    aplicarFiltros({ usuario_id: nuevo })
  }

  const handleFiltroPagado = (valor) => {
    const nuevo = filtroPagado === valor ? null : valor
    setFiltroPagado(nuevo)
    aplicarFiltros({ pagado: nuevo })
  }

  const handleFechaDesde = (e) => {
    const val = e.target.value
    setFechaDesde(val)
    aplicarFiltros({ fecha_desde: val || null })
  }

  const handleFechaHasta = (e) => {
    const val = e.target.value
    setFechaHasta(val)
    aplicarFiltros({ fecha_hasta: val || null })
  }

  const limpiarFiltros = () => {
    setFiltroLocalId(null); setFiltroEstado(null); setFiltroUsuarioId(null)
    setFiltroPagado(null)
    setFechaDesde(''); setFechaHasta(''); setBusqueda('')
    setPagina(0)
    fetchReparaciones(0, {
      local_id: null, estado: null, usuario_id: null,
      dni_cliente: null, fecha_desde: null, fecha_hasta: null, pagado: null,
    })
  }

  // ── Crear ─────────────────────────────────────────────────────────────────

  const handleSubmitCrear = async (e) => {
    e.preventDefault()
    setLoadingCrear(true)
    const esRevision = formCrear.estado_inicial === 'EN_REVISION'
    try {
      const res = await api.crearReparacion({
        estado_inicial:   formCrear.estado_inicial,
        celular:          formCrear.celular.trim(),
        nombre_cliente:   formCrear.nombre_cliente.trim(),
        telefono_cliente: formCrear.telefono_cliente.trim(),
        dni_cliente:      formCrear.dni_cliente.trim() || null,
        mail_cliente:     formCrear.mail_cliente.trim() || null,
        descripcion:      formCrear.descripcion.trim() || null,
        total:            esRevision ? null : Number(formCrear.total),
        pago_parcial:     Number(formCrear.pago_parcial),
        local_id:         Number(formCrear.local_id),
        ...(esAdmin && formCrear.fecha_ingreso ? { fecha_ingreso: formCrear.fecha_ingreso } : {}),
        ...(esAdmin && formCrear.usuario_id    ? { usuario_id: Number(formCrear.usuario_id) } : {}),
      })
      mostrarAlerta('success', 'Reparación creada correctamente.')
      const nuevoId = res?.reparacion?.reparacion_id
      if (nuevoId) await descargarPdf(
        () => api.descargarCertificadoRecepcion(nuevoId),
        `recepcion_${String(nuevoId).padStart(4, '0')}.pdf`
      )
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
      pago_parcial:     rep.pago_parcial,
      pago_reparador:   rep.pago_reparador ?? '',
      pagado:           rep.pagado ?? false,
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
        pago_parcial:     Number(formEditar.pago_parcial),
        telefono_cliente: formEditar.telefono_cliente.trim(),
        dni_cliente:      formEditar.dni_cliente.trim() || null,
        mail_cliente:     formEditar.mail_cliente.trim() || null,
      }
      if (esAdmin && formEditar.pago_reparador !== '') {
        body.pago_reparador = Number(formEditar.pago_reparador)
      }
      if (esAdmin) {
        body.pagado = formEditar.pagado
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
        precio_final: Number(montoAgregar),
        observaciones:  montoObs.trim() || null,
        ...(esAdmin && adminFecha     ? { fecha: adminFecha } : {}),
        ...(esAdmin && adminUsuarioId ? { usuario_id: Number(adminUsuarioId) } : {}),
      })
      mostrarAlerta('success', 'Monto actualizado correctamente.')
      setMontoRepId(null); setMontoAgregar(''); setMontoObs(''); setAdminFecha(''); setAdminUsuarioId('')
      fetchReparaciones()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingMonto(false)
    }
  }

  // ── Cambio pago parcial ───────────────────────────────────────────────────

  const abrirCambioPago = (rep) => {
    cerrarTodo()
    setCambioPagoRepId(rep.reparacion_id)
    setCambioPagoMonto(rep.pago_parcial)
  }

  const handleSubmitCambioPago = async (e) => {
    e.preventDefault()
    setLoadingCambioPago(true)
    try {
      await api.cambioPagoParcialReparacion(cambioPagoRepId, {
        nuevo_monto:   Number(cambioPagoMonto),
        observaciones: cambioPagoObs.trim() || null,
        ...(esAdmin && adminFecha     ? { fecha: adminFecha } : {}),
        ...(esAdmin && adminUsuarioId ? { usuario_id: Number(adminUsuarioId) } : {}),
      })
      mostrarAlerta('success', 'Pago parcial actualizado correctamente.')
      setCambioPagoRepId(null); setCambioPagoMonto(''); setCambioPagoObs(''); setAdminFecha(''); setAdminUsuarioId('')
      fetchReparaciones()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingCambioPago(false)
    }
  }

  // ── Aceptar (EN_REVISION → EN_REPARACION) ────────────────────────────────

  const abrirAceptar = (rep) => {
    cerrarTodo()
    setAceptarRepId(rep.reparacion_id)
  }

  const handleSubmitAceptar = async (e) => {
    e.preventDefault()
    setLoadingAceptar(true)
    const repId = aceptarRepId
    try {
      await api.aceptarReparacion(repId, {
        total_final:           Number(aceptarTotal),
        pago_parcial_agregado: Number(aceptarPagoParcial),
        observaciones:         aceptarObs.trim() || null,
        ...(esAdmin && adminFecha     ? { fecha: adminFecha } : {}),
        ...(esAdmin && adminUsuarioId ? { usuario_id: Number(adminUsuarioId) } : {}),
      })
      mostrarAlerta('success', 'Reparación aceptada correctamente.')
      await descargarPdf(
        () => api.descargarCertificadoRecepcion(repId),
        `recepcion_${String(repId).padStart(4, '0')}.pdf`
      )
      setAceptarRepId(null); setAceptarTotal(''); setAceptarPagoParcial(''); setAceptarObs(''); setAdminFecha(''); setAdminUsuarioId('')
      fetchReparaciones()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingAceptar(false)
    }
  }

  // ── Cancelar ──────────────────────────────────────────────────────────────

  const abrirCancelar = (rep) => {
    cerrarTodo()
    setCancelarRepId(rep.reparacion_id)
  }

  const handleSubmitCancelar = async (e) => {
    e.preventDefault()
    setLoadingCancelar(true)
    const repId = cancelarRepId
    try {
      await api.cancelarReparacion(repId, {
        monto_a_devolver: cancelarMonto !== '' ? Number(cancelarMonto) : null,
        observaciones:    cancelarObs.trim() || null,
        ...(esAdmin && adminFecha     ? { fecha: adminFecha } : {}),
        ...(esAdmin && adminUsuarioId ? { usuario_id: Number(adminUsuarioId) } : {}),
      })
      mostrarAlerta('success', 'Reparación cancelada.')
      await descargarPdf(
        () => api.descargarCertificadoCancelacion(repId),
        `cancelacion_${String(repId).padStart(4, '0')}.pdf`
      )
      setCancelarRepId(null); setCancelarMonto(''); setCancelarObs(''); setAdminFecha(''); setAdminUsuarioId('')
      fetchReparaciones()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingCancelar(false)
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
      ...(esAdmin && adminFecha     ? { fecha: adminFecha } : {}),
      ...(esAdmin && adminUsuarioId ? { usuario_id: Number(adminUsuarioId) } : {}),
    }
    const repId = transRepId
    const accion = transAccion
    try {
      if (accion === 'entregar')               await api.entregarReparacion(repId, body)
      else if (accion === 'garantia')          await api.garantiaReparacion(repId, body)
      else if (accion === 'entregar-garantia') await api.entregarGarantiaReparacion(repId, body)
      mostrarAlerta('success', 'Reparación actualizada correctamente.')
      // Al entregar (normal o por garantía) se genera el certificado de garantía
      if (accion === 'entregar' || accion === 'entregar-garantia') await descargarPdf(
        () => api.descargarCertificadoGarantia(repId),
        `garantia_${String(repId).padStart(4, '0')}.pdf`
      )
      setTransRepId(null); setTransAccion(null); setAdminFecha(''); setAdminUsuarioId('')
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
    setMostrarCrear(false); setFormCrear(formCrearVacio)
    setEditandoId(null)
    setMontoRepId(null); setMontoAgregar(''); setMontoObs('')
    setCambioPagoRepId(null); setCambioPagoMonto(''); setCambioPagoObs('')
    setAceptarRepId(null); setAceptarTotal(''); setAceptarPagoParcial(''); setAceptarObs('')
    setCancelarRepId(null); setCancelarMonto(''); setCancelarObs('')
    setTransRepId(null); setTransAccion(null); setTransObs('')
    setAdminFecha(''); setAdminUsuarioId('')
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  const descargarPdf = async (apiFn, filename) => {
    try {
      const blob = await apiFn()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = filename; a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    }
  }

  const nombreUsuario = (id) => usuarios.find(u => u.usuario_id === id)?.nombre ?? id

  const estadoClase = (estado) => ({
    EN_REVISION:         'pendiente',
    EN_REPARACION:       'activo',
    REPARACION_GARANTIA: 'activo',
    ENTREGADO:           'inactivo',
    ENTREGADO_GARANTIA:  'inactivo',
    CANCELADO:           'cancelado',
  }[estado] ?? '')

  const labelTransicion = (accion) => ({
    'entregar':          'Entregar',
    'garantia':          'Enviar a garantía',
    'entregar-garantia': 'Entregar garantía',
  }[accion] ?? accion)

  const adminCampos = () => esAdmin && (
    <div className="form-row">
      <div className="form-group">
        <label>Fecha</label>
        <input type="date" value={adminFecha} onChange={e => setAdminFecha(e.target.value)} />
      </div>
      <div className="form-group">
        <label>Vendedor/a</label>
        <select value={adminUsuarioId || usuarioId || ''} onChange={e => setAdminUsuarioId(e.target.value)}>
          {usuarios.map(u => <option key={u.usuario_id} value={u.usuario_id}>{u.nombre}</option>)}
        </select>
      </div>
    </div>
  )

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

            {/* Selector estado inicial */}
            <div className="form-row">
              <div className="form-group" style={{ flex: 1 }}>
                <label>Tipo de ingreso *</label>
                <div className="filtros-chips" style={{ marginTop: 6 }}>
                  {['EN_REVISION', 'EN_REPARACION'].map(est => (
                    <button key={est} type="button"
                      className={`filtro-chip ${formCrear.estado_inicial === est ? 'filtro-chip-activo' : ''}`}
                      onClick={() => setFormCrear(p => ({ ...p, estado_inicial: est, total: '' }))}>
                      {est === 'EN_REVISION' ? 'Revisión (monto desconocido)' : 'Reparación (monto conocido)'}
                    </button>
                  ))}
                </div>
              </div>
            </div>

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
                <label>Descripcion del problema</label>
                <input value={formCrear.descripcion}
                  onChange={e => setFormCrear(p => ({ ...p, descripcion: e.target.value }))}
                  placeholder={formCrear.estado_inicial === 'EN_REVISION' ? 'Ej: pantalla rota, no carga...' : 'Ej: cambio de módulo'} />
              </div>
            </div>

            <div className="form-row">
              {formCrear.estado_inicial === 'EN_REPARACION' && (
                <div className="form-group">
                  <label>Total *</label>
                  <input type="number" value={formCrear.total}
                    onChange={e => setFormCrear(p => ({ ...p, total: e.target.value }))}
                    required min={0} placeholder="Monto total" />
                </div>
              )}
              <div className="form-group">
                <label>{formCrear.estado_inicial === 'EN_REVISION' ? 'Costo de revisión *' : 'Adelanto *'}</label>
                <input type="number" value={formCrear.pago_parcial}
                  onChange={e => setFormCrear(p => ({ ...p, pago_parcial: e.target.value }))}
                  required min={0}
                  placeholder={formCrear.estado_inicial === 'EN_REVISION' ? 'Costo de diagnóstico' : 'Monto adelanto'} />
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
                  <select value={formCrear.usuario_id || usuarioId || ''}
                    onChange={e => setFormCrear(p => ({ ...p, usuario_id: e.target.value }))}>
                    {usuarios.map(u => <option key={u.usuario_id} value={u.usuario_id}>{u.nombre}</option>)}
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

      {/* ── Formulario editar ── */}
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
                <label>Pago parcial</label>
                <input type="number" value={formEditar.pago_parcial} min={0}
                  onChange={e => setFormEditar(p => ({ ...p, pago_parcial: e.target.value }))} />
              </div>
              {esAdmin && (
                <div className="form-group">
                  <label>Pago al reparador</label>
                  <input type="number" value={formEditar.pago_reparador} min={0}
                    placeholder="Completar cuando este listo"
                    onChange={e => setFormEditar(p => ({ ...p, pago_reparador: e.target.value }))} />
                </div>
              )}
              {esAdmin && (
                <div className="form-group" style={{ justifyContent: 'center' }}>
                  <label>Pagado al reparador</label>
                  <input type="checkbox" checked={formEditar.pagado}
                    onChange={e => setFormEditar(p => ({ ...p, pagado: e.target.checked }))}
                    style={{ width: 'auto', marginTop: 10 }} />
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
          <h3>Cambiar precio final — reparacion #{montoRepId}</h3>
          <form onSubmit={handleSubmitMonto} className="acc-form">
            <div className="form-row">
              <div className="form-group">
                <label>Nuevo precio final *</label>
                <input type="number" value={montoAgregar} min={1} required
                  onChange={e => setMontoAgregar(e.target.value)} placeholder="Ej: 5000" />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Observaciones</label>
                <input value={montoObs}
                  onChange={e => setMontoObs(e.target.value)} placeholder="Motivo (opcional)" />
              </div>
            </div>
            {adminCampos()}
            <div className="form-actions">
              <button type="button" className="btn btn-secondary"
                onClick={() => { setMontoRepId(null); setMontoAgregar(''); setMontoObs('') }}
                disabled={loadingMonto}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loadingMonto}>
                {loadingMonto ? 'Guardando...' : 'Confirmar'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Modal cambio pago parcial ── */}
      {cambioPagoRepId && (
        <div className="form-card">
          <h3>Corregir pago parcial — reparacion #{cambioPagoRepId}</h3>
          <form onSubmit={handleSubmitCambioPago} className="acc-form">
            <div className="form-row">
              <div className="form-group">
                <label>Nuevo monto *</label>
                <input type="number" value={cambioPagoMonto} min={0} required
                  onChange={e => setCambioPagoMonto(e.target.value)} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Observaciones</label>
                <input value={cambioPagoObs}
                  onChange={e => setCambioPagoObs(e.target.value)} placeholder="Motivo de la corrección (opcional)" />
              </div>
            </div>
            {adminCampos()}
            <div className="form-actions">
              <button type="button" className="btn btn-secondary"
                onClick={() => { setCambioPagoRepId(null); setCambioPagoMonto(''); setCambioPagoObs('') }}
                disabled={loadingCambioPago}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loadingCambioPago}>
                {loadingCambioPago ? 'Guardando...' : 'Confirmar'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Modal aceptar (EN_REVISION → EN_REPARACION) ── */}
      {aceptarRepId && (
        <div className="form-card">
          <h3>Aceptar reparacion — #{aceptarRepId}</h3>
          <p style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>
            Se establecerá el total y se pasará a estado EN_REPARACION.
          </p>
          <form onSubmit={handleSubmitAceptar} className="acc-form">
            <div className="form-row">
              <div className="form-group">
                <label>Total final *</label>
                <input type="number" value={aceptarTotal} min={0} required
                  onChange={e => setAceptarTotal(e.target.value)} placeholder="Monto total de la reparación" />
              </div>
              <div className="form-group">
                <label>Pago adicional del cliente</label>
                <input type="number" value={aceptarPagoParcial} min={0}
                  onChange={e => setAceptarPagoParcial(e.target.value)} placeholder="0 si no agrega nada" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group" style={{ flex: 1 }}>
                <label>Observaciones</label>
                <input value={aceptarObs}
                  onChange={e => setAceptarObs(e.target.value)} placeholder="Diagnóstico, notas (opcional)" />
              </div>
            </div>
            {adminCampos()}
            <div className="form-actions">
              <button type="button" className="btn btn-secondary"
                onClick={() => { setAceptarRepId(null); setAceptarTotal(''); setAceptarPagoParcial('') }}
                disabled={loadingAceptar}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loadingAceptar}>
                {loadingAceptar ? 'Guardando...' : 'Aceptar reparacion'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Modal cancelar ── */}
      {cancelarRepId && (
        <div className="form-card">
          <h3>Cancelar reparacion — #{cancelarRepId}</h3>
          <form onSubmit={handleSubmitCancelar} className="acc-form">
            <div className="form-row">
              <div className="form-group">
                <label>Monto a devolver al cliente</label>
                <input type="number" value={cancelarMonto} min={0}
                  onChange={e => setCancelarMonto(e.target.value)} placeholder="0 si no se devuelve nada" />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Motivo de cancelación</label>
                <input value={cancelarObs}
                  onChange={e => setCancelarObs(e.target.value)} placeholder="Opcional" />
              </div>
            </div>
            {adminCampos()}
            <div className="form-actions">
              <button type="button" className="btn btn-secondary"
                onClick={() => { setCancelarRepId(null); setCancelarMonto(''); setCancelarObs('') }}
                disabled={loadingCancelar}>Volver</button>
              <button type="submit" className="btn btn-danger" disabled={loadingCancelar}>
                {loadingCancelar ? 'Cancelando...' : 'Confirmar cancelación'}
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
            {adminCampos()}
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
      {!mostrarCrear && !editandoId && !montoRepId && !cambioPagoRepId && !aceptarRepId && !cancelarRepId && !transRepId && (
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
            {esAdmin && (
              <div className="filtros-row">
                <span className="filtros-sublabel">Pago al reparador:</span>
                <div className="filtros-chips">
                  <button
                    className={`filtro-chip ${filtroPagado === true ? 'filtro-chip-activo' : ''}`}
                    onClick={() => handleFiltroPagado(true)}>Pagados</button>
                  <button
                    className={`filtro-chip ${filtroPagado === false ? 'filtro-chip-activo' : ''}`}
                    onClick={() => handleFiltroPagado(false)}>No pagados</button>
                </div>
              </div>
            )}
            <div className="filtros-row">
              <span className="filtros-sublabel">Fecha:</span>
              <div className="filtros-chips">
                <input type="date" value={fechaDesde} onChange={handleFechaDesde} />
                <input type="date" value={fechaHasta} onChange={handleFechaHasta} />
              </div>
            </div>
            {(filtroLocalId || filtroEstado || filtroUsuarioId || filtroPagado !== null || fechaDesde || fechaHasta || busqueda) && (
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
                <th>Pago parcial</th>
                {esAdmin && <th>Pago reparador</th>}
                {esAdmin && <th>Pagado</th>}
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
                    <td>{formatFechaCorta(rep.fecha_ingreso)}</td>
                    <td>{rep.celular}</td>
                    <td>{rep.nombre_cliente}</td>
                    <td>{rep.total != null ? formatPrecio(rep.total) : '—'}</td>
                    <td>{formatPrecio(rep.pago_parcial)}</td>
                    {esAdmin && <td>{rep.pago_reparador != null ? formatPrecio(rep.pago_reparador) : '-'}</td>}
                    {esAdmin && <td>{rep.pagado ? <span className="estado-badge activo">Sí</span> : <span className="estado-badge">No</span>}</td>}
                    <td>
                      <span className={`estado-badge ${estadoClase(rep.estado)}`}>
                        {rep.estado.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>{nombreUsuario(rep.usuario_id)}</td>
                    <td className="acciones-cell">

                      {/* ── EN_REVISION ── */}
                      {rep.estado === 'EN_REVISION' && (<>
                        <button className="btn btn-sm btn-primary"
                          onClick={() => abrirAceptar(rep)}>
                          Aceptar
                        </button>
                        <button className="btn btn-sm btn-secondary"
                          onClick={() => abrirCancelar(rep)}>
                          Cancelar
                        </button>
                        <button className="btn btn-sm btn-secondary"
                          onClick={() => descargarPdf(
                            () => api.descargarCertificadoRecepcion(rep.reparacion_id),
                            `recepcion_${String(rep.reparacion_id).padStart(4, '0')}.pdf`
                          )}>
                          Cert. Recepción
                        </button>
                      </>)}

                      {/* ── EN_REPARACION ── */}
                      {rep.estado === 'EN_REPARACION' && (<>
                        <button className="btn btn-sm btn-primary"
                          onClick={() => abrirTransicion(rep.reparacion_id, 'entregar')}>
                          Entregar
                        </button>
                        <button className="btn btn-sm btn-secondary"
                          onClick={() => abrirCancelar(rep)}>
                          Cancelar
                        </button>
                        <button className="btn btn-sm btn-secondary"
                          onClick={() => descargarPdf(
                            () => api.descargarCertificadoRecepcion(rep.reparacion_id),
                            `recepcion_${String(rep.reparacion_id).padStart(4, '0')}.pdf`
                          )}>
                          Cert. Recepción
                        </button>
                      </>)}

                      {/* ── ENTREGADO / ENTREGADO_GARANTIA ── */}
                      {(rep.estado === 'ENTREGADO' || rep.estado === 'ENTREGADO_GARANTIA') && (<>
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
                      </>)}

                      {/* ── REPARACION_GARANTIA ── */}
                      {rep.estado === 'REPARACION_GARANTIA' && (
                        <button className="btn btn-sm btn-primary"
                          onClick={() => abrirTransicion(rep.reparacion_id, 'entregar-garantia')}>
                          Entregar garantia
                        </button>
                      )}

                      {/* ── CANCELADO ── */}
                      {rep.estado === 'CANCELADO' && (
                        <button className="btn btn-sm btn-secondary"
                          onClick={() => descargarPdf(
                            () => api.descargarCertificadoCancelacion(rep.reparacion_id),
                            `cancelacion_${String(rep.reparacion_id).padStart(4, '0')}.pdf`
                          )}>
                          Cert. Cancelación
                        </button>
                      )}

                      {/* ── Cambio de precio / adelanto (todos los estados menos cancelado) ── */}
                      {rep.estado !== 'CANCELADO' && (<>
                        <button className="btn btn-sm btn-secondary"
                          onClick={() => { cerrarTodo(); setMontoRepId(rep.reparacion_id) }}>
                          Cambiar precio final
                        </button>
                        <button className="btn btn-sm btn-secondary"
                          onClick={() => abrirCambioPago(rep)}>
                          Corregir adelanto
                        </button>
                      </>)}

                      {/* ── Siempre visibles ── */}
                      <button className="btn btn-sm btn-secondary"
                        onClick={() => abrirEditar(rep)}>Editar</button>
                      <button className="btn btn-sm btn-secondary"
                        onClick={() => verHistorial(rep)}>Historial</button>

                    </td>
                  </tr>
                </React.Fragment>
              ))}
            </tbody>
          </table>
          <div className="paginacion">
            <button className="btn btn-secondary btn-sm" onClick={() => irAPagina(pagina - 1)} disabled={pagina === 0}>← Anterior</button>
            <span className="pagina-info">Página {pagina + 1}</span>
            <button className="btn btn-secondary btn-sm" onClick={() => irAPagina(pagina + 1)} disabled={!hayMas}>Siguiente →</button>
          </div>
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
