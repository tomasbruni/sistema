import { useEffect, useRef, useState } from "react"
import { api } from "../../api/api"
import { formatPrecio } from "../../helpers/formats"
import "./ModalDetalle.css"

const MEDIOS_ELECTRONICOS = ["TRANSFERENCIA", "DEBITO", "CREDITO"]

// Arma el estado inicial del formulario a partir de los pagos actuales.
// Los importes de una devolución vienen negativos: se trabaja con el valor absoluto.
const estadoInicial = (pagos = []) => {
  const efectivo    = pagos.find((p) => p.medio_de_pago === "EFECTIVO")
  const electronico = pagos.find((p) => p.medio_de_pago !== "EFECTIVO")
  const medio = efectivo && electronico ? "ambos" : electronico ? "electronico" : "efectivo"
  return {
    medioPago: medio,
    medioPagoElectronico: MEDIOS_ELECTRONICOS.includes(electronico?.medio_de_pago) ? electronico.medio_de_pago : null,
    cuotas: electronico?.cuotas || 1,
    montoEfectivo: medio === "ambos" ? String(Math.abs(efectivo.importe)) : "",
    montoElectronico: medio === "ambos" ? String(Math.abs(electronico.importe)) : "",
  }
}

// Representación comparable de una lista de pagos: importe absoluto (las
// devoluciones vienen negativas), cuotas solo para electrónicos (sin dato = 1)
// y orden estable, para detectar si la edición realmente cambia algo.
const normalizarPagos = (pagos) =>
  JSON.stringify(
    pagos
      .map((p) => ({
        medio: p.medio_de_pago,
        importe: Math.abs(p.importe),
        cuotas: p.medio_de_pago === "EFECTIVO" ? null : Number(p.cuotas || 1),
      }))
      .sort((a, b) => a.medio.localeCompare(b.medio) || a.importe - b.importe)
  )

