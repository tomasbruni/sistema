import { useState } from 'react'
import './AccesoriosPage.css'
import SearchableSelect from '../components/SearchableSelect/SearchableSelect'
import { api } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import useSelectOptions from '../hooks/useSelectOptions'
import useListaFiltrada from '../hooks/useListaFiltrada'

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
    refetch,
    nombreTipo, nombreSubtipo,
  } = useListaFiltrada((p) => api.listarAccesorios(p), { conCatalogos: true })

  const [loadingExport, setLoadingExport] = useState(false)
  const [form, setForm]                   = useState(formVacio)
  const [editandoId, setEditandoId]       = useState(null)
  const [mostrarForm, setMostrarForm]     = useState(false)
  const [loading, setLoading]             = useState(false)

  const { options, setOption, buscadorSelect } =
    useSelectOptions(['tipos', 'subtipos', 'marcas', 'marcasCelulares', 'modelos'])

  // ── Exportar ─────────────────────────────────────────────────────────────
  const handleExportar = async () => {
    setLoadingExport(true)
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
      setLoadingExport(false)
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
    setLoading(true)

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
        const res = await api.verificarDuplicado(body)

        if (res?.tiene_duplicados) {
          const lineas = res.duplicados.map(d => {
            const etiqueta = d.es_mismo_precio ? '🔴 Duplicado exacto' : '🟡 Similar'
            return `  ${etiqueta}: "${d.nombre}" — SKU: ${d.sku} — $${d.precio.toLocaleString()}`
          }).join('\n')

          const encabezado = res.es_duplicado_exacto
            ? '🔴 Ya existe un accesorio con el mismo nombre Y precio:'
            : '🟡 Ya existen accesorios con nombre similar (distinto precio):'

          const confirmar = window.confirm(
            `${encabezado}\n\n${lineas}\n\n¿Querés crearlo de todas formas?`
          )
          if (!confirmar) { setLoading(false); return }
        }

        await api.crearAccesorio(body)
        mostrarAlerta('success', 'Accesorio creado correctamente.')
        refetch()
        cancelar()
      }
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoading(false)
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
          <button className="btn btn-primary" onClick={abrirCrear}>
            + Nuevo accesorio
          </button>
        )}
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.msg}</span>
          <button className="alerta-cerrar" onClick={cerrarAlerta}>✕</button>
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
                <input name="nombre" value={form.nombre} onChange={handleChange} required placeholder="Ej: Funda iPhone 15" />
              </div>
              <div className="form-group">
                <label>Precio *</label>
                <input name="precio" type="number" value={form.precio} onChange={handleChange} required min={0} placeholder="Ej: 2500" />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Tipo *</label>
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
              <div className="form-group">
                <label>Subtipo</label>
                <SearchableSelect
                  options={options.subtipos}
                  value={form.subtipo_id}
                  onChange={setFormField('subtipo_id')}
                  onSearch={(t) => buscadorSelect('subtipos', t, { tipo_id: form.tipo_id })}
                  placeholder="Buscar subtipo..."
                  disabled={!form.tipo_id}
                />
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
              <button type="button" className="btn btn-secondary" onClick={cancelar} disabled={loading}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Guardando...' : editandoId ? 'Guardar cambios' : 'Crear accesorio'}
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
              placeholder="Buscar por nombre o SKU..."
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
                  <th>SKU</th>
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
                    <td><span className="sku-badge">{acc.sku}</span></td>
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
    </div>
  )
}