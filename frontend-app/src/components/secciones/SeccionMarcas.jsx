import { useEffect, useCallback, useState } from 'react'
import { api } from '../../api/api'
import useCrudSeccion from '../../hooks/useCrudSeccion'
import SeccionBase from './SeccionBase'

export default function SeccionMarcas({ mostrarAlerta }) {
  const [filtroActivo, setFiltroActivo] = useState(true)

  const fetchFn = useCallback(
    (t) => api.listarMarcas({ buscar: t, activo: filtroActivo }),
    [filtroActivo]
  )
  const crud = useCrudSeccion(fetchFn, { nombre: '' })

  useEffect(() => { crud.fetchItems('') }, [filtroActivo])

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const body = { nombre: crud.form.nombre }
      if (crud.editandoId) {
        await api.actualizarMarca(crud.editandoId, body)
        mostrarAlerta('success', 'Marca actualizada correctamente.')
      } else {
        await api.crearMarca(body)
        mostrarAlerta('success', 'Marca creada correctamente.')
      }
      crud.fetchItems(crud.busqueda)
      crud.cancelar()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    }
  }

  const handleEliminar = async (item) => {
    if (!window.confirm(`¿Eliminar la marca "${item.nombre}"?`)) return
    try {
      await api.eliminarMarca(item.marca_id)
      mostrarAlerta('success', `Marca "${item.nombre}" eliminada.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al eliminar: ${err.message}`)
    }
  }

  const handleActivar = async (item) => {
    if (!window.confirm(`¿Reactivar la marca "${item.nombre}"?`)) return
    try {
      await api.actualizarMarca(item.marca_id, { activo: true })
      mostrarAlerta('success', `Marca "${item.nombre}" reactivada.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al activar: ${err.message}`)
    }
  }

  return (
    <SeccionBase
      titulo="Marcas"
      crud={crud}
      onAbrirEditar={(item) => crud.abrirEditar(item.marca_id, { nombre: item.nombre })}
      onEliminar={handleEliminar}
      onActivar={handleActivar}
      getId={i => i.marca_id}
      filtroActivo={filtroActivo}
      setFiltroActivo={setFiltroActivo}
      columnas={[{ label: 'Nombre', render: i => i.nombre }]}
      labelCrear='Nueva'
    >
      <form onSubmit={handleSubmit} className="acc-form">
        <div className="form-group">
          <label>Nombre *</label>
          <input
            value={crud.form.nombre}
            onChange={e => crud.setFormField('nombre')(e.target.value)}
            required
            placeholder="Ej: Noga"
          />
        </div>
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={crud.cancelar}>Cancelar</button>
          <button type="submit" className="btn btn-primary">
            {crud.editandoId ? 'Guardar cambios' : 'Crear marca'}
          </button>
        </div>
      </form>
    </SeccionBase>
  )
}