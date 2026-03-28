// ─── COMPONENTE GENÉRICO DE SECCIÓN ──────────────────────────────────────────
// Encapsula: header + buscador + form card + tabla
// Props:
//   titulo        → string
//   crud          → objeto retornado por useCrudSeccion
//   onAbrirCrear  → fn opcional (si no se pasa, usa crud.abrirCrear)
//   onAbrirEditar → fn(item)
//   onEliminar    → fn(item)
//   columnas      → [{ label, render: (item) => ReactNode }]
//   getId         → fn(item) => key
//   labelCrear    → string | null  (null oculta el botón de crear)
//   children      → contenido del formulario
export default function SeccionBase({
  titulo, crud,
  onAbrirCrear, onAbrirEditar, onEliminar,
  columnas, getId,
  labelCrear = 'Nuevo',
  children,
}) {
  const handleCrear = onAbrirCrear ?? crud.abrirCrear
  let tituloBase = null;
  if (titulo !== "Locales"){
    tituloBase = titulo.endsWith('s') ? titulo.slice(0, -1) : titulo;
  }
  else {
    tituloBase = "Local";
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
        <div className="lista-toolbar">
          <input
            className="buscador"
            type="search"
            placeholder={`Buscar ${titulo.toLowerCase()}...`}
            value={crud.busqueda}
            onChange={crud.handleBusqueda}
          />
        </div>
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
                <tr key={getId(item)}>
                  {columnas.map(c => <td key={c.label}>{c.render(item)}</td>)}
                  <td className="acciones-cell">
                    <button className="btn btn-sm btn-secondary" onClick={() => onAbrirEditar(item)}>Editar</button>
                    <button className="btn btn-sm btn-danger"    onClick={() => onEliminar(item)}>Eliminar</button>
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
