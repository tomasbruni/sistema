import { useEffect, useRef } from "react"

function ModalIngresoLote({ datos, onClose }) {
  const backdropRef = useRef(null)

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose?.()
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  if (!datos) return null

  const { ingreso_lote_id, fecha, nombre_receptor, movimientos = [] } = datos

  const totalUnidades = movimientos.reduce((s, m) => s + m.cantidad, 0)

  const fechaFmt = fecha
    ? new Intl.DateTimeFormat("es-AR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(fecha))
    : "—"

  return (
    <div
      className="modal-backdrop"
      ref={backdropRef}
      onClick={(e) => e.target === backdropRef.current && onClose?.()}
    >
      <div className="modal-panel">

        {/* Header */}
        <div className="modal-header">
          <h2>Ingreso de lote #{ingreso_lote_id}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {/* Meta */}
        <div className="modal-body">
          <div style={{ display: "flex", gap: "2rem", marginBottom: "1rem", fontSize: "0.9rem", color: "var(--text-muted, #888)" }}>
            <span><strong>Fecha:</strong> {fechaFmt}</span>
            <span><strong>Receptor:</strong> {nombre_receptor ?? "—"}</span>
          </div>

          {/* Movimientos */}
          <p className="modal-section-title">Artículos ingresados</p>
          <table className="modal-table">
            <thead>
              <tr>
                <th>Accesorio</th>
                <th className="num">Cantidad</th>
              </tr>
            </thead>
            <tbody>
              {movimientos.map((m, i) => (
                <tr key={i}>
                  <td>{m.nombre_accesorio}</td>
                  <td className="num">+{m.cantidad}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <span className="modal-footer-label">Total unidades</span>
          <span className="modal-footer-total">{totalUnidades}</span>
        </div>

      </div>
    </div>
  )
}

export default ModalIngresoLote