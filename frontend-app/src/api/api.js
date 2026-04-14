// ─── CONSTANTES ──────────────────────────────────────────────────────────────
export const LIMIT = 20
export const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ─── HELPERS ─────────────────────────────────────────────────────────────────
export const handleResponse = async (res) => {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || err.message || `Error ${res.status}`)
  }
  return res.json()
}

export const buildParams = (obj) => {
  const params = new URLSearchParams()
  Object.entries(obj).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') params.set(k, v)
  })
  return params.toString()
}

const authFetch = (url, options = {}) => {
  const token = localStorage.getItem('token')
  const headers = {
    ...options.headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
  return fetch(url, { ...options, headers }).then(res => {
    if (res.status === 401) {
      localStorage.removeItem('token')
      window.dispatchEvent(new CustomEvent('auth:logout', {
        detail: { source: '401' }
      }))
    }
    return res
  })
}

// ─── AUTH ─────────────────────────────────────────────────────────────────────
export const login = async ({ username, password }) => {
  const body = new URLSearchParams({ username, password })
  const res = await fetch(`${BASE_URL}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Error ${res.status}`)
  }
  const data = await res.json()
  localStorage.setItem('token', data.access_token)
  return data  // { access_token, token_type, nombre, rol }
}

export const logout = () => localStorage.removeItem('token')

