import { useEffect, useRef, useState } from 'react'

/**
 * Modal para crear un Tipo o un Subtipo de accesorio.
 *
 * Props:
 *   modo         — 'tipo' | 'subtipo'
 *   tipoId       — id del tipo preseleccionado (solo para modo 'subtipo')
 *   tipoNombre   — nombre del tipo preseleccionado (solo para modo 'subtipo')
 *   onConfirm    — fn({ nombre, tipo_id? }) => Promise  (llamado al guardar)
 *   onClose      — fn()
 */
export default function ModalCrearTipoSubtipo({ modo, tipoId, tipoNombre, onConfirm, onClose }) {
  const [nombre, setNombre]     = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const inputRef                = useRef(null)
  const backdropRef             = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const handleSubmit = async (e) => {
    e.preventDefault()
    const nombreTrim = nombre.trim()
    if (!nombreTrim) return
    setLoading(true)
    setError('')
    try {
      await onConfirm(modo === 'tipo'
        ? { nombre: nombreTrim }
        : { nombre: nombreTrim, tipo_id: tipoId }
      )
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="modal-backdrop"
      ref={backdropRef}
      onClick={(e) => e.target === backdropRef.current && onClose()}
    >
      <div className="modal-panel" style={{ maxWidth: 360 }}>
        <div className="modal-header">
          <h2>{modo === 'tipo' ? 'Nuevo tipo' : 'Nuevo subtipo'}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {modo === 'subtipo' && (
              <div className="form-group">
                <label>Tipo</label>
                <input value={tipoNombre ?? ''} disabled />
              </div>
            )}
            <div className="form-group">
              <label>{modo === 'tipo' ? 'Nombre del tipo *' : 'Nombre del subtipo *'}</label>
              <input
                ref={inputRef}
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder={modo === 'tipo' ? 'Ej: Funda' : 'Ej: Antigolpe'}
                required
              />
            </div>
            {error && <p style={{ color: 'var(--color-danger, #c00)', margin: 0, fontSize: 13 }}>{error}</p>}
          </div>

          <div className="modal-footer" style={{ justifyContent: 'flex-end', gap: 8 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || !nombre.trim()}>
              {loading ? 'Guardando...' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
