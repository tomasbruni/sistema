// CarritoProductos.jsx

export default function CarritoProductos({
  carrito = [],
  titulo,
  onConfirmar,
  loading,
  disabled,
  textoBoton,
  classBoton = "btn btn-primary",
  handleCantidadCarrito,
  handleEliminarDelCarrito
}) {
  if (carrito.length === 0) return null

  return (
    <div className="form-card">
      <h3>{titulo}</h3>

      <div className="table-wrapper">
        <table className="acc-table">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Producto</th>
              <th>Cantidad</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            {carrito.map(item => (
              <tr key={item._key}>
                <td><span className="sku-badge">{item.sku}</span></td>
                <td>{item.nombre}</td>

                <td>
                  <input
                    className="input-carrito"
                    type="number"
                    min={1}
                    value={item.cantidad}
                    onChange={e =>
                      handleCantidadCarrito(item._key, e.target.value)
                    }
                  />
                </td>

                <td>
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={() => handleEliminarDelCarrito(item._key)}
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
        <span>Total de líneas: {carrito.length}</span>
        <strong>
          {carrito.reduce((s, c) => s + c.cantidad, 0)} unidades
        </strong>
      </div>

      <div className="form-actions" style={{ marginTop: 16 }}>
        <button
          className={classBoton}
          onClick={onConfirmar}
          disabled={loading || disabled}
        >
          {loading ? "Procesando..." : textoBoton}
        </button>
      </div>
    </div>
  )
}