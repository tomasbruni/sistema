import { useEffect, useCallback, useState } from 'react'
import { api } from '../../api/api'
import useCrudSeccion from '../../hooks/useCrudSeccion'
import SeccionBase from './SeccionBase'
import SearchableSelect from '../SearchableSelect/SearchableSelect'

export default function SeccionSubtipos({ mostrarAlerta }) {
  const [filtroActivo, setFiltroActivo] = useState(true)

  const fetchFn = useCallback(
    (t) => api.listarSubtipos({ buscar: t, activo: filtroActivo }),
    [filtroActivo]
  )
  const crud = useCrudSeccion(fetchFn, { nombre: '', tipo_id: null })

  const [opcionesTipos, setOpcionesTipos] = useState([])
  const [tipos, setTipos]                 = useState([])

  const cargarTipos = async (termino) => {
    const data = await api.listarTipos({ buscar: termino })
    setOpcionesTipos(data.map(t => ({ value: t.tipo_id, label: t.nombre })))
  }

  useEffect(() => {
    crud.fetchItems('')
    api.listarTipos({ buscar: '' })
      .then(data => setTipos(data.map(t => ({ value: t.tipo_id, label: t.nombre }))))
      .catch(() => {})
    cargarTipos('')
  }, [filtroActivo])

  const abrirCrear = () => { crud.abrirCrear(); cargarTipos('') }
  const abrirEditar = (item) => {
    crud.abrirEditar(item.subtipo_id, { nombre: item.nombre, tipo_id: item.tipo_id })
    cargarTipos('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!crud.form.tipo_id) { mostrarAlerta('error', 'Debés seleccionar un tipo.'); return }
    try {
      const body = { nombre: crud.form.nombre, tipo_id: parseInt(crud.form.tipo_id) }
      if (crud.editandoId) {
        await api.actualizarSubtipo(crud.editandoId, body)
        mostrarAlerta('success', 'Subtipo actualizado correctamente.')
      } else {
        await api.crearSubtipo(body)
        mostrarAlerta('success', 'Subtipo creado correctamente.')
      }
      crud.fetchItems(crud.busqueda)
      crud.cancelar()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    }
  }

  const handleEliminar = async (item) => {
    if (!window.confirm(`¿Eliminar el subtipo "${item.nombre}"?\nSolo se puede si no tiene accesorios asociados.`)) return
    try {
      await api.eliminarSubtipo(item.subtipo_id)
      mostrarAlerta('success', `Subtipo "${item.nombre}" eliminado.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al eliminar: ${err.message}`)
    }
  }

  const handleActivar = async (item) => {
    if (!window.confirm(`¿Reactivar el subtipo "${item.nombre}"?`)) return
    try {
      await api.actualizarSubtipo(item.subtipo_id, { activo: true })
      mostrarAlerta('success', `Subtipo "${item.nombre}" reactivado.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al activar: ${err.message}`)
    }
  }

  const nombreTipo = (tipo_id) => tipos.find(t => t.value === tipo_id)?.label ?? `ID ${tipo_id}`

  return (
    <SeccionBase
      titulo="Subtipos"
      crud={crud}
      onAbrirCrear={abrirCrear}
      onAbrirEditar={abrirEditar}
      onEliminar={handleEliminar}
      onActivar={handleActivar}
      getId={i => i.subtipo_id}
      filtroActivo={filtroActivo}
      setFiltroActivo={setFiltroActivo}
      columnas={[
        { label: 'Nombre', render: i => i.nombre },
        { label: 'Tipo',   render: i => <span className="tag-badge">{nombreTipo(i.tipo_id)}</span> },
      ]}
    >
      <form onSubmit={handleSubmit} className="acc-form">
        <div className="form-row">
          <div className="form-group">
            <label>Nombre *</label>
            <input
              value={crud.form.nombre}
              onChange={e => crud.setFormField('nombre')(e.target.value)}
              required
              placeholder="Ej: Rígidas"
            />
          </div>
          <div className="form-group">
            <label>Tipo *</label>
            <SearchableSelect
              options={opcionesTipos}
              value={crud.form.tipo_id}
              onChange={crud.setFormField('tipo_id')}
              onSearch={cargarTipos}
              placeholder="Buscar tipo..."
            />
          </div>
        </div>
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={crud.cancelar}>Cancelar</button>
          <button type="submit" className="btn btn-primary">
            {crud.editandoId ? 'Guardar cambios' : 'Crear subtipo'}
          </button>
        </div>
      </form>
    </SeccionBase>
  )
}