import { useState } from 'react'

const formVacio = { compania: '', numero_serie: '', precio: '' }

export default function FormularioAgregarChip({ onAgregar }) {
  const [form, setForm] = useState(formVacio)

  const handleChange = e => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = e => {
    e.preventDefault()
    if (!form.compania.trim() || !form.numero_serie.trim() || !form.precio) return
    onAgregar({
      compania:     form.compania.trim(),
      numero_serie: form.numero_serie.trim(),
      precio:       Number(form.precio),
    })
    setForm(formVacio)
  }

  return (
    <div className="form-card">
      <h3>Agregar chip al lote</h3>
      <form onSubmit={handleSubmit}>
        <div className="form-row">

          <div className="form-group">
            <label>Compañía *</label>
            <input
              name="compania"
              value={form.compania}
              onChange={handleChange}
              placeholder="Ej: Claro, Personal, Movistar"
              required
            />
          </div>

          <div className="form-group">
            <label>N° de serie *</label>
            <input
              name="numero_serie"
              value={form.numero_serie}
              onChange={handleChange}
              placeholder="Ej: 8954010123456789"
              required
            />
          </div>

          <div className="form-group" style={{ maxWidth: 140 }}>
            <label>Precio *</label>
            <input
              name="precio"
              type="number"
              min={0}
              value={form.precio}
              onChange={handleChange}
              placeholder="Ej: 1500"
              required
            />
          </div>

          <div className="form-group" style={{ justifyContent: 'flex-end' }}>
            <label>&nbsp;</label>
            <button type="submit" className="btn btn-primary">+ Agregar</button>
          </div>

        </div>
      </form>
    </div>
  )
}
