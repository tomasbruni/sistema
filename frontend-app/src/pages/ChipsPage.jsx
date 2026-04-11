import { useEffect, useRef, useState } from 'react'
import './AccesoriosPage.css'
import { api, LIMIT } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import SelectorLocalReceptor from '../components/chips/SelectorLocalReceptor'
import FormularioAgregarChip from '../components/chips/FormularioAgregarChip'
import CarritoChips from '../components/chips/CarritoChips'

// ─── ESTADOS POSIBLES ────────────────────────────────────────────────────────
const ESTADOS = ['DISPONIBLE', 'VENDIDO']

// ─── ESTADO INICIAL DEL FORMULARIO ──────────────────────────────────────────
const formVacio = {
  compania:     '',
  numero_serie: '',
  precio:       '',
  local_id:     null,
  estado:       'DISPONIBLE',
}

// ─── COMPONENTE PRINCIPAL ────────────────────────────────────────────────────
export default function ChipsPage() {
  const { alerta, mostrarAlerta }       = useAlerta()

  const [chips, setChips]               = useState([])
  const [form, setForm]                 = useState(formVacio)
  const [editandoId, setEditandoId]     = useState(null)
  const [mostrarForm, setMostrarForm]   = useState(false)
  const [loading, setLoading]           = useState(false)
  const [loadingLista, setLoadingLista] = useState(false)

  const [locales, setLocales]           = useState([])
  const [usuarios, setUsuarios]         = useState([])
  const COMPANIAS = ['CLARO', 'PERSONAL', 'MOVISTAR', 'TUENTI']

  // Filtros
  const [filtroLocalId, setFiltroLocalId]   = useState(null)
  const [filtroEstado, setFiltroEstado]     = useState(null)
  const [filtroCompania, setFiltroCompania] = useState(null)

  // Búsqueda y exportar
  const [busqueda, setBusqueda]           = useState('')
  const debounceRef                       = useRef(null)
  const [loadingExport, setLoadingExport] = useState(false)

  // Paginación
  const [pagina, setPagina]   = useState(0)
  const [hayMas, setHayMas]   = useState(false)

  // ── Ingreso por lote ──────────────────────────────────────────────────────
  const [modoIngreso, setModoIngreso]       = useState(false)
  const [loteLocalId, setLoteLocalId]       = useState(null)
  const [loteReceptorId, setLoteReceptorId] = useState(null)
  const [loteObs, setLoteObs]               = useState('')
  const [carrito, setCarrito]               = useState([])
  const [loadingLote, setLoadingLote]       = useState(false)
  const carritoKeyRef                       = useRef(0)

  // ── Carga inicial ─────────────────────────────────────────────────────────
  useEffect(() => {
    fetchChips(0, null, null, null, '')
    api.listarLocales().then(setLocales).catch(() => {})
    api.listarUsuarios().then(setUsuarios).catch(() => {})
  }, [])

  // ── Lista principal ───────────────────────────────────────────────────────
  const fetchChips = async (pag, localId = filtroLocalId, estado = filtroEstado, compania = filtroCompania, buscar = busqueda) => {
    setLoadingLista(true)
    try {
      const data = await api.listarChips({
        skip: pag * LIMIT, limit: LIMIT + 1,
        local_id: localId,
        estado,
        compania,
        buscar,
      })
      setHayMas(data.length > LIMIT)
      setChips(data.slice(0, LIMIT))
    } catch (err) {
      mostrarAlerta('error', `Error al cargar chips: ${err.message}`)
    } finally {
      setLoadingLista(false)
    }
  }

  const irAPagina = (nueva) => {
    setPagina(nueva)
    fetchChips(nueva)
  }

  // ── Búsqueda ─────────────────────────────────────────────────────────────
  const handleBusqueda = (e) => {
    const val = e.target.value
    setBusqueda(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setPagina(0)
      fetchChips(0, filtroLocalId, filtroEstado, filtroCompania, val)
    }, 400)
  }

  // ── Filtros ───────────────────────────────────────────────────────────────
  const handleFiltroLocal = (localId) => {
    const nuevo = filtroLocalId === localId ? null : localId
    setFiltroLocalId(nuevo)
    setPagina(0)
    fetchChips(0, nuevo, filtroEstado, filtroCompania, busqueda)
  }

  const handleFiltroEstado = (estado) => {
    const nuevo = filtroEstado === estado ? null : estado
    setFiltroEstado(nuevo)
    setPagina(0)
    fetchChips(0, filtroLocalId, nuevo, filtroCompania, busqueda)
  }

  const handleFiltroCompania = (compania) => {
    const nuevo = filtroCompania === compania ? null : compania
    setFiltroCompania(nuevo)
    setPagina(0)
    fetchChips(0, filtroLocalId, filtroEstado, nuevo, busqueda)
  }

  const limpiarFiltros = () => {
    setFiltroLocalId(null)
    setFiltroEstado(null)
    setFiltroCompania(null)
    setBusqueda('')
    setPagina(0)
    fetchChips(0, null, null, null, '')
  }

  // ── Exportar ─────────────────────────────────────────────────────────────
  const handleExportar = async () => {
    setLoadingExport(true)
    try {
      const blob = await api.exportarChips({
        local_id: filtroLocalId,
        estado:   filtroEstado,
        compania: filtroCompania,
        buscar:   busqueda,
      })
      const url  = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href  = url
      link.download = 'chips.xlsx'
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      mostrarAlerta('error', `Error al exportar: ${err.message}`)
    } finally {
      setLoadingExport(false)
    }
  }

  // ── Form helpers ──────────────────────────────────────────────────────────
  const handleChange = (e) => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  const abrirCrear = () => {
    setForm(formVacio)
    setEditandoId(null)
    setMostrarForm(true)
  }

  const abrirEditar = (chip) => {
    setForm({
      compania:     chip.compania,
      numero_serie: chip.numero_serie,
      precio:       chip.precio,
      local_id:     chip.local_id ?? null,
      estado:       chip.estado,
    })
    setEditandoId(chip.chip_id)
    setMostrarForm(true)
  }

  const cancelar = () => {
    setMostrarForm(false)
    setEditandoId(null)
    setForm(formVacio)
  }

  // ── Submit ────────────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    const body = {
      compania:     form.compania.trim(),
      numero_serie: form.numero_serie.trim(),
      precio:       Number(form.precio),
      local_id:     Number(form.local_id),
      estado:       form.estado,
    }

    try {
      if (editandoId) {
        await api.actualizarChip(editandoId, body)
        mostrarAlerta('success', 'Chip actualizado correctamente.')
      } else {
        await api.crearChip(body)
        mostrarAlerta('success', 'Chip creado correctamente.')
      }
      cancelar()
      fetchChips(pagina)
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  // ── Eliminar ──────────────────────────────────────────────────────────────
  const handleEliminar = async (chip) => {
    if (!window.confirm(`¿Eliminar el chip con N° de serie ${chip.numero_serie}?`)) return
    try {
      await api.eliminarChip(chip.chip_id)
      mostrarAlerta('success', 'Chip eliminado.')
      fetchChips(pagina)
    } catch (err) {
      mostrarAlerta('error', `Error al eliminar: ${err.message}`)
    }
  }

  // ── Ingreso por lote: handlers ────────────────────────────────────────────
  const abrirIngreso = () => {
    setModoIngreso(true)
    setMostrarForm(false)
    setCarrito([])
    setLoteLocalId(null)
    setLoteReceptorId(null)
    setLoteObs('')
  }

  const cancelarIngreso = () => {
    setModoIngreso(false)
    setCarrito([])
  }

  const handleAgregarAlCarrito = (chip) => {
    const duplicado = carrito.some(c => c.numero_serie === chip.numero_serie)
    if (duplicado) {
      mostrarAlerta('error', `El N° de serie ${chip.numero_serie} ya está en el lote.`)
      return
    }
    carritoKeyRef.current += 1
    setCarrito(prev => [...prev, { ...chip, _key: carritoKeyRef.current }])
  }

  const handleEliminarDelCarrito = (key) => {
    setCarrito(prev => prev.filter(c => c._key !== key))
  }

  const handleConfirmarLote = async () => {
    if (!loteLocalId) { mostrarAlerta('error', 'Seleccioná un local.'); return }
    if (carrito.length === 0) { mostrarAlerta('error', 'El lote está vacío.'); return }

    setLoadingLote(true)
    try {
      const res = await api.ingresarLoteChips({
        local_id:     loteLocalId,
        receptor_id:  loteReceptorId,
        observaciones: loteObs || null,
        chips: carrito.map(({ compania, numero_serie, precio }) => ({ compania, numero_serie, precio })),
      })

      // Descargar remito PDF
      const blob = await api.generarIngresoChipsPdf(res.ingreso_lote_chip_id)
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `ingreso_chips_${res.ingreso_lote_chip_id}.pdf`
      a.click()
      URL.revokeObjectURL(url)

      mostrarAlerta('success', `${res.total_chips} chips ingresados. Remito descargado.`)
      cancelarIngreso()
      fetchChips(0)
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingLote(false)
    }
  }

  // ── Helpers de display ────────────────────────────────────────────────────
  const nombreLocal = (id) => locales.find(l => l.local_id === id)?.nombre ?? id

  const estadoClase = (estado) => {
    const mapa = {
      DISPONIBLE: 'activo',
      VENDIDO:    'inactivo',
    }
    return mapa[estado] ?? ''
  }

  // ─── RENDER ───────────────────────────────────────────────────────────────
  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Chips</h2>
        {!mostrarForm && !modoIngreso && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-primary" onClick={abrirCrear}>+ Nuevo chip</button>
            <button className="btn btn-secondary" onClick={abrirIngreso}>Ingresar lote</button>
          </div>
        )}
        {modoIngreso && (
          <button className="btn btn-secondary" onClick={cancelarIngreso}>Cancelar ingreso</button>
        )}
      </div>

      {/* Alerta */}
      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>{alerta.msg}</div>
      )}

      {/* ── Modo ingreso por lote ── */}
      {modoIngreso && (
        <>
          <SelectorLocalReceptor
            localId={loteLocalId}
            setLocalId={setLoteLocalId}
            receptorId={loteReceptorId}
            setReceptorId={setLoteReceptorId}
            observaciones={loteObs}
            setObservaciones={setLoteObs}
            locales={locales}
            usuarios={usuarios}
          />
          <FormularioAgregarChip onAgregar={handleAgregarAlCarrito} />
          <CarritoChips
            carrito={carrito}
            onEliminar={handleEliminarDelCarrito}
            onConfirmar={handleConfirmarLote}
            loading={loadingLote}
          />
        </>
      )}

      {/* ── Formulario chip individual ── */}
      {mostrarForm && (
        <div className="form-card">
          <h3>{editandoId ? 'Editar chip' : 'Nuevo chip'}</h3>
          <form onSubmit={handleSubmit} className="acc-form">

            <div className="form-row">
              <div className="form-group">
                <label>Compañía *</label>
                <select
                  name="compania"
                  value={form.compania}
                  onChange={handleChange}
                  required
                >
                  <option value="">Seleccionar</option>
                  {COMPANIAS.map(c => <option key={c} value={c}>{c.charAt(0) + c.slice(1).toLowerCase()}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Número de serie *</label>
                <input
                  name="numero_serie"
                  value={form.numero_serie}
                  onChange={handleChange}
                  required
                  placeholder="Ej: 8954010123456789"

                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Precio *</label>
                <input
                  name="precio"
                  type="number"
                  value={form.precio}
                  onChange={handleChange}
                  required
                  min={0}
                  placeholder="Ej: 1500"
                />
              </div>
              <div className="form-group">
                <label>Local *</label>
                <select name="local_id" value={form.local_id ?? ''} onChange={handleChange} required>
                  <option value="">Seleccionar local...</option>
                  {locales.map(l => (
                    <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Estado *</label>
                <select name="estado" value={form.estado} onChange={handleChange} required>
                  {ESTADOS.map(e => (
                    <option key={e} value={e}>{e}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-actions">
              <button type="button" className="btn btn-secondary" onClick={cancelar} disabled={loading}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Guardando...' : editandoId ? 'Guardar cambios' : 'Crear chip'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Buscador y toolbar ── */}
      {!mostrarForm && !modoIngreso && (
        <div className="lista-toolbar">
          <input
            className="buscador"
            type="search"
            placeholder="Buscar por número de serie..."
            value={busqueda}
            onChange={handleBusqueda}
          />
          <button
            className="btn btn-export"
            onClick={handleExportar}
            disabled={loadingExport}
            title="Exporta los resultados con los filtros actuales"
          >
            {loadingExport ? 'Exportando...' : '⬇ Exportar Excel'}
          </button>
        </div>
      )}

      {/* ── Filtros ── */}
      {!mostrarForm && !modoIngreso && (
        <div className="filtros-panel">
          <span className="filtros-label">Filtrar por:</span>

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

          <div className="filtros-row">
            <span className="filtros-sublabel">Estado:</span>
            <div className="filtros-chips">
              {ESTADOS.map(e => (
                <button
                  key={e}
                  className={`filtro-chip filtro-chip-estado ${filtroEstado === e ? 'filtro-chip-activo' : ''}`}
                  onClick={() => handleFiltroEstado(e)}
                >
                  {e}
                </button>
              ))}
            </div>
          </div>

          <div className="filtros-row">
            <span className="filtros-sublabel">Compañía:</span>
            <div className="filtros-chips">
              {COMPANIAS.map(c => (
                <button
                  key={c}
                  className={`filtro-chip ${filtroCompania === c ? 'filtro-chip-activo' : ''}`}
                  onClick={() => handleFiltroCompania(c)}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {(filtroLocalId || filtroEstado || filtroCompania) && (
            <button className="btn-limpiar-filtros" onClick={limpiarFiltros}>
              ✕ Limpiar filtros
            </button>
          )}
        </div>
      )}

      {/* ── Tabla ── */}
      {!modoIngreso && (
        loadingLista ? (
          <p className="empty-msg">Cargando...</p>
        ) : chips.length === 0 ? (
          <p className="empty-msg">No hay chips registrados.</p>
        ) : (
          <>
            <div className="table-wrapper">
              <table className="acc-table">
                <thead>
                  <tr>
                    <th>N° de serie</th>
                    <th>Compañía</th>
                    <th>Precio</th>
                    <th>Local</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {chips.map(chip => (
                    <tr key={chip.chip_id}>
                      <td><span className="sku-badge">{chip.numero_serie}</span></td>
                      <td>{chip.compania}</td>
                      <td>${chip.precio.toLocaleString()}</td>
                      <td>{nombreLocal(chip.local_id)}</td>
                      <td>
                        <span className={`estado-badge ${estadoClase(chip.estado)}`}>
                          {chip.estado}
                        </span>
                      </td>
                      <td className="acciones-cell">
                        <button className="btn btn-sm btn-secondary" onClick={() => abrirEditar(chip)}>Editar</button>
                        <button className="btn btn-sm btn-danger"    onClick={() => handleEliminar(chip)}>Eliminar</button>
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
        )
      )}
    </div>
  )
}