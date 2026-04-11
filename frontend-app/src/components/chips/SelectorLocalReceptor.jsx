export default function SelectorLocalReceptor({
  localId,
  setLocalId,
  receptorId,
  setReceptorId,
  observaciones,
  setObservaciones,
  locales = [],
  usuarios = [],
}) {
  return (
    <div className="form-card">
      <div className="form-row">

        <div className="form-group" style={{ maxWidth: 280 }}>
          <label>Local de destino *</label>
          <select
            value={localId ?? ''}
            onChange={e => setLocalId(e.target.value ? parseInt(e.target.value) : null)}
          >
            <option value="">— Seleccioná un local —</option>
            {locales.map(l => (
              <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
            ))}
          </select>
        </div>

        <div className="form-group" style={{ maxWidth: 280 }}>
          <label>Receptor</label>
          <select
            value={receptorId ?? ''}
            onChange={e => setReceptorId(e.target.value ? parseInt(e.target.value) : null)}
          >
            <option value="">— Opcional —</option>
            {usuarios.map(u => (
              <option key={u.usuario_id} value={u.usuario_id}>{u.nombre}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Observaciones</label>
          <input
            type="text"
            placeholder="Opcional"
            value={observaciones}
            onChange={e => setObservaciones(e.target.value)}
          />
        </div>

      </div>
    </div>
  )
}
