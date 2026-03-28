import { NavLink, Outlet } from 'react-router-dom'
import Navbar from './Navbar.jsx'

export default function Layout() {

  return (
    <div className="layout">
        <div className="layout-main">
          <header>
            <Navbar></Navbar>
          </header>
          <main className="layout-content">
            <Outlet />
          </main>
        </div>
    </div>
  )
}