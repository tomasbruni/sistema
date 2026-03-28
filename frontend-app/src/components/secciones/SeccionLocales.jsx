import { useEffect, useCallback } from 'react'
import { api } from '../../api/api'
import useCrudSeccion from '../../hooks/useCrudSeccion'
import SeccionBase from './SeccionBase'

export default function SeccionLocales({ mostrarAlerta }) {
  const fetchFn = useCallback(() => api.listarLocales(), [])
  const crud    = useCrudSeccion(fetchFn, { nombre: '', direccion: '', tipo: '' })

  useEffect(() => { crud.fetchItems('') }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const body = { nombre: crud.form.nombre, direccion: crud.form.direccion, tipo: crud.form.tipo }
      if (crud.editandoId) {
        await api.actualizarLocal(crud.editandoId, body)
        mostrarAlerta('success', 'Local actualizado correctamente.')
      } else {
        await api.crearLocal(body)
        mostrarAlerta('success', 'Local creado correctamente.')
      }
      crud.fetchItems(crud.busqueda)
      crud.cancelar()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    }
  }

  const handleEliminar = async (item) => {
    if (!window.confirm(`¿Eliminar el local "${item.nombre}"?`)) return
    try {
      await api.eliminarLocal(item.local_id)
      mostrarAlerta('success', `Local "${item.nombre}" eliminado.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al eliminar: ${err.message}`)
    }
  }

  return (
    <SeccionBase
      titulo="Locales"
      crud={crud}
      onAbrirEditar={(item) => crud.abrirEditar(item.local_id, { nombre: item.nombre, direccion: item.direccion, tipo: item.tipo })}
      onEliminar={handleEliminar}
      getId={i => i.local_id}
      columnas={[
        { label: 'Nombre',    render: i => i.nombre },
        { label: 'Dirección', render: i => i.direccion },
        { label: 'Tipo', render: i => i.tipo },
      ]}
      labelCrear="Nuevo"
    >
      <form onSubmit={handleSubmit} className="acc-form">
        <div className="form-group">
          <label>Nombre *</label>
          <input
            value={crud.form.nombre}
            onChange={e => crud.setForm({ ...crud.form, nombre: e.target.value })}
            required
            placeholder="Ej: Sucursal Centro"
          />
        </div>
        <div className="form-group">
          <label>Dirección *</label>
          <input
            value={crud.form.direccion}
            onChange={e => crud.setForm({ ...crud.form, direccion: e.target.value })}
            required
            placeholder="Ej: Av. Corrientes 1234"
          />
        </div>
        <div className="form-group">
          <label>Tipo *</label>
          <select
            value={crud.form.tipo ?? "LOCAL"}
            onChange={e => crud.setForm({ ...crud.form, tipo: e.target.value })}
          >
            <option value="LOCAL">Local</option>
            <option value="DEPOSITO">Depósito</option>
            <option value="ONLINE">Venta online</option>
          </select>
        </div>
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={crud.cancelar}>Cancelar</button>
          <button type="submit" className="btn btn-primary">
            {crud.editandoId ? 'Guardar cambios' : 'Crear local'}
          </button>
        </div>
      </form>
    </SeccionBase>
  )
}