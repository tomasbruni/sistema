// AgregarProducto.jsx
import SearchableSelect from "../SearchableSelect/SearchableSelect"

export default function AgregarProducto({
  options,
  formItem,
  setFormItem,
  buscadorSelect,
  handleAgregarItem
}) {
  return (
    <div className="form-card">
      <h3>Agregar producto</h3>

      <div className="form-row">

        <div className="form-group" style={{ flex: 2 }}>
          <label>Accesorio *</label>
          <SearchableSelect
            options={options.accesorios}
            value={formItem.accesorio_id}
            onChange={(val) => {
              const found = options.accesorios.find(o => o.value === val)
              setFormItem(prev => ({
                ...prev,
                accesorio_id: val,
                accesorio_data: found?._raw ?? null
              }))
            }}
            onSearch={(t) => buscadorSelect('accesorios', t)}
            placeholder="Buscar por nombre o SKU..."
          />
        </div>

        <div className="form-group" style={{ maxWidth: 100 }}>
          <label>Cantidad *</label>
          <input
            type="number"
            min={1}
            value={formItem.cantidad}
            onChange={e =>
              setFormItem(prev => ({
                ...prev,
                cantidad: e.target.value
              }))
            }
          />
        </div>

        <div className="form-group" style={{ justifyContent: 'flex-end' }}>
          <label>&nbsp;</label>
          <button
            className="btn btn-primary"
            onClick={handleAgregarItem}
          >
            + Agregar
          </button>
        </div>

      </div>
    </div>
  )
}