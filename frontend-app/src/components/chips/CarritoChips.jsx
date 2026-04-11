export default function CarritoChips({
  carrito = [],
  onEliminar,
  onConfirmar,
  loading,
}) {
  if (carrito.length === 0) return null

  return (
    <div className="form-card">
      <h3>Chips a ingresar</h3>

      <div className="table-wrapper">
        <table className="acc-table">
          <thead>
            <tr>
              <th>N° de serie</th>
              <th>Compañía</th>
              <th>Precio</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {carrito.map(chip => (
              <tr key={chip._key}>
                <td><span className="sku-badge">{chip.numero_serie}</span></td>
                <td>{chip.compania}</td>
                <td>${chip.precio.toLocaleString()}</td>
                <td>
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={() => onEliminar(chip._key)}
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="venta-total">
        <span>Total a ingresar:</span>
        <strong>{carrito.length} chips</strong>
      </div>

      <div className="form-actions" style={{ marginTop: 16 }}>
        <button
          className="btn btn-primary"
          onClick={onConfirmar}
          disabled={loading}
        >
          {loading ? 'Procesando...' : 'Confirmar ingreso y descargar remito'}
        </button>
      </div>
    </div>
  )
}
