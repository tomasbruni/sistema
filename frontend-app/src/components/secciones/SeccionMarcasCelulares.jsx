import { useEffect, useCallback, useState } from 'react'
import { api } from '../../api/api'
import useCrudSeccion from '../../hooks/useCrudSeccion'
import SeccionBase from './SeccionBase'

export default function SeccionMarcasCelulares({ mostrarAlerta }) {
  const [filtroActivo, setFiltroActivo] = useState(true)

  const fetchFn = useCallback(
    (t) => api.listarMarcasCelulares({ buscar: t, activo: filtroActivo }),
    [filtroActivo]
  )
  const crud = useCrudSeccion(fetchFn, { nombre: '' })

  useEffect(() => { crud.fetchItems('') }, [filtroActivo])

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const body = { nombre: crud.form.nombre }
      if (crud.editandoId) {
        await api.actualizarMarcaCelular(crud.editandoId, body)
        mostrarAlerta('success', 'Marca actualizada correctamente.')
      } else {
        await api.crearMarcaCelular(body)
        mostrarAlerta('success', 'Marca creada correctamente.')
      }
      crud.fetchItems(crud.busqueda)
      crud.cancelar()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    }
  }

  const handleEliminar = async (item) => {
    if (!window.confirm(`¿Desactivar la marca "${item.nombre}"?\nTambién se desactivarán sus modelos asociados.`)) return
    try {
      await api.eliminarMarcaCelular(item.marca_celular_id)
      mostrarAlerta('success', `Marca "${item.nombre}" desactivada.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al eliminar: ${err.message}`)
    }
  }

  const handleActivar = async (item) => {
    if (!window.confirm(`¿Reactivar la marca "${item.nombre}"?`)) return
    try {
      await api.actualizarMarcaCelular(item.marca_celular_id, { activo: true })
      mostrarAlerta('success', `Marca "${item.nombre}" reactivada.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al activar: ${err.message}`)
    }
  }

  return (
    <SeccionBase
      titulo="Marcas de celular"
      crud={crud}
      onAbrirEditar={(item) => crud.abrirEditar(item.marca_celular_id, { nombre: item.nombre })}
      onEliminar={handleEliminar}
      onActivar={handleActivar}
      getId={i => i.marca_celular_id}
      filtroActivo={filtroActivo}
      setFiltroActivo={setFiltroActivo}
      columnas={[
        { label: 'Nombre', render: i => i.nombre },
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
              placeholder="Ej: Samsung"
            />
          </div>
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