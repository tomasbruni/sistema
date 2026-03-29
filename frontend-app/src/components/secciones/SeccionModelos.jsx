import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/api'
import useCrudSeccion from '../../hooks/useCrudSeccion'
import useSelectOptions from '../../hooks/useSelectOptions'
import SeccionBase from './SeccionBase'
import SearchableSelect from '../SearchableSelect/SearchableSelect'

export default function SeccionModelos({ mostrarAlerta }) {
  const [filtroActivo, setFiltroActivo] = useState(true)

  const fetchFn = useCallback(
    (t) => api.listarModelos({ buscar: t, activo: filtroActivo }),
    [filtroActivo]
  )
  const crud = useCrudSeccion(fetchFn, { nombre: '', marca_celular_id: null })
  const [todasLasMarcas, setTodasLasMarcas] = useState([])
  const { options, buscadorSelect } = useSelectOptions(['marcasCelulares'])

  useEffect(() => {
    crud.fetchItems('')
    api.listarMarcasCelulares({ limit: 1000 }).then(data => setTodasLasMarcas(data))
  }, [filtroActivo])

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const body = {
        nombre:           crud.form.nombre,
        marca_celular_id: parseInt(crud.form.marca_celular_id),
      }
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
    if (!window.confirm(`¿Desactivar el modelo "${item.nombre}"?`)) return
    try {
      await api.eliminarModelo(item.modelo_celular_id)
      mostrarAlerta('success', `Modelo "${item.nombre}" desactivado.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al eliminar: ${err.message}`)
    }
  }

  const handleActivar = async (item) => {
    if (!window.confirm(`¿Reactivar el modelo "${item.nombre}"?`)) return
    try {
      await api.actualizarModelo(item.modelo_celular_id, { activo: true })
      mostrarAlerta('success', `Modelo "${item.nombre}" reactivado.`)
      crud.fetchItems(crud.busqueda)
    } catch (err) {
      mostrarAlerta('error', `Error al activar: ${err.message}`)
    }
  }

  const nombreMarca = (marca_celular_id) =>
    todasLasMarcas.find(m => m.marca_celular_id === marca_celular_id)?.nombre ?? '—'

  return (
    <SeccionBase
      titulo="Modelos de celular"
      crud={crud}
      onAbrirEditar={(item) => {
        buscadorSelect('marcasCelulares', '')
        crud.abrirEditar(item.modelo_celular_id, {
          nombre:           item.nombre,
          marca_celular_id: item.marca_celular_id,
        })
      }}
      onEliminar={handleEliminar}
      onActivar={handleActivar}
      getId={i => i.modelo_celular_id}
      filtroActivo={filtroActivo}
      setFiltroActivo={setFiltroActivo}
      columnas={[
        { label: 'Marca',  render: i => nombreMarca(i.marca_celular_id) },
        { label: 'Modelo', render: i => i.nombre },
      ]}
    >
      <form onSubmit={handleSubmit} className="acc-form">
        <div className="form-row">
          <div className="form-group">
            <label>Marca *</label>
            <SearchableSelect
              options={options.marcasCelulares}
              value={crud.form.marca_celular_id}
              onChange={crud.setFormField('marca_celular_id')}
              onSearch={(t) => buscadorSelect('marcasCelulares', t)}
              placeholder="Buscar marca..."
            />
          </div>
          <div className="form-group">
            <label>Modelo *</label>
            <input
              value={crud.form.nombre}
              onChange={e => crud.setFormField('nombre')(e.target.value)}
              required
              placeholder="Ej: Galaxy S24"
            />
          </div>
        </div>
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={crud.cancelar}>Cancelar</button>
          <button type="submit" className="btn btn-primary" disabled={!crud.form.marca_celular_id}>
            {crud.editandoId ? 'Guardar cambios' : 'Crear modelo'}
          </button>
        </div>
      </form>
    </SeccionBase>
  )
}