// ─── API ─────────────────────────────────────────────────────────────────────
export const api = {
// ─── LISTAR ───────────────────────────────────────────────────
// ─── LISTAR EGRESOS ───────────────────────────────────────
  listarEgresos: ({
    skip = 0,
    limit = LIMIT,
    fecha_desde = null,
    fecha_hasta = null,
    local_id = null,
    usuario_id = null,
  } = {}) =>
    authFetch(
      `${BASE_URL}/egresos/?${buildParams({
        skip,
        limit,
        fecha_desde,
        fecha_hasta,
        local_id,
        usuario_id,
      })}`
    ).then(handleResponse),


  // ─── CREAR EGRESO ─────────────────────────────────────────
  crearEgreso: ({
    monto,
    descripcion,
    local_id,
    usuario_id = null, // admin opcional
  }) =>
    authFetch(`${BASE_URL}/egresos/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        monto,
        descripcion,
        local_id,
        ...(usuario_id && { usuario_id }),
      }),
    }).then(handleResponse),


  // ─── OBTENER EGRESO ───────────────────────────────────────
  obtenerEgreso: ({ egreso_id }) =>
    authFetch(`${BASE_URL}/egresos/${egreso_id}`)
      .then(handleResponse),


  // ─── ELIMINAR EGRESO ──────────────────────────────────────
  eliminarEgreso: ({ egreso_id }) =>
    authFetch(`${BASE_URL}/egresos/${egreso_id}`, {
      method: 'DELETE',
    }).then(handleResponse),


  // ─── ACTUALIZAR EGRESO ────────────────────────────────────
  actualizarEgreso: ({
    egreso_id,
    monto = null,
    descripcion = null,
    local_id = null,
  }) =>
    authFetch(`${BASE_URL}/egresos/${egreso_id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...(monto !== null && { monto }),
        ...(descripcion !== null && { descripcion }),
        ...(local_id !== null && { local_id }),
      }),
    }).then(handleResponse),

  // INGRESOS
  listarIngresos: ({ skip = 0, limit = LIMIT, fecha_desde = null, fecha_hasta = null, local_id = null } = {}) =>
    authFetch(`${BASE_URL}/ingresos/?${buildParams({ skip, limit, fecha_desde, fecha_hasta, local_id })}`).then(handleResponse),

  getDetalleIngreso: (ingreso_lote_id) =>
    authFetch(`${BASE_URL}/ingresos/${ingreso_lote_id}`).then(handleResponse),

  generarIngresoPdf: (ingreso_lote_id) =>
    authFetch(`${BASE_URL}/ingresos/${ingreso_lote_id}/pdf`)
      .then(res => {
        if (!res.ok) return res.json().then(e => { throw new Error(e.detail || `Error ${res.status}`) })
        return res.blob()
      }),

  listarTransferencias: ({ skip = 0, limit = LIMIT, fecha_desde = null, fecha_hasta = null, local_origen_id = null, local_destino_id = null, usuario_id = null } = {}) =>
    authFetch(`${BASE_URL}/transferencias/?${buildParams({ skip, limit, fecha_desde, fecha_hasta, local_origen_id, local_destino_id, usuario_id })}`).then(handleResponse),

  getDetalleTransferencia: (transferencia_id) =>
    authFetch(`${BASE_URL}/transferencias/${transferencia_id}`).then(handleResponse),

  generarTransferenciaPdf: (transferencia_id) =>
    authFetch(`${BASE_URL}/transferencias/${transferencia_id}/pdf`)
      .then(res => {
        if (!res.ok) return res.json().then(e => { throw new Error(e.detail || `Error ${res.status}`) })
        return res.blob()
      }),

  // DETALLE VENTAS
  getDetallesVenta: (ventaId) =>
    authFetch(`${BASE_URL}/detalles/venta/${ventaId}`).then(handleResponse),

  // LISTADOS
  listarAccesorios: ({ skip = 0, limit = LIMIT, buscar = '', tipo_id = null, subtipo_id = null, marca_celular_id = null, modelo_celular_id = null, activo = true } = {}) =>
    authFetch(`${BASE_URL}/accesorios/?${buildParams({ skip, limit, buscar, tipo_id, subtipo_id, marca_celular_id, modelo_celular_id, activo })}`).then(handleResponse),

  listarTipos: ({ buscar = '', activo = true } = {}) =>
    authFetch(`${BASE_URL}/tipos-accesorios/?${buildParams({ limit: 100, buscar, activo })}`).then(handleResponse),

  listarSubtipos: ({ tipo_id = null, buscar = '', activo = true } = {}) =>
    authFetch(`${BASE_URL}/subtipos-accesorios/?${buildParams({ limit: 100, tipo_id, buscar, activo })}`).then(handleResponse),

  listarMarcas: ({ buscar = '', activo = true } = {}) =>
    authFetch(`${BASE_URL}/marcas/?${buildParams({ limit: 100, buscar, activo })}`).then(handleResponse),

  listarMarcasCelulares: ({ buscar = '', activo = true } = {}) =>
    authFetch(`${BASE_URL}/marcas-celulares/?${buildParams({ limit: 100, buscar, activo })}`).then(handleResponse),

  listarModelos: ({ buscar = '', marca_celular_id = null, activo = true } = {}) =>
  authFetch(`${BASE_URL}/modelos-celulares/?${buildParams({ limit: 100, buscar, marca_celular_id , activo})}`).then(handleResponse),

  listarStock: ({ skip = 0, limit = LIMIT, buscar = '', tipo_id = null, subtipo_id = null, local_id = null, activo = true } = {}) =>
    authFetch(`${BASE_URL}/stock/?${buildParams({ skip, limit, buscar, tipo_id, subtipo_id, local_id, activo })}`).then(handleResponse),

  listarLocales: ({ activo, tipo } = {}) => {
      const query = buildParams({ activo, tipo });
      return authFetch(`${BASE_URL}/locales/${query ? `?${query}` : ""}`).then(handleResponse);
  },

  listarComisiones: () =>
    authFetch(`${BASE_URL}/comisiones/`).then(handleResponse),

  listarCelulares: ({ skip = 0, limit = LIMIT, local_id = null, estado = null, imei = '', marca_celular_id = null, modelo_celular_id = null } = {}) =>
    authFetch(`${BASE_URL}/celulares/?${buildParams({ skip, limit, local_id, estado, imei, marca_celular_id, modelo_celular_id })}`).then(handleResponse),

  listarChips: ({ skip = 0, limit = LIMIT, local_id = null, estado = null, compania = null, buscar = null } = {}) =>
    authFetch(`${BASE_URL}/chips/?${buildParams({ skip, limit, local_id, estado, compania, buscar })}`).then(handleResponse),

  listarVentas: ({ skip = 0, limit = LIMIT, local_id = null } = {}) =>
    authFetch(
      `${BASE_URL}/ventas/?${buildParams({ skip, limit, local_id })}`
    ).then(handleResponse),

  listarUsuarios: ({ activo } = {}) => {
    const query = buildParams({ activo });
    return authFetch(`${BASE_URL}/usuarios/${query ? `?${query}` : ""}`).then(handleResponse);
  },

  crearUsuario: (body) =>
    authFetch(`${BASE_URL}/usuarios/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  actualizarUsuario: (id, body) =>
    authFetch(`${BASE_URL}/usuarios/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  desactivarUsuario: (id) =>
    authFetch(`${BASE_URL}/usuarios/${id}`, { method: 'DELETE' }).then(handleResponse),

  // MODULO ACCESORIOS
  verificarDuplicado: (body) =>
    authFetch(`${BASE_URL}/accesorios/verificar-duplicado`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  crearAccesorio: (body) =>
    authFetch(`${BASE_URL}/accesorios/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  actualizarAccesorio: (id, body) =>
    authFetch(`${BASE_URL}/accesorios/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  eliminarAccesorio: (id) =>
    authFetch(`${BASE_URL}/accesorios/${id}`, { method: 'DELETE' }).then(handleResponse),

  // FormData — no pasar Content-Type, el browser lo setea con el boundary correcto
  importarExcel: (formData) =>
    authFetch(`${BASE_URL}/accesorios/importar-excel`, {
      method: 'POST',
      body: formData,
    }).then(handleResponse),

  exportarAccesorios: ({ buscar = '', tipo_id = null, subtipo_id = null, activo = true } = {}) =>
    authFetch(`${BASE_URL}/accesorios/export?${buildParams({ buscar, tipo_id, subtipo_id, activo })}`)
      .then(res => {
        if (!res.ok) throw new Error(`Error ${res.status}`)
        return res.blob()
      }),

  // MODULO STOCK
  ajustarStock: (body) =>
    authFetch(`${BASE_URL}/stock/ajustar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  ingresoEgreso: (body) =>
    authFetch(`${BASE_URL}/stock/ingreso-egreso`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  transferir: (body) =>
    authFetch(`${BASE_URL}/stock/transferir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  exportarStock: ({ buscar = '', tipo_id = null, subtipo_id = null, local_id = null, activo = true } = {}) =>
    authFetch(`${BASE_URL}/stock/export?${buildParams({ buscar, tipo_id, subtipo_id, local_id, activo })}`)
      .then(res => {
        if (!res.ok) throw new Error(`Error ${res.status}`)
        return res.blob()
      }),

  // Reemplaza a ingresoEgreso para el flujo de ingreso
  ingresarLote: (body) =>
    authFetch(`${BASE_URL}/stock/ingresar-lote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  // Nueva transferencia por lote
  transferirLote: (body) =>
    authFetch(`${BASE_URL}/stock/transferir-lote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  // Egreso individual (reemplaza al uso de ingresoEgreso para SALIDA)
  egresoStock: (body) =>
    authFetch(`${BASE_URL}/stock/egreso`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  // LOCALES
  crearLocal: (body) =>
    authFetch(`${BASE_URL}/locales/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  actualizarLocal: (id, body) =>
    authFetch(`${BASE_URL}/locales/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  eliminarLocal: (id) =>
    authFetch(`${BASE_URL}/locales/${id}`, { method: 'DELETE' }).then(handleResponse),

  // MOVIMIENTOS
  listarMovimientos: ({ skip = 0, limit = LIMIT, local_id = null, tipo_movimiento = null, fecha_desde = null, fecha_hasta = null } = {}) =>
    authFetch(`${BASE_URL}/movimientos/?${buildParams({ skip, limit, local_id, tipo_movimiento, fecha_desde, fecha_hasta })}`).then(handleResponse),

  exportarMovimientos: ({ local_id = null, tipo_movimiento = null, fecha_desde = null, fecha_hasta = null } = {}) =>
    authFetch(`${BASE_URL}/movimientos/export?${buildParams({ local_id, tipo_movimiento, fecha_desde, fecha_hasta })}`)
      .then(res => {
        if (!res.ok) throw new Error(`Error ${res.status}`)
        return res.blob()
      }),

  // CAJA DIARIA
  generarCajaDiaria: ({ local_id, usuario_id = null, fecha = null, desde = null, hasta = null }) =>
    authFetch(
      `${BASE_URL}/caja-diaria/pdf?${buildParams({ local_id, ...(usuario_id && { usuario_id }), fecha, desde, hasta })}`
    ).then(res => {
      if (!res.ok) return res.json().then(e => { throw new Error(e.detail || `Error ${res.status}`) })
      return res.blob()
    }),

  // SOBRANTES / FALTANTES
  upsertSobranteFaltante: (body) =>
    authFetch(`${BASE_URL}/sobrantes-faltantes/`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  getSobranteFaltante: ({ local_id, fecha }) =>
    authFetch(`${BASE_URL}/sobrantes-faltantes/?${buildParams({ local_id, fecha })}`).then(handleResponse),

  // VENTAS
  crearVenta: (body) =>
    authFetch(`${BASE_URL}/ventas/crear-venta`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  // ─── MÓDULO CHIPS ──────────────────────────────────────────────────────────
  exportarChips: ({ local_id = null, estado = null, compania = null, buscar = null } = {}) =>
    authFetch(`${BASE_URL}/chips/export?${buildParams({ local_id, estado, compania, buscar, limit: 10000 })}`)
      .then(res => {
        if (!res.ok) throw new Error(`Error ${res.status}`)
        return res.blob()
      }),

  obtenerChip: (id) =>
    authFetch(`${BASE_URL}/chips/${id}`).then(handleResponse),

  buscarChipPorNumeroSerie: (numero_serie) =>
    authFetch(`${BASE_URL}/chips/numero-serie/${encodeURIComponent(numero_serie)}`).then(handleResponse),

  crearChip: (body) =>
    authFetch(`${BASE_URL}/chips/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  actualizarChip: (id, body) =>
    authFetch(`${BASE_URL}/chips/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  eliminarChip: (id) =>
    authFetch(`${BASE_URL}/chips/${id}`, { method: 'DELETE' }).then(handleResponse),

  ingresarLoteChips: (body) =>
    authFetch(`${BASE_URL}/chips/ingresar-lote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  listarIngresosChips: ({ skip = 0, limit = 20, fecha_desde = null, fecha_hasta = null, local_id = null } = {}) =>
    authFetch(`${BASE_URL}/chips/ingresos/?${buildParams({ skip, limit, fecha_desde, fecha_hasta, local_id })}`).then(handleResponse),

  getDetalleIngresoChips: (ingreso_lote_chip_id) =>
    authFetch(`${BASE_URL}/chips/ingresos/${ingreso_lote_chip_id}`).then(handleResponse),

  generarIngresoChipsPdf: (ingreso_lote_chip_id) =>
    authFetch(`${BASE_URL}/chips/ingresos/${ingreso_lote_chip_id}/pdf`)
      .then(res => {
        if (!res.ok) return res.json().then(e => { throw new Error(e.detail || `Error ${res.status}`) })
        return res.blob()
      }),

  // CELULARES
  crearCelular: (body) =>
    authFetch(`${BASE_URL}/celulares/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  actualizarCelular: (id, body) =>
    authFetch(`${BASE_URL}/celulares/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  eliminarCelular: (id) =>
    authFetch(`${BASE_URL}/celulares/${id}`, { method: 'DELETE' }).then(handleResponse),

  // TIPOS DE ACCESORIOS
  crearTipo: (body) =>
    authFetch(`${BASE_URL}/tipos-accesorios/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  actualizarTipo: (id, body) =>
    authFetch(`${BASE_URL}/tipos-accesorios/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  eliminarTipo: (id) =>
  authFetch(`${BASE_URL}/tipos-accesorios/${id}`, {
    method: 'DELETE',
  }).then(handleResponse),

  // SUBTIPOS DE ACCESORIOS
  crearSubtipo: (body) =>
    authFetch(`${BASE_URL}/subtipos-accesorios/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  actualizarSubtipo: (id, body) =>
    authFetch(`${BASE_URL}/subtipos-accesorios/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  eliminarSubtipo: (id) =>
  authFetch(`${BASE_URL}/subtipos-accesorios/${id}`, {
    method: 'DELETE',
  }).then(handleResponse),

  // MODELOS CELULARES
  crearModelo: (body) =>
    authFetch(`${BASE_URL}/modelos-celulares/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  actualizarModelo: (id, body) =>
    authFetch(`${BASE_URL}/modelos-celulares/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  eliminarModelo: (id) =>
    authFetch(`${BASE_URL}/modelos-celulares/${id}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // MARCAS CELULARES
  crearMarcaCelular: (body) =>
  authFetch(`${BASE_URL}/marcas-celulares/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(handleResponse),

  actualizarMarcaCelular: (id, body) =>
    authFetch(`${BASE_URL}/marcas-celulares/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  eliminarMarcaCelular: (id) =>
    authFetch(`${BASE_URL}/marcas-celulares/${id}`, { method: 'DELETE' }).then(handleResponse),

  // MARCAS
  crearMarca: (body) =>
    authFetch(`${BASE_URL}/marcas/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  actualizarMarca: (id, body) =>
    authFetch(`${BASE_URL}/marcas/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  eliminarMarca: (id) =>
  authFetch(`${BASE_URL}/marcas/${id}`, {
    method: 'DELETE',
  }).then(handleResponse),

  // COMISIONES
  crearComision: (body) =>
    authFetch(`${BASE_URL}/comisiones/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  actualizarComision: (id, body) =>
    authFetch(`${BASE_URL}/comisiones/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),
  
  eliminarComision: (id) =>
    authFetch(`${BASE_URL}/comisiones/${id}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // PEDIDOS ONLINE
  crearPedidoOnline: (body) =>
    fetch(`${BASE_URL}/pedidos-online/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  listarPedidosOnline: ({ skip = 0, limit = LIMIT, estado = null, local_retiro_id = null, fecha_desde = null, fecha_hasta = null } = {}) =>
    authFetch(`${BASE_URL}/pedidos-online/?${buildParams({ skip, limit, estado, local_retiro_id, fecha_desde, fecha_hasta })}`).then(handleResponse),

  obtenerPedidoOnline: (id) =>
    authFetch(`${BASE_URL}/pedidos-online/${id}`).then(handleResponse),

  aprobarPedido: (id, body) =>
    authFetch(`${BASE_URL}/pedidos-online/${id}/aprobar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  rechazarPedido: (id, body = {}) =>
    authFetch(`${BASE_URL}/pedidos-online/${id}/rechazar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  entregarPedido: (id) =>
    authFetch(`${BASE_URL}/pedidos-online/${id}/entregar`, {
      method: 'POST',
    }).then(handleResponse),

  cancelarPedido: (id, body = {}) =>
    authFetch(`${BASE_URL}/pedidos-online/${id}/cancelar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  // MOVIMIENTOS FINANCIEROS
  listarMovimientosFinancieros: ({ offset = 0, limit = LIMIT, tipo = null, fecha_desde = null, fecha_hasta = null } = {}) =>
    authFetch(`${BASE_URL}/movimientos-financieros/?${buildParams({ offset, limit, tipo, fecha_desde, fecha_hasta })}`).then(handleResponse),

  crearMovimientoFinanciero: ({ tipo, monto, descripcion }) =>
    authFetch(`${BASE_URL}/movimientos-financieros/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tipo, monto, descripcion }),
    }).then(handleResponse),

  actualizarMovimientoFinanciero: (id, body) =>
    authFetch(`${BASE_URL}/movimientos-financieros/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  eliminarMovimientoFinanciero: (id) =>
    authFetch(`${BASE_URL}/movimientos-financieros/${id}`, { method: 'DELETE' })
      .then(res => { if (!res.ok) return res.json().then(e => { throw new Error(e.detail || `Error ${res.status}`) }) }),

  // REPARACIONES
  listarReparaciones: ({ estado = null, local_id = null, usuario_id = null, dni_cliente = null, fecha_desde = null, fecha_hasta = null } = {}) =>
    authFetch(`${BASE_URL}/reparaciones/?${buildParams({ estado, local_id, usuario_id, dni_cliente, fecha_desde, fecha_hasta })}`).then(handleResponse),

  crearReparacion: (body) =>
    authFetch(`${BASE_URL}/reparaciones/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  actualizarReparacion: (id, body) =>
    authFetch(`${BASE_URL}/reparaciones/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handleResponse),

  obtenerHistorialReparacion: (id) =>
    authFetch(`${BASE_URL}/reparaciones/${id}/historial`).then(handleResponse),

  cambiarPrecioReparacion: (id, body) =>
    authFetch(`${BASE_URL}/reparaciones/${id}/cambio-de-precio`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }).then(handleResponse),

  entregarReparacion: (id, body) =>
    authFetch(`${BASE_URL}/reparaciones/${id}/entregar`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }).then(handleResponse),

  garantiaReparacion: (id, body) =>
    authFetch(`${BASE_URL}/reparaciones/${id}/garantia`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }).then(handleResponse),

  entregarGarantiaReparacion: (id, body) =>
    authFetch(`${BASE_URL}/reparaciones/${id}/entregar-garantia`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }).then(handleResponse),

  descargarCertificadoRecepcion: (id) =>
    authFetch(`${BASE_URL}/reparaciones/${id}/certificado-recepcion`)
      .then(res => {
        if (!res.ok) return res.json().then(e => { throw new Error(e.detail || `Error ${res.status}`) })
        return res.blob()
      }),

  descargarCertificadoGarantia: (id) =>
    authFetch(`${BASE_URL}/reparaciones/${id}/certificado-garantia`)
      .then(res => {
        if (!res.ok) return res.json().then(e => { throw new Error(e.detail || `Error ${res.status}`) })
        return res.blob()
      }),

  descargarReporteComisiones: ({ local_id, usuario_id, desde, hasta }) =>
    authFetch(`${BASE_URL}/reportes/comisiones/excel?${buildParams({ local_id, usuario_id, desde, hasta })}`),
}