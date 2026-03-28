import { useEffect, useCallback } from 'react'
import { api } from '../../api/api'
import useCrudSeccion from '../../hooks/useCrudSeccion'
import SeccionBase from './SeccionBase'

const TIPOS_PRODUCTO = ['ACCESORIO', 'CELULAR', 'CHIP']
const TIPOS_CALCULO  = ['PORCENTAJE', 'FIJO']

const EMPTY_FORM = { tipo_producto: '', tipo_calculo: '', valor: '' }

export default function SeccionComisiones({ mostrarAlerta }) {
  const fetchFn = useCallback(() => api.listarComisiones(), [])

  const crud = useCrudSeccion(fetchFn, EMPTY_FORM)

  useEffect(() => { crud.fetchItems('') }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const body = {
        tipo_calculo: crud.form.tipo_calculo,
        valor: Number(crud.form.valor),
        ...(!crud.editandoId && { tipo_producto: crud.form.tipo_producto }),
      }
      
    if (crud.editandoId) {
      await api.actualizarComision(crud.editandoId, body)
      mostrarAlerta('success', 'Comisión actualizada correctamente.')
    } else {
      await api.crearComision(body)
      mostrarAlerta('success', 'Comisión creada correctamente.')
    }

      crud.fetchItems('')
      crud.cancelar()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    }
  }

  const handleEliminar = async (item) => {
    if (!window.confirm(`¿Eliminar la comisión para "${item.tipo_producto}"?`)) return
    try {
      await fetch(`http://localhost:8000/comisiones/${item.config_comision_id}`, { method: 'DELETE' })
        .then(r => { if (!r.ok) throw new Error(`Error ${r.status}`); return r.json() })
      mostrarAlerta('success', `Comisión para "${item.tipo_producto}" eliminada.`)
      crud.fetchItems('')
    } catch (err) {
      mostrarAlerta('error', `Error al eliminar: ${err.message}`)
    }
  }

  return (
    <SeccionBase
      titulo="Comisiones"
      crud={crud}
      onAbrirEditar={(item) =>
        crud.abrirEditar(item.config_comision_id, {
          tipo_producto: item.tipo_producto,
          tipo_calculo:  item.tipo_calculo,
          valor:         String(item.valor),
        })
      }
      onEliminar={handleEliminar}
      getId={i => i.config_comision_id}
      columnas={[
        { label: 'Tipo de producto', render: i => i.tipo_producto },
        { label: 'Tipo de cálculo',  render: i => i.tipo_calculo },
        {
          label: 'Valor',
          render: i =>
            i.tipo_calculo === 'PORCENTAJE' ? `${i.valor}%` : `$${i.valor}`,
        },
      ]}
      labelCrear="Nueva"
    >
      <form onSubmit={handleSubmit} className="acc-form">

        {/* Tipo de producto — solo al crear */}
        {!crud.editandoId && (
          <div className="form-group">
            <label>Tipo de producto *</label>
            <select
              value={crud.form.tipo_producto}
              onChange={e => crud.setFormField('tipo_producto')(e.target.value)}
              required
            >
              <option value="">Seleccionar...</option>
              {TIPOS_PRODUCTO.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        )}

        {/* Tipo de cálculo */}
        <div className="form-group">
          <label>Tipo de cálculo *</label>
          <select
            value={crud.form.tipo_calculo}
            onChange={e => crud.setFormField('tipo_calculo')(e.target.value)}
            required
          >
            <option value="">Seleccionar...</option>
            {TIPOS_CALCULO.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        {/* Valor */}
        <div className="form-group">
          <label>
            Valor *
            {crud.form.tipo_calculo === 'PORCENTAJE' && ' (%)'}
            {crud.form.tipo_calculo === 'FIJO'       && ' ($)'}
          </label>
          <input
            type="number"
            min="0"
            value={crud.form.valor}
            onChange={e => crud.setFormField('valor')(e.target.value)}
            required
            placeholder={crud.form.tipo_calculo === 'PORCENTAJE' ? 'Ej: 3' : 'Ej: 500'}
          />
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={crud.cancelar}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary">
            Guardar cambios
          </button>
        </div>
      </form>
    </SeccionBase>
  )
}