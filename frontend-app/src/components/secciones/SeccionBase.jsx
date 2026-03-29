export default function SeccionBase({
  titulo, crud,
  onAbrirCrear, onAbrirEditar, onEliminar, onActivar,
  columnas, getId,
  labelCrear = 'Nuevo',
  filtroActivo, setFiltroActivo,
  children,
}) {
  const handleCrear = onAbrirCrear ?? crud.abrirCrear

  let tituloBase = null
  if (titulo !== "Locales") {
    tituloBase = titulo.endsWith('s') ? titulo.slice(0, -1) : titulo
  } else {
    tituloBase = "Local"
  }

  return (
    <>
      <div className="seccion-header">
        <h3 className="seccion-titulo">{titulo}</h3>
        {!crud.mostrarForm && labelCrear !== null && (
          <button className="btn btn-primary" onClick={handleCrear}>{labelCrear}</button>
        )}
      </div>

      {crud.mostrarForm && (
        <div className="form-card">
          <h3>{crud.editandoId ? `Editar ${titulo.toLowerCase()}` : `${labelCrear} ${tituloBase.toLowerCase()}`}</h3>
          {children}
        </div>
      )}

      {!crud.mostrarForm && (
        <>
          <div className="lista-toolbar">
            <input
              className="buscador"
              type="search"
              placeholder={`Buscar ${titulo.toLowerCase()}...`}
              value={crud.busqueda}
              onChange={crud.handleBusqueda}
            />
          </div>

          {/* Filtro activo/inactivo — solo si la sección lo soporta */}
          {filtroActivo !== undefined && (
            <div className="filtros-panel">
              <div className="filtros-row">
                <span className="filtros-sublabel">Estado:</span>
                <div className="filtros-chips">
                  {[{ valor: true, label: 'Activos' }, { valor: false, label: 'Inactivos' }].map(({ valor, label }) => (
                    <button
                      key={label}
                      className={`filtro-chip filtro-chip-estado ${filtroActivo === valor ? 'filtro-chip-activo' : ''}`}
                      onClick={() => setFiltroActivo(valor)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {crud.loading ? (
        <p className="empty-msg">Cargando...</p>
      ) : crud.items.length === 0 ? (
        <p className="empty-msg">
          {crud.busqueda
            ? `Sin resultados para "${crud.busqueda}".`
            : `No hay ${titulo.toLowerCase()} registrados.`}
        </p>
      ) : (
        <div className="table-wrapper">
          <table className="acc-table">
            <thead>
              <tr>
                {columnas.map(c => <th key={c.label}>{c.label}</th>)}
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {crud.items.map(item => (
                <tr key={getId(item)} className={item.activo === false ? 'row-inactiva' : ''}>
                  {columnas.map(c => <td key={c.label}>{c.render(item)}</td>)}
                  <td className="acciones-cell">
                    <button className="btn btn-sm btn-secondary" onClick={() => onAbrirEditar(item)}>Editar</button>
                    {item.activo === false && onActivar
                      ? <button className="btn btn-sm btn-success" onClick={() => onActivar(item)}>Activar</button>
                      : <button className="btn btn-sm btn-danger"  onClick={() => onEliminar(item)}>Eliminar</button>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}