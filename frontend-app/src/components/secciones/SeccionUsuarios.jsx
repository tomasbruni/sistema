import { useEffect, useCallback, useState } from 'react'
import { api } from '../../api/api'
import useCrudSeccion from '../../hooks/useCrudSeccion'
import SeccionBase from './SeccionBase'

export default function SeccionUsuarios({ mostrarAlerta }) {
  const [filtroActivo, setFiltroActivo] = useState(true)

  const fetchFn = useCallback(
    () => api.listarUsuarios({ activo: filtroActivo }),
    [filtroActivo]
  )
  const crud = useCrudSeccion(fetchFn, { nombre: '', password: '', rol: 'usuario' })

  useEffect(() => { crud.fetchItems('') }, [filtroActivo])

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (crud.editandoId) {
        const body = { nombre: crud.form.nombre }
        await api.actualizarUsuario(crud.editandoId, body)
        mostrarAlerta('success', 'Usuario actualizado correctamente.')
      } else {
        await api.crearUsuario({ nombre: crud.form.nombre, password: crud.form.password, rol: crud.form.rol })
        mostrarAlerta('success', 'Usuario creado correctamente.')
      }
      crud.fetchItems(crud.busqueda)
      crud.cancelar()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    }
  }

  const handleEliminar = async (item) => {
    if (!window.confirm(`¿Desactivar el usuario "${item.nombre}"?`)) return
    try {
      await api.desactivarUsuario(item.usuario_id)
      mostrarAlerta('success', `Usuario "${item.nombre}" desactivado.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al desactivar: ${err.message}`)
    }
  }

  const handleActivar = async (item) => {
    if (!window.confirm(`¿Reactivar el usuario "${item.nombre}"?`)) return
    try {
      await api.actualizarUsuario(item.usuario_id, { activo: true })
      mostrarAlerta('success', `Usuario "${item.nombre}" reactivado.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al reactivar: ${err.message}`)
    }
  }

  return (
    <SeccionBase
      titulo="Usuarios"
      crud={crud}
      onAbrirEditar={(item) => crud.abrirEditar(item.usuario_id, { nombre: item.nombre, password: '', rol: item.rol })}
      onEliminar={handleEliminar}
      onActivar={handleActivar}
      getId={i => i.usuario_id}
      filtroActivo={filtroActivo}
      setFiltroActivo={setFiltroActivo}
      columnas={[
        { label: 'Nombre', render: i => i.nombre },
        { label: 'Rol',    render: i => i.rol },
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
            placeholder="Nombre de usuario"
          />
        </div>
        {!crud.editandoId && (
          <>
            <div className="form-group">
              <label>Contraseña *</label>
              <input
                type="password"
                value={crud.form.password}
                onChange={e => crud.setForm({ ...crud.form, password: e.target.value })}
                required
                placeholder="Contraseña"
              />
            </div>
            <div className="form-group">
              <label>Rol *</label>
              <select
                value={crud.form.rol}
                onChange={e => crud.setForm({ ...crud.form, rol: e.target.value })}
              >
                <option value="usuario">Usuario</option>
                <option value="admin">Administrador</option>
              </select>
            </div>
          </>
        )}
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={crud.cancelar}>Cancelar</button>
          <button type="submit" className="btn btn-primary">
            {crud.editandoId ? 'Guardar cambios' : 'Crear usuario'}
          </button>
        </div>
      </form>
    </SeccionBase>
  )
}
