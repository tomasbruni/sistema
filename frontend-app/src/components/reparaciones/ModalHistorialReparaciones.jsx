import { useEffect, useRef } from 'react'
import '../ventas/ModalDetalle.css'
import { formatFecha, formatFechaCorta, formatPrecio } from '../../helpers/formats'

function ModalHistorialReparaciones({ reparacion, historial, nombreUsuario, onClose }) {
  const backdropRef = useRef(null)

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!reparacion) return null

  return (
    <div
      className="modal-backdrop"
      ref={backdropRef}
      onClick={(e) => e.target === backdropRef.current && onClose?.()}
    >
      <div className="modal-panel" style={{ maxWidth: '720px' }}>

        <div className="modal-header">
          <h2>Historial — #{reparacion.reparacion_id} {reparacion.celular}</h2>
          <p>{reparacion.nombre_cliente}</p>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {historial.length === 0 ? (
            <p style={{ margin: 0, color: '#666' }}>Sin movimientos registrados.</p>
          ) : (
            <table className="modal-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Tipo</th>
                  <th>Estado anterior</th>
                  <th>Estado nuevo</th>
                  <th className="num">Monto anterior</th>
                  <th className="num">Monto nuevo</th>
                  <th className="num">Entrega recibida</th>
                  <th>Usuario</th>
                  <th>Observaciones</th>
                </tr>
              </thead>
              <tbody>
                {historial.map((mov) => (
                  <tr key={mov.id}>
                    <td>{formatFechaCorta(mov.fecha)}</td>
                    <td>{mov.tipo_movimiento}</td>
                    <td>{mov.estado_anterior ?? '-'}</td>
                    <td>{mov.estado_nuevo ?? '-'}</td>
                    <td className="num">{mov.monto_anterior != null ? formatPrecio(mov.monto_anterior) : '-'}</td>
                    <td className="num">{mov.monto_nuevo != null ? formatPrecio(mov.monto_nuevo) : '-'}</td>
                    <td className="num">{mov.monto_entrega_recibido != null ? formatPrecio(mov.monto_entrega_recibido) : '-'}</td>
                    <td>{nombreUsuario(mov.usuario_id)}</td>
                    <td>{mov.observaciones ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

      </div>
    </div>
  )
}

export default ModalHistorialReparaciones
