import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { useAuth } from './hooks/useAuth'
import Layout from './components/layout/Layout'
import AuthPage from './pages/AuthPage'
import AccesoriosPage from './pages/AccesoriosPage'
import StockPage from './pages/StockPage'
import AdicionalesPage from './pages/AdicionalesPage'
import MovimientosPage from './pages/MovimientosPage'
import VentasPage from './pages/VentasPage'
import CelularesPage from './pages/CelularesPage'
import ChipsPage from './pages/ChipsPage'
import ReportesPage from './pages/ReportesPage'
import IngresosPage from './pages/IngresosPage'
import IngresosChipsPage from './pages/IngresosChipsPage'
import TransferenciasPage from './pages/TransferenciasPage'
import PedidosOnlinePage from './pages/PedidosOnlinePage'
import ReparacionesPage from './pages/ReparacionesPage'
import ImportarExcelPage from './pages/ImportarExcelPage'
import GastosPage from './pages/GastosPage'

function RutaPrivada({ children }) {
  const { token } = useAuth()

  return token ? children : <Navigate to="/login" replace />
}

function RutaAdmin({ children }) {
  const { token, rol } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  if (rol !== 'admin') return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        <Route path="/" element={<RutaPrivada><Layout /></RutaPrivada>}>
          <Route index element={<Navigate to="ventas" replace />} />
          <Route path="ventas" element={<VentasPage />} />
          <Route path="stock"         element={<StockPage />} />
          <Route path="transferencias" element={<TransferenciasPage />} />
          <Route path="ingresos"  element={<RutaAdmin><IngresosPage /></RutaAdmin>} />
          <Route path="ingresos-chips" element={<RutaAdmin><IngresosChipsPage /></RutaAdmin>} />
          <Route path="accesorios"  element={<RutaAdmin><AccesoriosPage /></RutaAdmin>} />
          <Route path="adicionales" element={<RutaAdmin><AdicionalesPage /></RutaAdmin>} />
          <Route path="movimientos" element={<RutaAdmin><MovimientosPage /></RutaAdmin>} />
          <Route path="chips"       element={<RutaAdmin><ChipsPage /></RutaAdmin>} />
          <Route path="celulares"   element={<RutaAdmin><CelularesPage /></RutaAdmin>} />
          <Route path="reportes"    element={<RutaAdmin><ReportesPage /></RutaAdmin>} />
          {/* <Route path="pedidos-online" element={<RutaAdmin><PedidosOnlinePage /></RutaAdmin>} /> */}
          <Route path="gastos" element={<RutaAdmin><GastosPage /></RutaAdmin>} />
          <Route path="reparaciones" element={<ReparacionesPage />} />
          <Route path="importar-excel" element={<RutaAdmin><ImportarExcelPage /></RutaAdmin>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}