function ModalEditarPagos({ venta, onClose, onGuardado }) {
  const backdropRef = useRef(null)
  const inicial = estadoInicial(venta.pagos)

  const [medioPago, setMedioPago]                       = useState(inicial.medioPago) // 'efectivo' | 'electronico' | 'ambos'
  const [medioPagoElectronico, setMedioPagoElectronico] = useState(inicial.medioPagoElectronico)
  const [cuotas, setCuotas]                             = useState(inicial.cuotas)
  const [montoEfectivo, setMontoEfectivo]               = useState(inicial.montoEfectivo)
  const [montoElectronico, setMontoElectronico]         = useState(inicial.montoElectronico)
  const [error, setError]                               = useState(null)
  const [guardando, setGuardando]                       = useState(false)

  const total = Math.abs(venta.monto_total)

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose?.()
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  const handleGuardar = async () => {
    setError(null)

    if (medioPago !== "efectivo" && !medioPagoElectronico) {
      setError("Seleccioná un medio de pago electrónico.")
      return
    }
    if (medioPago !== "efectivo" && medioPagoElectronico !== "CREDITO" && Number(cuotas) > 1) {
      setError("Las cuotas solo aplican a pagos con tarjeta de crédito.")
      return
    }

    // Construir pagos (mismo criterio que al crear la venta)
    let pagos = []
    if (medioPago === "efectivo") {
      pagos = [{ medio_de_pago: "EFECTIVO", importe: total }]
    } else if (medioPago === "electronico") {
      pagos = [{ medio_de_pago: medioPagoElectronico, importe: total, cuotas: Number(cuotas) }]
    } else {
      const ef = parseInt(montoEfectivo)    || 0
      const el = parseInt(montoElectronico) || 0
      if (ef + el !== total) {
        setError(`La suma de los pagos (${formatPrecio(ef + el)}) no coincide con el total (${formatPrecio(total)}).`)
        return
      }
      if (ef > 0) pagos.push({ medio_de_pago: "EFECTIVO", importe: ef })
      if (el > 0) pagos.push({ medio_de_pago: medioPagoElectronico, importe: el, cuotas: Number(cuotas) })
    }

    // Sin cambios: se cierra sin llamar al backend (evita reescribir los pagos)
    if (normalizarPagos(pagos) === normalizarPagos(venta.pagos)) {
      onClose?.()
      return
    }

    setGuardando(true)
    try {
      await api.actualizarPagosVenta(venta.venta_id, pagos)
      onGuardado?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setGuardando(false)
    }
  }

  const selectMedioElectronico = (
    <div className="form-group" style={{ maxWidth: 200 }}>
      <label>Forma de pago</label>
      <select value={medioPagoElectronico ?? ""} onChange={(e) => setMedioPagoElectronico(e.target.value)}>
        <option value="" disabled>Seleccionar...</option>
        <option value="TRANSFERENCIA">Transferencia</option>
        <option value="DEBITO">Débito</option>
        <option value="CREDITO">Crédito</option>
      </select>
    </div>
  )

  const selectCuotas = (
    <div className="form-group" style={{ maxWidth: 200 }}>
      <label>Cuotas</label>
      <select value={cuotas} onChange={(e) => setCuotas(Number(e.target.value))}>
        <option value={1}>1</option>
        <option value={3}>3</option>
        <option value={6}>6</option>
        <option value={12}>12</option>
      </select>
    </div>
  )

  return (
    <div
      className="modal-backdrop"
      ref={backdropRef}
      onClick={(e) => e.target === backdropRef.current && onClose?.()}
    >
      <div className="modal-panel">

        {/* Header */}
        <div className="modal-header">
          <h2>Editar pago de {venta.tipo === "DEVOLUCION" ? "devolución" : "venta"} #{venta.venta_id}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {/* Body */}
        <div className="modal-body">
          <div>
            <p className="modal-section-title">Pago actual</p>
            {venta.pagos.map((p, i) => (
              <span key={i} className="pago-badge">
                {p.medio_de_pago}: {formatPrecio(p.importe)}
              </span>
            ))}
          </div>

          <div>
            <p className="modal-section-title">Nuevo pago</p>
            <div className="form-row">
              <div className="form-group" style={{ maxWidth: 200 }}>
                <label>Medio</label>
                <select value={medioPago} onChange={(e) => setMedioPago(e.target.value)}>
                  <option value="efectivo">Efectivo</option>
                  <option value="electronico">Electrónico</option>
                  <option value="ambos">Ambos</option>
                </select>
              </div>

              {medioPago === "electronico" && (
                <>
                  {selectMedioElectronico}
                  {selectCuotas}
                </>
              )}
            </div>

            {medioPago === "ambos" && (
              <>
                <div className="form-row">
                  <div className="form-group">
                    <label>Monto efectivo</label>
                    <input
                      type="number"
                      min={0}
                      value={montoEfectivo}
                      onChange={(e) => setMontoEfectivo(e.target.value)}
                      placeholder="$"
                    />
                  </div>
                  <div className="form-group">
                    <label>Monto electrónico</label>
                    <input
                      type="number"
                      min={0}
                      value={montoElectronico}
                      onChange={(e) => setMontoElectronico(e.target.value)}
                      placeholder="$"
                    />
                  </div>
                </div>
                <div className="form-row">
                  {selectMedioElectronico}
                  {selectCuotas}
                </div>
                {(() => {
                  const suma = (parseInt(montoEfectivo) || 0) + (parseInt(montoElectronico) || 0)
                  const ok = suma === total
                  return (
                    <p className={`venta-pago-hint ${ok ? "hint-ok" : "hint-error"}`}>
                      Suma de pagos: {formatPrecio(suma)} / Total: {formatPrecio(total)}
                      {ok ? " ✓" : " — no coincide"}
                    </p>
                  )
                })()}
              </>
            )}

            {error && <p className="venta-pago-hint hint-error">{error}</p>}
          </div>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <span className="modal-footer-label">Total {formatPrecio(total)}</span>
          <div>
            <button className="btn btn-secondary btn-sm" onClick={onClose} disabled={guardando}>Cancelar</button>{" "}
            <button className="btn btn-primary btn-sm" onClick={handleGuardar} disabled={guardando}>
              {guardando ? "Guardando..." : "Guardar"}
            </button>
          </div>
        </div>

      </div>
    </div>
  )
}

export default ModalEditarPagos
