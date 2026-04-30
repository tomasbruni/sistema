import { useState } from 'react'

export default function ModalExportarStock({ onConfirm, onClose, loading }) {
  const [mostrarListado, setMostrarListado] = useState(true)

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,0.45)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 200,
      }}
    >
      <div onClick={e => e.stopPropagation()} style={{ maxWidth: 360, width: '100%', background: '#fff', borderRadius: 8, padding: '24px', boxShadow: '0 8px 32px rgba(0,0,0,0.18)' }}>
        <h3 style={{ marginBottom: 16 }}>Exportar stock</h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
          {[
            { value: true,  label: 'Con listado detallado', desc: 'Incluye una fila por cada accesorio' },
            { value: false, label: 'Solo resumen',          desc: 'Solo encabezado y totales por subtipo' },
          ].map(({ value, label, desc }) => (
            <label
              key={String(value)}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 10,
                padding: '10px 12px', borderRadius: 6, cursor: 'pointer',
                border: `2px solid ${mostrarListado === value ? '#1A1A2E' : '#ddd'}`,
                background: mostrarListado === value ? '#f0f0f8' : '#fff',
              }}
            >
              <input
                type="radio"
                name="mostrar_listado"
                checked={mostrarListado === value}
                onChange={() => setMostrarListado(value)}
                style={{ marginTop: 2 }}
              />
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{label}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{desc}</div>
              </div>
            </label>
          ))}
        </div>

        <div className="form-actions">
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>
            Cancelar
          </button>
          <button className="btn btn-primary" onClick={() => onConfirm(mostrarListado)} disabled={loading}>
            {loading ? 'Exportando...' : '⬇ Descargar'}
          </button>
        </div>
      </div>
    </div>
  )
}
