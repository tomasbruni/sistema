import { useEffect, useRef } from "react"

function ModalTransferencia({ datos, onClose }) {
  const backdropRef = useRef(null)

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose?.()
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  if (!datos) return null

  const { transferencia_id, fecha, nombre_usuario, local_origen, local_destino, observaciones, items = [] } = datos

  const totalUnidades = items.reduce((s, i) => s + i.cantidad, 0)

  const fechaFmt = fecha
    ? new Intl.DateTimeFormat("es-AR", {
        day: "2-digit", month: "2-digit", year: "numeric",
        hour: "2-digit", minute: "2-digit",
      }).format(new Date(fecha))
    : "—"

  return (
    <div
      className="modal-backdrop"
      ref={backdropRef}
      onClick={(e) => e.target === backdropRef.current && onClose?.()}
    >
      <div className="modal-panel">

        <div className="modal-header">
          <h2>Transferencia #{transferencia_id}</h2>
          <div>
            <p><strong>Fecha:</strong> {fechaFmt}</p>
            <p><strong>Emisor:</strong> {nombre_usuario ?? "—"}</p>
            <p><strong>Origen:</strong> {local_origen ?? "—"}</p>
            <p><strong>Destino:</strong> {local_destino ?? "—"}</p>
            {observaciones && <p><strong>Observaciones:</strong> {observaciones}</p>}
          </div>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <table className="modal-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Producto</th>
                <th className="num">Cantidad</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i}>
                  <td>{item.accesorio_id}</td>
                  <td>{item.nombre}</td>
                  <td className="num">{item.cantidad}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="modal-footer">
          <span className="modal-footer-label">Total unidades</span>
          <span className="modal-footer-total">{totalUnidades}</span>
        </div>

      </div>
    </div>
  )
}

export default ModalTransferencia
