import { NavLink } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

export default function Navbar() {
  const { nombre, rol, logout } = useAuth()

  return (
    <nav className="navbar">
      <ul className="navbar-links">
        <li><NavLink to="/ventas">Ventas</NavLink></li>
        <li><NavLink to="/stock">Stock</NavLink></li>
        <li><NavLink to="/transferencias">Transferencias</NavLink></li>
        {rol === 'admin' && (
          <>
            <li><NavLink to="/ingresos">Ingresos</NavLink></li>
            <li><NavLink to="/accesorios">Accesorios</NavLink></li>
            <li><NavLink to="/adicionales">Adicionales</NavLink></li>
            <li><NavLink to="/movimientos">Movimientos</NavLink></li>
            <li><NavLink to="/chips">Chips</NavLink></li>
            <li><NavLink to="/celulares">Celulares</NavLink></li>
            <li><NavLink to="/reportes">Reportes</NavLink></li>
          </>
        )}
      </ul>
      <div className="navbar-usuario">
        <span className="navbar-nombre">{nombre}</span>
        <button className="navbar-logout" onClick={logout}>Salir</button>
      </div>
    </nav>
  );
}