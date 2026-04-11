import { useEffect, useRef } from "react"

function ModalIngresoLoteChips({ datos, onClose }) {
  const backdropRef = useRef(null)

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose?.()
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  if (!datos) return null

  const { ingreso_lote_chip_id, fecha, nombre_receptor, local, observaciones, chips = [] } = datos

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
          <h2>Ingreso de chips #{ingreso_lote_chip_id}</h2>
          <div>
            <p><strong>Fecha:</strong> {fechaFmt}</p>
            <p><strong>Receptor:</strong> {nombre_receptor ?? "—"}</p>
            <p><strong>Local:</strong> {local ?? "—"}</p>
            {observaciones && <p><strong>Observaciones:</strong> {observaciones}</p>}
          </div>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {/* Chips */}
        <div className="modal-body">
          <table className="modal-table">
            <thead>
              <tr>
                <th>N° de serie</th>
                <th>Compañía</th>
                <th className="num">Precio</th>
              </tr>
            </thead>
            <tbody>
              {chips.map((c, i) => (
                <tr key={i}>
                  <td>{c.numero_serie}</td>
                  <td>{c.compania}</td>
                  <td className="num">${c.precio.toLocaleString("es-AR")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <span className="modal-footer-label">Total chips</span>
          <span className="modal-footer-total">{chips.length}</span>
        </div>

      </div>
    </div>
  )
}

export default ModalIngresoLoteChips
