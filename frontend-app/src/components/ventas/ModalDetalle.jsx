import { useEffect, useRef } from "react"
import "./ModalDetalle.css"

const fmt = (n) =>
  new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0,
  }).format(n)

function ModalDetalle({ detalles, admin, onClose }) {
  const backdropRef = useRef(null)

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose?.()
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  if (!detalles) return null

  const { venta_id, accesorios = [], celulares = [], chips = [] } = detalles

  const total = [
    ...accesorios.map((a) => a.precio_unitario * a.cantidad),
    ...celulares.map((c) => c.precio_unitario),
    ...chips.map((c) => c.precio_unitario),
  ].reduce((s, v) => s + v, 0)

  return (
    <div
      className="modal-backdrop"
      ref={backdropRef}
      onClick={(e) => e.target === backdropRef.current && onClose?.()}
    >
      <div className="modal-panel">

        {/* Header */}
        <div className="modal-header">
          <h2>Detalle de venta #{venta_id}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {/* Body */}
        <div className="modal-body">

          {/* Accesorios */}
          {accesorios.length > 0 && (
            <div>
              <p className="modal-section-title">Accesorios</p>
              <table className="modal-table">
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th className="num">P. Lista</th>
                    <th className="num">P. Unitario</th>
                    <th className="num">Cant.</th>
                    {admin && <th className="num">Comisión</th>}
                  </tr>
                </thead>
                <tbody>
                  {accesorios.map((a, i) => (
                    <tr key={i}>
                      <td>{a.nombre}</td>
                      <td className="num">{fmt(a.precio_lista)}</td>
                      <td className={`num ${a.precio_unitario !== a.precio_lista ? "descuento" : ""}`}>
                        {fmt(a.precio_unitario)}
                      </td>
                      <td className="num">×{a.cantidad}</td>
                      {admin && <td className="num">{fmt(a.comision_importe)}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Celulares */}
          {celulares.length > 0 && (
            <div>
              <p className="modal-section-title">Celulares</p>
              <table className="modal-table">
                <thead>
                  <tr>
                    <th>Marca y modelo</th>
                    <th>IMEI</th>
                    <th className="num">P. Lista</th>
                    <th className="num">P. Unitario</th>
                    {admin && <th className="num">Comisión</th>}
                  </tr>
                </thead>
                <tbody>
                  {celulares.map((c, i) => (
                    <tr key={i}>
                      <td>{c.marca} {c.modelo}</td>
                      <td>{c.imei}</td>
                      <td className="num">{fmt(c.precio_lista)}</td>
                      <td className={`num ${c.precio_unitario !== c.precio_lista ? "descuento" : ""}`}>
                        {fmt(c.precio_unitario)}
                      </td>
                      {admin && <td className="num">{fmt(c.comision_importe)}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Chips */}
          {chips.length > 0 && (
            <div>
              <p className="modal-section-title">Chips</p>
              <table className="modal-table">
                <thead>
                  <tr>
                    <th>Compañía</th>
                    <th>N° Serie</th>
                    <th className="num">P. Lista</th>
                    <th className="num">P. Unitario</th>
                    {admin && <th className="num">Comisión</th>}
                  </tr>
                </thead>
                <tbody>
                  {chips.map((ch, i) => (
                    <tr key={i}>
                      <td>{ch.compania}</td>
                      <td>{ch.numero_serie}</td>
                      <td className="num">{fmt(ch.precio_lista)}</td>
                      <td className={`num ${ch.precio_unitario !== ch.precio_lista ? "descuento" : ""}`}>
                        {fmt(ch.precio_unitario)}
                      </td>
                      {admin && <td className="num">{fmt(ch.comision_importe)}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="modal-footer">
          <span className="modal-footer-label">Total</span>
          <span className="modal-footer-total">{fmt(total)}</span>
        </div>

      </div>
    </div>
  )
}

export default ModalDetalle