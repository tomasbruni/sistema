import { useState, useRef, useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";

export default function NavDropdown({ label, items }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const location = useLocation();

  const isActive = items.some(i => location.pathname === i.to);

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => { setOpen(false) }, [location.pathname]);

  return (
    <li className="nav-dropdown" ref={ref}>
      <button
        className={`nav-dropdown-toggle ${isActive ? "active" : ""}`}
        onClick={() => setOpen(o => !o)}
      >
        {label} <span className="nav-dropdown-arrow">&#9662;</span>
      </button>
      {open && (
        <ul className="nav-dropdown-menu">
          {items.map(i => (
            <li key={i.to}>
              <NavLink to={i.to}>{i.label}</NavLink>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
