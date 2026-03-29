import { useEffect, useRef, useState } from 'react'
import './AccesoriosPage.css'
import SearchableSelect from '../components/SearchableSelect/SearchableSelect'
import { api, LIMIT } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import useSelectOptions from '../hooks/useSelectOptions'

const ESTADOS = ['DISPONIBLE', 'VENDIDO', 'REPARACION']

const formVacio = {
  modelo_celular_id: null,
  marca_celular_id: null,
  imei:      '',
  precio:    '',
  local_id:  null,
  estado:    'DISPONIBLE',
}

export default function CelularesPage() {
  const { alerta, mostrarAlerta }         = useAlerta()

  const [celulares, setCelulares]         = useState([])
  const [form, setForm]                   = useState(formVacio)
  const [editandoId, setEditandoId]       = useState(null)
  const [mostrarForm, setMostrarForm]     = useState(false)
  const [loading, setLoading]             = useState(false)
  const [loadingLista, setLoadingLista]   = useState(false)

  const { options, buscadorSelect, setOption }       = useSelectOptions(['marcasCelulares','modelos'])
  const [locales, setLocales]             = useState([])
  const [marcasDisponibles, setMarcasDisponibles] = useState([]) // ["Apple", "Samsung", ...]
  const [modelosDisponibles, setModelosDisponibles] = useState([])

  // Filtros
  const [filtroLocalId, setFiltroLocalId] = useState(null)
  const [filtroEstado, setFiltroEstado]   = useState(null)
  const [filtroMarca, setFiltroMarca]     = useState(null)
  const [filtroModelo, setFiltroModelo]   = useState(null)
  const [listaModelosFiltro, setListaModelosFiltro] = useState([])

  // Búsqueda IMEI
  const [busquedaImei, setBusquedaImei]   = useState('')
  const debounceRef                       = useRef(null)

  // Paginación
  const [pagina, setPagina]               = useState(0)
  const [hayMas, setHayMas]               = useState(false)

  // ── Carga inicial ─────────────────────────────────────────────────────────
  useEffect(() => {
    fetchCelulares(0, null, null, null, null, '')
    buscadorSelect('marcas', '')
    api.listarLocales().then(setLocales).catch(() => {})
    api.listarMarcasCelulares()
      .then(data => setMarcasDisponibles(data))
      .catch(() => {})
    api.listarModelos()
      .then(data => setModelosDisponibles(data))
      .catch(() => {})
  }, [])

  // ── Lista principal ───────────────────────────────────────────────────────
  const fetchCelulares = async (
    pag,
    localId  = filtroLocalId,
    estado   = filtroEstado,
    marca    = filtroMarca,
    modelo   = filtroModelo,
    imei     = busquedaImei,
  ) => {
    setLoadingLista(true)
    try {
      const data = await api.listarCelulares({
        skip: pag * LIMIT, limit: LIMIT + 1,
        local_id: localId,
        estado,
        marca_celular_id: marca,
        modelo_celular_id: modelo,
        imei,
      })
      setHayMas(data.length > LIMIT)
      setCelulares(data.slice(0, LIMIT))
    } catch (err) {
      mostrarAlerta('error', `Error al cargar celulares: ${err.message}`)
    } finally {
      setLoadingLista(false)
    }
  }

  const irAPagina = (nueva) => {
    setPagina(nueva)
    fetchCelulares(nueva)
  }

  // ── Búsqueda IMEI con debounce ────────────────────────────────────────────
  const handleBusquedaImei = (e) => {
    const val = e.target.value
    setBusquedaImei(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setPagina(0)
      fetchCelulares(0, filtroLocalId, filtroEstado, filtroMarca, val)
    }, 400)
  }

  // ── Filtros ───────────────────────────────────────────────────────────────
  const handleFiltroLocal = (localId) => {
    const nuevo = filtroLocalId === localId ? null : localId
    setFiltroLocalId(nuevo)
    setPagina(0)
    fetchCelulares(0, nuevo, filtroEstado, filtroMarca, filtroModelo)
  }

  const handleFiltroEstado = (estado) => {
    const nuevo = filtroEstado === estado ? null : estado
    setFiltroEstado(nuevo)
    setPagina(0)
    fetchCelulares(0, filtroLocalId, nuevo, filtroMarca, filtroModelo)
  }

  const handleFiltroMarca = (marca) => {
    const nuevo = filtroMarca === marca ? null : marca
    setFiltroMarca(nuevo)
    setFiltroModelo(null)
    setListaModelosFiltro([])
    setPagina(0)
    fetchCelulares(0, filtroLocalId, filtroEstado, nuevo, filtroModelo)
    if (nuevo) {
      api.listarModelos({ marca_celular_id: nuevo, buscar: '' })
        .then(data => setListaModelosFiltro(data.map(s => ({ value: s.subtipo_id, label: s.nombre }))))
        .catch(() => {})
    }
  }

  const handleFiltroModelo = (modelo) => {
    const nuevo = filtroModelo === modelo ? null : modelo
    setFiltroModelo(nuevo)
    setPagina(0)
    fetchCelulares(0, filtroLocalId, filtroEstado, filtroMarca, filtroModelo)
  }  

  const limpiarFiltros = () => {
    setFiltroLocalId(null)
    setFiltroEstado(null)
    setFiltroMarca(null)
    setFiltroModelo(null)
    setListaModelosFiltro(null)
    setBusquedaImei('')
    setPagina(0)
    fetchCelulares(0, null, null, null, null, '')
  }

  const hayFiltrosActivos = filtroLocalId || filtroEstado || filtroMarca || busquedaImei

  // ── Form helpers ──────────────────────────────────────────────────────────
  const handleChange = (e) => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  const setFormField = (field) => (value) =>
    setForm(prev => ({ ...prev, [field]: value }))

  const abrirCrear = () => {
    setForm(formVacio)
    setEditandoId(null)
    setMostrarForm(true)
    buscadorSelect('modelos', '')
  }

  const abrirEditar = (cel) => {
    setForm({
      marca_celular_id: cel.marca_celular_id ?? null,
      modelo_celular_id: cel.modelo_celular_id ?? null,
      imei:      cel.imei,
      precio:    cel.precio,
      local_id:  cel.local_id ?? null,
      estado:    cel.estado,
    })
    setEditandoId(cel.celular_id)
    setMostrarForm(true)
    buscadorSelect('marcasCelulares', '')
    if (cel.marca_celular_id) {
      buscadorSelect('modelos', '', { marca_celular_id: cel.marca_celular_id })
    }
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
      marca_celular_id: form.marca_celular_id,
      modelo_celular_id: form.modelo_celular_id,
      imei:      form.imei.trim(),
      precio:    Number(form.precio),
      local_id:  form.local_id,
      estado:    form.estado,
    }
    try {
      if (editandoId) {
        await api.actualizarCelular(editandoId, body)
        mostrarAlerta('success', 'Celular actualizado correctamente.')
      } else {
        await api.crearCelular(body)
        mostrarAlerta('success', 'Celular creado correctamente.')
      }
      cancelar()
      fetchCelulares(pagina)
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  // ── Eliminar ──────────────────────────────────────────────────────────────
  const handleEliminar = async (cel) => {
    if (!window.confirm(`¿Eliminar el celular con IMEI ${cel.imei}?`)) return
    try {
      await api.eliminarCelular(cel.celular_id)
      mostrarAlerta('success', 'Celular eliminado.')
      fetchCelulares(pagina)
    } catch (err) {
      mostrarAlerta('error', `Error al eliminar: ${err.message}`)
    }
  }

  // ── Helpers de display ────────────────────────────────────────────────────
  const nombreLocal  = (id) => locales.find(l => l.local_id === id)?.nombre ?? id
  const nombreMarca = (id) => marcasDisponibles.find(m => m.marca_celular_id === id)?.nombre ?? id
  const nombreModelo = (id) => modelosDisponibles.find(m => m.modelo_celular_id === id)?.nombre ?? id

  const estadoClase = (estado) => ({
    DISPONIBLE: 'activo',
    VENDIDO:    'inactivo',
    REPARACION: 'warning',
  })[estado] ?? ''

  // ─── RENDER ───────────────────────────────────────────────────────────────
  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Celulares</h2>
        {!mostrarForm && (
          <button className="btn btn-primary" onClick={abrirCrear}>+ Nuevo celular</button>
        )}
      </div>

      {alerta && <div className={`alerta alerta-${alerta.tipo}`}>{alerta.msg}</div>}

      {/* ── Formulario ── */}
      {mostrarForm && (
        <div className="form-card">
          <h3>{editandoId ? 'Editar celular' : 'Nuevo celular'}</h3>
          <form onSubmit={handleSubmit} className="acc-form">
            <div className="form-row">
              <div className="form-group">
                <label>IMEI *</label>
                <input name="imei" value={form.imei} onChange={handleChange} required placeholder="Ej: 123456789012345" />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Marca celular</label>
                <SearchableSelect
                  options={options.marcasCelulares}
                  value={form.marca_celular_id}
                  onChange={(val) => {
                    setFormField('marca_celular_id')(val)
                    setFormField('modelo_celular_id')(null)
                    setOption('modelos', [])
                    if (val) buscadorSelect('modelos', '', { marca_celular_id: val })
                  }}
                  onSearch={(t) => buscadorSelect('marcasCelulares', t)}
                  placeholder="Buscar marca de celular..."
                />
              </div>
              <div className="form-group">
                <label>Modelo celular</label>
                <SearchableSelect
                  options={options.modelos}
                  value={form.modelo_celular_id}
                  onChange={setFormField('modelo_celular_id')}
                  onSearch={(t) => buscadorSelect('modelos', t, { marca_celular_id: form.marca_celular_id })}
                  placeholder="Buscar modelo..."
                  disabled={!form.marca_celular_id}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Precio *</label>
                <input name="precio" type="number" value={form.precio} onChange={handleChange} required min={0} placeholder="Ej: 150000" />
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
                  {ESTADOS.map(e => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>
            </div>

            <div className="form-actions">
              <button type="button" className="btn btn-secondary" onClick={cancelar} disabled={loading}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Guardando...' : editandoId ? 'Guardar cambios' : 'Crear celular'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Buscador y filtros ── */}
      {!mostrarForm && (
        <>
          <div className="lista-toolbar">
            <input
              className="buscador"
              type="search"
              placeholder="Buscar por IMEI..."
              value={busquedaImei}
              onChange={handleBusquedaImei}
            />
          </div>

          <div className="filtros-panel">
            <span className="filtros-label">Filtrar por:</span>

            {marcasDisponibles.length > 0 && (
              <div className="filtros-row">
                <span className="filtros-sublabel">Tipo:</span>
                <SearchableSelect
                  options={options.marcasCelulares}
                  value={filtroMarca}
                  onChange={(val) => handleFiltroMarca(val)}
                  onSearch={(t) => buscadorSelect('marcasCelulares', t)}
                  placeholder="Filtrar por marca"
                />
              </div>
            )}

            {filtroMarca && listaModelosFiltro.length > 0 && (
              <div className="filtros-subtipos">
                <span className="filtros-sublabel">Subtipo:</span>
                <div className='ss-filtro-subtipo'>
                  <SearchableSelect
                    options={options.modelos}
                    value={filtroModelo}
                    onChange={(id) => handleFiltroModelo(id)}
                    onSearch={(t) => buscadorSelect('modelos', t)}
                    placeholder="Filtrar por modelo"
                  />
                </div>
              </div>)}


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
                    className={`filtro-chip ${filtroEstado === e ? 'filtro-chip-activo' : ''}`}
                    onClick={() => handleFiltroEstado(e)}
                  >
                    {e}
                  </button>
                ))}
              </div>
            </div>

            {hayFiltrosActivos && (
              <button className="btn-limpiar-filtros" onClick={limpiarFiltros}>✕ Limpiar filtros</button>
            )}
          </div>
        </> 
      )}

      {/* ── Tabla ── */}
      {loadingLista ? (
        <p className="empty-msg">Cargando...</p>
      ) : celulares.length === 0 ? (
        <p className="empty-msg">No hay celulares registrados.</p>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="acc-table">
              <thead>
                <tr>
                  <th>IMEI</th>
                  <th>Marca</th>
                  <th>Modelo</th>
                  <th>Precio</th>
                  <th>Local</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {celulares.map(cel => (
                  <tr key={cel.celular_id}>
                    <td><span className="sku-badge">{cel.imei}</span></td>
                    <td>{nombreMarca(cel.marca_celular_id)}</td>
                    <td>{nombreModelo(cel.modelo_celular_id)}</td>
                    <td>${cel.precio.toLocaleString()}</td>
                    <td>{nombreLocal(cel.local_id)}</td>
                    <td>
                      <span className={`estado-badge ${estadoClase(cel.estado)}`}>
                        {cel.estado}
                      </span>
                    </td>
                    <td className="acciones-cell">
                      <button className="btn btn-sm btn-secondary" onClick={() => abrirEditar(cel)}>Editar</button>
                      <button className="btn btn-sm btn-danger"    onClick={() => handleEliminar(cel)}>Eliminar</button>
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
    </div>
  )
}