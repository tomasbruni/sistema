import { useEffect, useRef } from "react"

function ModalIngresoLote({ datos, onClose }) {
  const backdropRef = useRef(null)

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose?.()
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  if (!datos) return null

  const { ingreso_lote_id, fecha, nombre_receptor, local, movimientos = [] } = datos

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
          <h2>Ingreso #{ingreso_lote_id}</h2>
          <div>
            <p><strong>Fecha:</strong> {fechaFmt}</p>
            <p><strong>Receptor:</strong> {nombre_receptor ?? "—"}</p>
            <p><strong>Local:</strong> {local ?? "—"}</p>
          </div>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {/* Meta */}
        <div className="modal-body">
          {/* Movimientos */}
          <table className="modal-table">
            <thead>
              <tr>
                <th>Producto</th>
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