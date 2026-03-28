import { useEffect, useCallback } from 'react'
import { api } from '../../api/api'
import useCrudSeccion from '../../hooks/useCrudSeccion'
import SeccionBase from './SeccionBase'

export default function SeccionModelos({ mostrarAlerta }) {
  const fetchFn = useCallback((t) => api.listarModelos({ buscar: t }), [])
  const crud    = useCrudSeccion(fetchFn, { marca: '', modelo: '' })

  useEffect(() => { crud.fetchItems('') }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const body = { marca: crud.form.marca, modelo: crud.form.modelo }
    if (crud.editandoId) {
      await api.actualizarModelo(crud.editandoId, body)
      mostrarAlerta('success', 'Modelo actualizado correctamente.')
    } else {
      await api.crearModelo(body)
      mostrarAlerta('success', 'Modelo creado correctamente.')
    }
      crud.fetchItems(crud.busqueda)
      crud.cancelar()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    }
  }

  const handleEliminar = async (item) => {
    if (!window.confirm(`¿Eliminar el modelo "${item.marca} ${item.modelo}"?`)) return

    try {
      await api.eliminarModelo(item.modelo_id)

      mostrarAlerta('success', `Modelo "${item.marca} ${item.modelo}" eliminado.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al eliminar: ${err.message}`)
    }
  }

  return (
    <SeccionBase
      titulo="Modelos"
      crud={crud}
      onAbrirEditar={(item) => crud.abrirEditar(item.modelo_id, { marca: item.marca, modelo: item.modelo })}
      onEliminar={handleEliminar}
      getId={i => i.modelo_id}
      columnas={[
        { label: 'Marca',  render: i => i.marca },
        { label: 'Modelo', render: i => i.modelo },
      ]}
    >
      <form onSubmit={handleSubmit} className="acc-form">
        <div className="form-row">
          <div className="form-group">
            <label>Marca *</label>
            <input
              value={crud.form.marca}
              onChange={e => crud.setFormField('marca')(e.target.value)}
              required
              placeholder="Ej: Samsung"
            />
          </div>
          <div className="form-group">
            <label>Modelo *</label>
            <input
              value={crud.form.modelo}
              onChange={e => crud.setFormField('modelo')(e.target.value)}
              required
              placeholder="Ej: Galaxy S24"
            />
          </div>
        </div>
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={crud.cancelar}>Cancelar</button>
          <button type="submit" className="btn btn-primary">
            {crud.editandoId ? 'Guardar cambios' : 'Crear modelo'}
          </button>
        </div>
      </form>
    </SeccionBase>
  )
}
