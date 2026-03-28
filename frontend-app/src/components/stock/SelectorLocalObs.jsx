export default function SelectorLocalObs({
  // modo ingreso
  localId,
  setLocalId,

  // modo transferencia
  localOrigenId,
  setLocalOrigenId,
  localDestinoId,
  setLocalDestinoId,

  // opcional receptor
  receptorId = null,
  setReceptorId = null,
  usuarios = [],

  // comunes
  observaciones,
  setObservaciones,
  locales = [],

  // flags
  mode = 'ingreso', // 'ingreso' | 'transferencia'
  showReceptor = false
}) {
  return (
    <div className="form-card">
      <div className="form-row">

        {/* ── INGRESO ── */}
        {mode === 'ingreso' && (
          <div className="form-group" style={{ maxWidth: 280 }}>
            <label>Local de destino *</label>
            <select
              value={localId ?? ''}
              onChange={e =>
                setLocalId(e.target.value ? parseInt(e.target.value) : null)
              }
            >
              <option value="">— Seleccioná un local —</option>
              {locales.map(l => (
                <option key={l.local_id} value={l.local_id}>
                  {l.nombre}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* ── TRANSFERENCIA ── */}
        {mode === 'transferencia' && (
          <>
            <div className="form-group">
              <label>Local de origen *</label>
              <select
                value={localOrigenId ?? ''}
                onChange={e =>
                  setLocalOrigenId(e.target.value ? parseInt(e.target.value) : null)
                }
              >
                <option value="">— Seleccioná —</option>
                {locales.map(l => (
                  <option key={l.local_id} value={l.local_id}>
                    {l.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Local de destino *</label>
              <select
                value={localDestinoId ?? ''}
                onChange={e =>
                  setLocalDestinoId(e.target.value ? parseInt(e.target.value) : null)
                }
              >
                <option value="">— Seleccioná —</option>
                {locales
                  .filter(l => l.local_id !== localOrigenId)
                  .map(l => (
                    <option key={l.local_id} value={l.local_id}>
                      {l.nombre}
                    </option>
                  ))}
              </select>
            </div>
          </>
        )}

        {/* ── RECEPTOR (opcional) ── */}
        {showReceptor && (
          <div className="form-group" style={{ maxWidth: 280 }}>
            <label>Receptor *</label>
            <select
              value={receptorId ?? ''}
              onChange={e =>
                setReceptorId(e.target.value ? parseInt(e.target.value) : null)
              }
            >
              <option value="">— Seleccioná un receptor —</option>
              {usuarios.map(u => (
                <option key={u.usuario_id} value={u.usuario_id}>
                  {u.nombre}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* ── OBSERVACIONES ── */}
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