import { useState, useRef } from 'react'
import './AccesoriosPage.css'
import SearchableSelect from '../components/SearchableSelect/SearchableSelect'
import { api } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import useSelectOptions from '../hooks/useSelectOptions'
import useListaFiltrada from '../hooks/useListaFiltrada'
import ModalCrearTipoSubtipo from '../components/accesorios/ModalCrearTipoSubtipo'

const formVacio = {
  nombre: '',
  precio: '',
  tipo_id: null,
  subtipo_id: null,
  marca_celular_id: null,
  modelo_celular_id: null,
  marca_id: null,
  activo: true,
}

export default function AccesoriosPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()

  const {
    items: accesorios, loadingLista,
    pagina, hayMas, irAPagina,
    busqueda, handleBusqueda,
    filtroTipoId, filtroSubtipoId, filtroActivo,
    handleFiltroTipo, handleFiltroSubtipo, handleFiltroActivo,
    tiposFiltro, subtiposFiltro,
    limpiarFiltros, hayFiltrosActivos,
    refetch, refetchTipos, refetchSubtipos,
    nombreTipo, nombreSubtipo,
  } = useListaFiltrada((p) => api.listarAccesorios(p), { conCatalogos: true })

  const [loading, setLoading]             = useState(null) // null | 'export' | 'form' | 'masivo'
  const [form, setForm]                   = useState(formVacio)
  const [editandoId, setEditandoId]       = useState(null)
  const [mostrarForm, setMostrarForm]     = useState(false)
  const [modalNuevo, setModalNuevo]       = useState(null) // 'tipo' | 'subtipo' | null
  const [mostrarFormMasivo, setMostrarFormMasivo] = useState(false)
  const [formMasivo, setFormMasivo]               = useState({ tipo_id: null, subtipo_id: null, nuevo_precio: '' })
  const nombreRef = useRef(null)

  const { options, setOption, buscadorSelect } =
    useSelectOptions(['tipos', 'subtipos', 'marcas', 'marcasCelulares', 'modelos'])

  // ── Crear tipo/subtipo desde el form ─────────────────────────────────────
  const handleCrearTipoSubtipo = async (body) => {
    if (modalNuevo === 'tipo') {
      const nuevo = await api.crearTipo(body)
      await buscadorSelect('tipos', '')
      setFormField('tipo_id')(nuevo.tipo_id)
      setFormField('subtipo_id')(null)
      setOption('subtipos', [])
      refetchTipos()
    } else {
      const nuevo = await api.crearSubtipo(body)
      await buscadorSelect('subtipos', '', { tipo_id: form.tipo_id })
      setFormField('subtipo_id')(nuevo.subtipo_id)
      refetchSubtipos()
    }
  }

  // ── Exportar ─────────────────────────────────────────────────────────────
  const handleExportar = async () => {
    setLoading('export')
    try {
      const blob = await api.exportarAccesorios({
        buscar:     busqueda,
        tipo_id:    filtroTipoId,
        subtipo_id: filtroSubtipoId,
        activo:     filtroActivo,
      })
      const url  = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href  = url
      link.download = 'accesorios.xlsx'
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      mostrarAlerta('error', `Error al exportar: ${err.message}`)
    } finally {
      setLoading(null)
    }
  }

  // ── Form helpers ──────────────────────────────────────────────────────────
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  const setFormField = (field) => (value) =>
    setForm(prev => ({ ...prev, [field]: value }))

  const abrirCrear = () => {
    setForm(formVacio)
    setEditandoId(null)
    setMostrarForm(true)
    buscadorSelect('tipos', '')
    buscadorSelect('marcas', '')
    buscadorSelect('marcasCelulares', '')
    setOption('subtipos', [])
    setOption('modelos', [])
  }

  const abrirEditar = (acc) => {
    setForm({
      nombre:           acc.nombre,
      precio:           acc.precio,
      tipo_id:          acc.tipo_id          ?? null,
      subtipo_id:       acc.subtipo_id       ?? null,
      marca_celular_id: acc.marca_celular_id ?? null,
      modelo_celular_id: acc.modelo_celular_id ?? null,
      marca_id:         acc.marca_id         ?? null,
      activo:           acc.activo,
    })
    setEditandoId(acc.accesorio_id)
    setMostrarForm(true)
    buscadorSelect('tipos', '')
    buscadorSelect('marcas', '')
    buscadorSelect('marcasCelulares', '')
    buscadorSelect('subtipos', '', { tipo_id: acc.tipo_id })
    // precargar modelos filtrados por la marca actual
    if (acc.marca_celular_id) {
      buscadorSelect('modelos', '', { marca_celular_id: acc.marca_celular_id })
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
    setLoading('form')

    const body = {
      nombre:            form.nombre,
      precio:            parseInt(form.precio),
      tipo_id:           form.tipo_id           ? parseInt(form.tipo_id)           : undefined,
      subtipo_id:        form.subtipo_id        ? parseInt(form.subtipo_id)        : null,
      marca_celular_id:  form.marca_celular_id  ? parseInt(form.marca_celular_id)  : null,
      modelo_celular_id: form.modelo_celular_id ? parseInt(form.modelo_celular_id) : null,
      marca_id:          form.marca_id          ? parseInt(form.marca_id)          : null,
      activo:            form.activo,
    }

    try {
      if (editandoId) {
        await api.actualizarAccesorio(editandoId, body)
        mostrarAlerta('success', 'Accesorio actualizado correctamente.')
        refetch()
        cancelar()
      } else {
        await api.crearAccesorio(body)
        mostrarAlerta('success', 'Accesorio creado correctamente.')
        refetch()
        setForm(prev => ({ ...prev, nombre: '', precio: '' }))
        setTimeout(() => nombreRef.current?.focus(), 0)
      }
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoading(null)
    }
  }

  // ── Cambio de precio masivo ───────────────────────────────────────────────
  const handleSubmitMasivo = async (e) => {
    e.preventDefault()
    if (!formMasivo.tipo_id) return
    const n = parseInt(formMasivo.nuevo_precio)
    if (isNaN(n) || n < 0) { mostrarAlerta('error', 'Precio inválido'); return }

    setLoading('masivo')
    try {
      const body = {
        tipo_id:     parseInt(formMasivo.tipo_id),
        subtipo_id:  formMasivo.subtipo_id ? parseInt(formMasivo.subtipo_id) : null,
        nuevo_precio: n,
      }
      const res = await api.cambioPrecioMasivo(body)
      mostrarAlerta('success', `${res.mensaje} — ${res.accesorios_modificados} accesorio/s modificado/s.`)
      setMostrarFormMasivo(false)
      setFormMasivo({ tipo_id: null, subtipo_id: null, nuevo_precio: '' })
      refetch()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoading(null)
    }
  }

  // ── Eliminar / Activar ────────────────────────────────────────────────────
  const handleEliminar = async (acc) => {
    if (!window.confirm(`¿Eliminar "${acc.nombre}"?\nSi tiene ventas o detalles, se desactivará.`)) return
    try {
      const res = await api.eliminarAccesorio(acc.accesorio_id)
      mostrarAlerta('success', `"${acc.nombre}" ${res.mensaje}.`)
      refetch()
    } catch (err) {
      mostrarAlerta('error', `Error al eliminar: ${err.message}`)
    }
  }

  const handleActivar = async (acc) => {
    if (!window.confirm(`¿Reactivar "${acc.nombre}"?`)) return
    try {
      await api.actualizarAccesorio(acc.accesorio_id, { activo: true })
      mostrarAlerta('success', `"${acc.nombre}" reactivado correctamente.`)
      refetch()
    } catch (err) {
      mostrarAlerta('error', `Error al activar: ${err.message}`)
    }
  }

  // ─── RENDER ───────────────────────────────────────────────────────────────
  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Accesorios</h2>
        {!mostrarForm && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-secondary" onClick={() => { setMostrarFormMasivo(v => !v) }}>
              Cambio precio masivo
            </button>
            <button className="btn btn-primary" onClick={abrirCrear}>
              + Nuevo accesorio
            </button>
          </div>
        )}
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.msg}</span>
          <button className="alerta-cerrar" onClick={cerrarAlerta}>✕</button>
        </div>
      )}

      {/* ── Cambio precio masivo ── */}
      {mostrarFormMasivo && !mostrarForm && (
        <div className="form-card">
          <h3>Cambio de precio masivo</h3>
          <form onSubmit={handleSubmitMasivo} className="acc-form">
            <div className="form-row">
              <div className="form-group">
                <label>Tipo *</label>
                <SearchableSelect
                  options={options.tipos}
                  value={formMasivo.tipo_id}
                  onChange={(val) => {
                    setFormMasivo(prev => ({ ...prev, tipo_id: val, subtipo_id: null }))
                    setOption('subtipos', [])
                    if (val) buscadorSelect('subtipos', '', { tipo_id: val })
                  }}
                  onSearch={(t) => buscadorSelect('tipos', t)}
                  placeholder="Seleccionar tipo..."
                />
              </div>
              <div className="form-group">
                <label>Subtipo <small>(opcional)</small></label>
                <SearchableSelect
                  options={options.subtipos}
                  value={formMasivo.subtipo_id}
                  onChange={(val) => setFormMasivo(prev => ({ ...prev, subtipo_id: val }))}
                  onSearch={(t) => buscadorSelect('subtipos', t, { tipo_id: formMasivo.tipo_id })}
                  placeholder="Todos los subtipos"
                  disabled={!formMasivo.tipo_id}
                />
              </div>
              <div className="form-group">
                <label>Nuevo precio *</label>
                <input
                  type="number"
                  min={0}
                  required
                  placeholder="Ej: 3500"
                  value={formMasivo.nuevo_precio}
                  onChange={(e) => setFormMasivo(prev => ({ ...prev, nuevo_precio: e.target.value }))}
                />
              </div>
            </div>
            <div className="form-actions">
              <button type="button" className="btn btn-secondary" onClick={() => { setMostrarFormMasivo(false); setFormMasivo({ tipo_id: null, subtipo_id: null, nuevo_precio: '' }) }}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading === 'masivo' || !formMasivo.tipo_id}>
                {loading === 'masivo' ? 'Aplicando...' : 'Aplicar cambio'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Formulario ── */}
      {mostrarForm && (
        <div className="form-card">
          <h3>{editandoId ? 'Editar accesorio' : 'Nuevo accesorio'}</h3>
          <form onSubmit={handleSubmit} className="acc-form">

            <div className="form-row">
              <div className="form-group">
                <label>Nombre *</label>
                <input ref={nombreRef} name="nombre" value={form.nombre} onChange={handleChange} required placeholder="Ej: Funda iPhone 15" />
              </div>
              <div className="form-group">
                <label>Precio *</label>
                <input name="precio" type="number" value={form.precio} onChange={handleChange} required min={0} placeholder="Ej: 2500" />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Tipo *</label>
                <div style={{ display: 'flex', gap: 6, width: '100%' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <SearchableSelect
                      options={options.tipos}
                      value={form.tipo_id}
                      onChange={(val) => {
                        setFormField('tipo_id')(val)
                        setFormField('subtipo_id')(null)
                        setOption('subtipos', [])
                        if (val) buscadorSelect('subtipos', '', { tipo_id: val })
                      }}
                      onSearch={(t) => buscadorSelect('tipos', t)}
                      placeholder="Buscar tipo..."
                    />
                  </div>
                  <button type="button" className="btn btn-secondary btn-sm" title="Agregar tipo" onClick={() => setModalNuevo('tipo')}>+</button>
                </div>
              </div>
              <div className="form-group">
                <label>Subtipo</label>
                <div style={{ display: 'flex', gap: 6, width: '100%' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <SearchableSelect
                      options={options.subtipos}
                      value={form.subtipo_id}
                      onChange={setFormField('subtipo_id')}
                      onSearch={(t) => buscadorSelect('subtipos', t, { tipo_id: form.tipo_id })}
                      placeholder="Buscar subtipo..."
                      disabled={!form.tipo_id}
                    />
                  </div>
                  <button type="button" className="btn btn-secondary btn-sm" title="Agregar subtipo" onClick={() => setModalNuevo('subtipo')} disabled={!form.tipo_id}>+</button>
                </div>
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
                <label>Marca accesorio</label>
                <SearchableSelect
                  options={options.marcas}
                  value={form.marca_id}
                  onChange={setFormField('marca_id')}
                  onSearch={(t) => buscadorSelect('marcas', t)}
                  placeholder="Buscar marca..."
                />
              </div>
            </div>

            <div className="form-group form-check">
              <label>
                <input name="activo" type="checkbox" checked={form.activo} onChange={handleChange} />
                Activo
              </label>
            </div>

            <div className="form-actions">
              <button type="button" className="btn btn-secondary" onClick={cancelar} disabled={loading === 'form'}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loading === 'form'}>
                {loading === 'form' ? 'Guardando...' : editandoId ? 'Guardar cambios' : 'Crear accesorio'}
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
              placeholder="Buscar por nombre..."
              value={busqueda}
              onChange={handleBusqueda}
            />
            <button
              className="btn btn-export"
              onClick={handleExportar}
              disabled={loading === 'export'}
              title="Exporta los resultados con los filtros actuales"
            >
              {loading === 'export' ? 'Exportando...' : '⬇ Exportar Excel'}
            </button>
          </div>

          <div className="filtros-panel">
            <span className="filtros-label">Filtrar por:</span>

            <div className="filtros-row">
              <span className="filtros-sublabel">Estado:</span>
              <div className="filtros-chips">
                {[{ valor: true, label: 'Activos' }, { valor: false, label: 'Inactivos' }].map(({ valor, label }) => (
                  <button
                    key={label}
                    className={`filtro-chip filtro-chip-estado ${filtroActivo === valor ? 'filtro-chip-activo' : ''}`}
                    onClick={() => handleFiltroActivo(valor)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {tiposFiltro.length > 0 && (
              <div className="filtros-row">
                <span className="filtros-sublabel">Tipo:</span>
                <SearchableSelect
                  options={options.tipos}
                  value={filtroTipoId}
                  onChange={(val) => handleFiltroTipo(val)}
                  onSearch={(t) => buscadorSelect('tipos', t)}
                  placeholder="Filtrar por tipo"
                />
              </div>
            )}

            {filtroTipoId && subtiposFiltro.length > 0 && (
              <div className="filtros-subtipos">
                <span className="filtros-sublabel">Subtipo:</span>
                <div className='ss-filtro-subtipo'>
                  <SearchableSelect
                    options={options.subtipos}
                    value={filtroSubtipoId}
                    onChange={(id) => handleFiltroSubtipo(id)}
                    onSearch={(t) => buscadorSelect('subtipos', t, {tipo_id: filtroTipoId})}
                    placeholder="Filtrar por subtipo"
                  />
                </div>
              </div>
            )}

            {hayFiltrosActivos && (
              <button className="btn-limpiar-filtros" onClick={limpiarFiltros}>
                ✕ Limpiar filtros
              </button>
            )}
          </div>
        </>
      )}

      {/* ── Tabla ── */}
      {loadingLista ? (
        <p className="empty-msg">Cargando...</p>
      ) : accesorios.length === 0 ? (
        <p className="empty-msg">
          {busqueda ? `Sin resultados para "${busqueda}".` : 'No hay accesorios registrados.'}
        </p>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="acc-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre</th>
                  <th>Precio</th>
                  <th>Tipo</th>
                  <th>Subtipo</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {accesorios.map(acc => (
                  <tr key={acc.accesorio_id} className={!acc.activo ? 'row-inactiva' : ''}>
                    <td>{acc.accesorio_id}</td>
                    <td>{acc.nombre}</td>
                    <td>${acc.precio.toLocaleString()}</td>
                    <td>{acc.tipo_id    ? nombreTipo(acc.tipo_id)       : '—'}</td>
                    <td>{acc.subtipo_id ? nombreSubtipo(acc.subtipo_id) : '—'}</td>
                    <td>
                      <span className={`estado-badge ${acc.activo ? 'activo' : 'inactivo'}`}>
                        {acc.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="acciones-cell">
                      <button className="btn btn-sm btn-secondary" onClick={() => abrirEditar(acc)}>Editar</button>
                      {acc.activo
                        ? <button className="btn btn-sm btn-danger"  onClick={() => handleEliminar(acc)}>Eliminar</button>
                        : <button className="btn btn-sm btn-success" onClick={() => handleActivar(acc)}>Activar</button>
                      }
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
      {modalNuevo && (
        <ModalCrearTipoSubtipo
          modo={modalNuevo}
          tipoId={form.tipo_id}
          tipoNombre={options.tipos.find(t => t.value === form.tipo_id)?.label}
          onConfirm={handleCrearTipoSubtipo}
          onClose={() => setModalNuevo(null)}
        />
      )}
    </div>
  )
}