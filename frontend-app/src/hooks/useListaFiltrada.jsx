import { useState, useRef, useEffect } from 'react'
import { api, LIMIT } from '../api/api'

// ─── useListaFiltrada ────────────────────────────────────────────────────────
// Encapsula: lista paginada + búsqueda con debounce + filtros tipo/subtipo/local/activo
//
// @param fetchFn      — función que recibe los params y devuelve Promise<array[]>
//                       ej: (p) => api.listarAccesorios(p)
//                       ej: (p) => api.listarStock(p)
// @param conLocales   — carga y expone el filtro de locales (default: false)
// @param conCatalogos — carga marcas y modelos para resolver IDs en tabla (default: false)
// ─────────────────────────────────────────────────────────────────────────────
export default function useListaFiltrada(fetchFn, { conLocales = false, conCatalogos = false, conUsuarios = false } = {}) {
  // items son los campos como vienen directo de la db, o del modelo de response de la api, por ej StockResponse
  // ── Lista ──────────────────────────────────────────────────────────────────
  const [items, setItems]               = useState([])
  const [loadingLista, setLoadingLista] = useState(false)
  const [pagina, setPagina]             = useState(0)
  const [hayMas, setHayMas]             = useState(false)

  // ── Búsqueda ───────────────────────────────────────────────────────────────
  const [busqueda, setBusqueda] = useState('')
  const debounceRef             = useRef(null)

  // ── Filtros ────────────────────────────────────────────────────────────────
  const [filtroTipoId, setFiltroTipoId]       = useState(null)
  const [filtroSubtipoId, setFiltroSubtipoId] = useState(null)
  const [filtroLocalId, setFiltroLocalId]     = useState(null)
  const [filtroActivo, setFiltroActivo]       = useState(true)

  // ── Opciones del panel de filtros ──────────────────────────────────────────
  const [tiposFiltro, setTiposFiltro]       = useState([])
  const [subtiposFiltro, setSubtiposFiltro] = useState([])
  const [locales, setLocales]               = useState([])

  // ── Catálogos para resolver IDs en tabla (solo si conCatalogos = true) ─────
  const [subtipos, setSubtipos] = useState([])
  const [usuarios, setUsuarios] = useState([])

  // ── Carga inicial ──────────────────────────────────────────────────────────
  useEffect(() => {
    // aca se carga la lista principal con todo,
    _fetch('', 0, null, null, null, true)
    api.listarTipos({ buscar: '' })
      .then(data => setTiposFiltro(data.map(t => ({ value: t.tipo_id, label: t.nombre }))))
      .catch(() => {})
    if (conLocales) {
      api.listarLocales()
        .then(setLocales)
        .catch(() => {})
    }
    if (conCatalogos) {
      api.listarSubtipos({ buscar: '' })
        .then(data => setSubtipos(data.map(m => ({ value: m.subtipo_id, label: m.nombre }))))
        .catch(() => {})
    }
    if (conUsuarios) {
      api.listarUsuarios().then(setUsuarios).catch(()=>{})
    }
  }, [])
  // se queja pq se usa _fetch que se re-renderiza y conCatalogos que puede cambiar,
  // y se puede quedar con referencias viejas, pero no importa 
  // porque lo uso una vez en el render y luego no se vuelve a correr el useEFfect
  // entonces dentro del use effect nunca se va a usar una referencia vieja porque no se vuelve a usar directamente
  // ── Helpers para resolver IDs a nombres en la tabla ───────────────────────
  const nombreTipo  = (id) => tiposFiltro.find(m => m.value === id)?.label  ?? `ID ${id}`
  const nombreSubtipo = (id) => subtipos.find(m => m.value === id)?.label ?? `ID ${id}`

  // ── Fetch interno ──────────────────────────────────────────────────────────
  // Siempre recibe todos los parámetros explícitos en vez de leerlos del estado,
  // porque dentro de handlers síncronos el estado puede estar stale en ese render.
  // se re-renderiza en cada render, usa fetchFn que puede cambiar, (en realidad no por como se usa, suele ser fija)
  // si pongo useCallback deberia depender de fetchFn
  const _fetch = async (termino, pag, tipoId, subtipoId, localId, activo) => {
    setLoadingLista(true)
    try {
      const params = {
        skip: pag * LIMIT, limit: LIMIT + 1,
        buscar: termino,
        tipo_id: tipoId,
        subtipo_id: subtipoId,
        activo,
        ...(conLocales ? { local_id: localId } : {}),
      }
      const data = await fetchFn(params)
      setHayMas(data.length > LIMIT)
      setItems(data.slice(0, LIMIT))
    } finally {
      setLoadingLista(false)
    }
  }

  // ── Búsqueda con debounce ─────────────────────────────────────────────────
  const handleBusqueda = (e) => {
    const val = e.target.value
    setBusqueda(val) // para mantener filtros entre nuevos fetchs con nuevos filtros
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setPagina(0)
      _fetch(val, 0, filtroTipoId, filtroSubtipoId, filtroLocalId, filtroActivo)
    }, 400)
  }

  // ── Paginación ─────────────────────────────────────────────────────────────
  const irAPagina = (nueva) => {
    setPagina(nueva)
    _fetch(busqueda, nueva, filtroTipoId, filtroSubtipoId, filtroLocalId, filtroActivo)
  }

  // ── Filtro tipo ────────────────────────────────────────────────────────────
  const handleFiltroTipo = (tipoId) => {
    const nuevo = filtroTipoId === tipoId ? null : tipoId
    setFiltroTipoId(nuevo)
    setFiltroSubtipoId(null)
    setSubtiposFiltro([])
    setPagina(0)
    _fetch(busqueda, 0, nuevo, null, filtroLocalId, filtroActivo)
    if (nuevo) {
      api.listarSubtipos({ tipo_id: nuevo, buscar: '' })
        .then(data => setSubtiposFiltro(data.map(s => ({ value: s.subtipo_id, label: s.nombre }))))
        .catch(() => {})
    }
  }

  // ── Filtro subtipo ─────────────────────────────────────────────────────────
  const handleFiltroSubtipo = (subtipoId) => {
    const nuevo = filtroSubtipoId === subtipoId ? null : subtipoId
    setFiltroSubtipoId(nuevo)
    setPagina(0)
    _fetch(busqueda, 0, filtroTipoId, nuevo, filtroLocalId, filtroActivo)
  }

  // ── Filtro local (solo cuando conLocales = true) ───────────────────────────
  const handleFiltroLocal = (localId) => {
    const nuevo = filtroLocalId === localId ? null : localId
    setFiltroLocalId(nuevo)
    setPagina(0)
    _fetch(busqueda, 0, filtroTipoId, filtroSubtipoId, nuevo, filtroActivo)
  }

  // ── Filtro activo ──────────────────────────────────────────────────────────
  const handleFiltroActivo = (valor) => {
    const nuevo = filtroActivo === valor ? null : valor
    setFiltroActivo(nuevo)
    setPagina(0)
    _fetch(busqueda, 0, filtroTipoId, filtroSubtipoId, filtroLocalId, nuevo)
  }

  // ── Limpiar todos los filtros ──────────────────────────────────────────────
  const limpiarFiltros = () => {
    setBusqueda('')
    setFiltroTipoId(null)
    setFiltroSubtipoId(null)
    setFiltroLocalId(null)
    setFiltroActivo(true)
    setSubtiposFiltro([])
    setPagina(0)
    _fetch('', 0, null, null, null, true)
  }

  // ── Refetch con los filtros actuales (tras crear / editar / eliminar) ──────
  const refetch = () =>
    _fetch(busqueda, pagina, filtroTipoId, filtroSubtipoId, filtroLocalId, filtroActivo)

  const refetchTipos = () =>
    api.listarTipos({ buscar: '' })
      .then(data => setTiposFiltro(data.map(t => ({ value: t.tipo_id, label: t.nombre }))))
      .catch(() => {})

  const refetchSubtipos = () =>
    api.listarSubtipos({ buscar: '' })
      .then(data => setSubtipos(data.map(s => ({ value: s.subtipo_id, label: s.nombre }))))
      .catch(() => {})

  const hayFiltrosActivos = !!(filtroTipoId || filtroSubtipoId || filtroLocalId || filtroActivo !== true)

  return {
    // Lista
    items, loadingLista,
    // Paginación
    pagina, hayMas, irAPagina,
    // Búsqueda
    busqueda, handleBusqueda,
    // Valores de filtros (para highlight de chips y para exportar)
    filtroTipoId, filtroSubtipoId, filtroLocalId, filtroActivo,
    // Handlers de filtros
    handleFiltroTipo, handleFiltroSubtipo, handleFiltroLocal, handleFiltroActivo,
    // Opciones del panel
    tiposFiltro, subtiposFiltro, locales, usuarios,
    // Catálogos y helpers (solo si conCatalogos = true)
    nombreTipo, nombreSubtipo,
    // Utilidades
    limpiarFiltros, hayFiltrosActivos, refetch, refetchTipos, refetchSubtipos,
  }
}