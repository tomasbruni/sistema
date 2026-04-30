import { NavLink } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import NavDropdown from "./NavDropdown";

export default function Navbar() {
  const { nombre, rol, logout } = useAuth();

  return (
    <nav className="navbar">
      <ul className="navbar-links">
        <li><NavLink to="/ventas">Ventas</NavLink></li>
        <li><NavLink to="/reparaciones">Reparaciones</NavLink></li>
        <li><NavLink to="/stock">Stock</NavLink></li>
        {rol !== 'admin' && <li><NavLink to="/transferencias">Transferencias</NavLink></li>}
        {rol === 'admin' && (
          <>
            <NavDropdown label="Mov. de stock" items={[
              { to: "/ingresos", label: "Ingresos" },
              { to: "/ingresos-chips", label: "Ingresos chips" },
              { to: "/transferencias", label: "Transferencias" },
              { to: "/movimientos", label: "Movimientos" },
            ]} />
            <NavDropdown label="Productos" items={[
              { to: "/accesorios", label: "Accesorios" },
              { to: "/chips", label: "Chips" },
              { to: "/celulares", label: "Celulares" },
              { to: "/importar-excel", label: "Importar Excel" },
            ]} />
            <NavDropdown label="Finanzas" items={[
              { to: "/reportes", label: "Reportes" },
              { to: "/finanzas", label: "Finanzas" },
            ]} />
            <li><NavLink to="/adicionales">Archivos maestros</NavLink></li>
            {/* <li><NavLink to="/pedidos-online">Pedidos Online</NavLink></li> */}
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
