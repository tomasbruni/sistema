import { useEffect, useCallback } from 'react'
import { api } from '../../api/api'
import useCrudSeccion from '../../hooks/useCrudSeccion'
import SeccionBase from './SeccionBase'

export default function SeccionTipos({ mostrarAlerta }) {
  const fetchFn = useCallback((t) => api.listarTipos({ buscar: t }), [])
  const crud    = useCrudSeccion(fetchFn, { nombre: '' })

  useEffect(() => { crud.fetchItems('') }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (crud.editandoId) {
        await api.actualizarTipo(crud.editandoId, { nombre: crud.form.nombre })
        mostrarAlerta('success', 'Tipo actualizado correctamente.')
      } else {
        await api.crearTipo({ nombre: crud.form.nombre })
      }
      crud.fetchItems(crud.busqueda)
      crud.cancelar()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    }
  }

  const handleEliminar = async (item) => {
    if (!window.confirm(`¿Eliminar el tipo "${item.nombre}"?\nSolo se puede si no tiene accesorios asociados.`)) return

    try {
      await api.eliminarTipo(item.tipo_id)

      mostrarAlerta('success', `Tipo "${item.nombre}" eliminado.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al eliminar: ${err.message}`)
    }
  }

  return (
    <SeccionBase
      titulo="Tipos"
      crud={crud}
      onAbrirEditar={(item) => crud.abrirEditar(item.tipo_id, { nombre: item.nombre })}
      onEliminar={handleEliminar}
      getId={i => i.tipo_id}
      columnas={[{ label: 'Nombre', render: i => i.nombre }]}
    >
      <form onSubmit={handleSubmit} className="acc-form">
        <div className="form-group">
          <label>Nombre *</label>
          <input
            value={crud.form.nombre}
            onChange={e => crud.setForm({ nombre: e.target.value })}
            required
            placeholder="Ej: Fundas"
          />
        </div>
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={crud.cancelar}>Cancelar</button>
          <button type="submit" className="btn btn-primary">
            {crud.editandoId ? 'Guardar cambios' : 'Crear tipo'}
          </button>
        </div>
      </form>
    </SeccionBase>
  )
}
