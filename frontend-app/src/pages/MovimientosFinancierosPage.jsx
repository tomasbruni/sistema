import { useState, useEffect } from 'react'
import { api, LIMIT } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import './AccesoriosPage.css'
import './MovimientosPage.css'

const formatFecha = (fechaStr) => {
  if (!fechaStr) return '—'
  return new Date(fechaStr).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

const formatMonto = (monto) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 }).format(monto)

const FORM_VACIO = { tipo: 'INGRESO', monto: '', descripcion: '' }

export default function MovimientosFinancierosPage() {
  const { alerta, mostrarAlerta } = useAlerta()

  const [movimientos, setMovimientos] = useState([])
  const [loading, setLoading] = useState(false)
  const [pagina, setPagina] = useState(0)
  const [hayMas, setHayMas] = useState(false)

  const [filtroTipo, setFiltroTipo] = useState(null)
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')

  const [form, setForm] = useState(FORM_VACIO)
  const [editando, setEditando] = useState(null) // id del movimiento en edición
  const [guardando, setGuardando] = useState(false)
  const [confirmBorrar, setConfirmBorrar] = useState(null)

  useEffect(() => {
    cargar(0, filtroTipo, fechaDesde, fechaHasta)
  }, [])

  const cargar = async (pag, tipo, desde, hasta) => {
    setLoading(true)
    try {
      const data = await api.listarMovimientosFinancieros({
        offset: pag * LIMIT,
        limit: LIMIT + 1,
        tipo: tipo || null,
        fecha_desde: desde || null,
        fecha_hasta: hasta || null,
      })
      setHayMas(data.length > LIMIT)
      setMovimientos(data.slice(0, LIMIT))
      setPagina(pag)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoading(false)
    }
  }

  const aplicarFiltros = () => cargar(0, filtroTipo, fechaDesde, fechaHasta)

  const handleFiltroTipo = (tipo) => {
    const nuevo = filtroTipo === tipo ? null : tipo
    setFiltroTipo(nuevo)
    cargar(0, nuevo, fechaDesde, fechaHasta)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.monto || !form.descripcion.trim()) {
      mostrarAlerta('warning', 'Completá todos los campos')
      return
    }
    setGuardando(true)
    try {
      if (editando !== null) {
        await api.actualizarMovimientoFinanciero(editando, {
          tipo: form.tipo,
          monto: parseInt(form.monto),
          descripcion: form.descripcion.trim(),
        })
        mostrarAlerta('success', 'Movimiento actualizado')
      } else {
        await api.crearMovimientoFinanciero({
          tipo: form.tipo,
          monto: parseInt(form.monto),
          descripcion: form.descripcion.trim(),
        })
        mostrarAlerta('success', 'Movimiento registrado')
      }
      setForm(FORM_VACIO)
      setEditando(null)
      cargar(0, filtroTipo, fechaDesde, fechaHasta)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setGuardando(false)
    }
  }

  const iniciarEdicion = (mov) => {
    setEditando(mov.id)
    setForm({ tipo: mov.tipo, monto: String(mov.monto), descripcion: mov.descripcion })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const cancelarEdicion = () => {
    setEditando(null)
    setForm(FORM_VACIO)
  }

  const confirmarBorrar = async (id) => {
    try {
      await api.eliminarMovimientoFinanciero(id)
      mostrarAlerta('success', 'Movimiento eliminado')
      setConfirmBorrar(null)
      cargar(0, filtroTipo, fechaDesde, fechaHasta)
    } catch (e) {
      mostrarAlerta('error', e.message)
    }
  }

  const totalIngresosVisible = movimientos
    .filter(m => m.tipo === 'INGRESO')
    .reduce((acc, m) => acc + m.monto, 0)

  const totalEgresosVisible = movimientos
    .filter(m => m.tipo === 'EGRESO')
    .reduce((acc, m) => acc + m.monto, 0)

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Movimientos Financieros</h2>
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.mensaje}</span>
        </div>
      )}

      {/* ── Formulario ── */}
      <div className="form-card">
        <h3>{editando !== null ? 'Editar movimiento' : 'Nuevo movimiento'}</h3>
        <form className="acc-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label>Tipo</label>
              <select value={form.tipo} onChange={e => setForm(f => ({ ...f, tipo: e.target.value }))}>
                <option value="INGRESO">Ingreso</option>
                <option value="EGRESO">Egreso</option>
              </select>
            </div>
            <div className="form-group">
              <label>Monto ($)</label>
              <input
                type="number"
                min="1"
                placeholder="0"
                value={form.monto}
                onChange={e => setForm(f => ({ ...f, monto: e.target.value }))}
              />
            </div>
          </div>
          <div className="form-group">
            <label>Descripcion</label>
            <input
              type="text"
              placeholder="Ej: alquiler, pago proveedor, venta externa..."
              value={form.descripcion}
              onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))}
            />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="submit" className="btn-primary" disabled={guardando}>
              {guardando ? 'Guardando...' : editando !== null ? 'Guardar cambios' : 'Registrar'}
            </button>
            {editando !== null && (
              <button type="button" className="btn-secondary" onClick={cancelarEdicion}>
                Cancelar
              </button>
            )}
          </div>
        </form>
      </div>

      {/* ── Filtros ── */}
      <div className="filtros-row" style={{ marginBottom: 12 }}>
        {['INGRESO', 'EGRESO'].map(t => (
          <button
            key={t}
            className={`filtro-chip ${filtroTipo === t ? 'filtro-chip-activo' : ''} ${t === 'INGRESO' ? 'filtro-chip-mov-entrada' : 'filtro-chip-mov-salida'}`}
            onClick={() => handleFiltroTipo(t)}
          >
            {t === 'INGRESO' ? 'Ingresos' : 'Egresos'}
          </button>
        ))}
        <div className="fecha-inputs">
          <div className="fecha-group">
            <span className="fecha-label">Desde</span>
            <input
              type="date"
              className="fecha-input"
              value={fechaDesde}
              onChange={e => setFechaDesde(e.target.value)}
            />
          </div>
          <span className="fecha-separador">—</span>
          <div className="fecha-group">
            <span className="fecha-label">Hasta</span>
            <input
              type="date"
              className="fecha-input"
              value={fechaHasta}
              onChange={e => setFechaHasta(e.target.value)}
            />
          </div>
          <button className="btn-secondary" style={{ marginTop: 16 }} onClick={aplicarFiltros}>
            Filtrar
          </button>
          {(fechaDesde || fechaHasta || filtroTipo) && (
            <button
              className="btn-secondary"
              style={{ marginTop: 16 }}
              onClick={() => {
                setFechaDesde('')
                setFechaHasta('')
                setFiltroTipo(null)
                cargar(0, null, '', '')
              }}
            >
              Limpiar
            </button>
          )}
        </div>
      </div>

      {/* ── Totales de la página ── */}
      {movimientos.length > 0 && (
        <div className="filtros-row" style={{ marginBottom: 12, gap: 16 }}>
          <span className="tipo-badge tipo-entrada">
            Ingresos: {formatMonto(totalIngresosVisible)}
          </span>
          <span className="tipo-badge tipo-salida">
            Egresos: {formatMonto(totalEgresosVisible)}
          </span>
          <span className="tipo-badge" style={{ background: '#e8e8f0', color: '#1a1a2e' }}>
            Neto: {formatMonto(totalIngresosVisible - totalEgresosVisible)}
          </span>
        </div>
      )}

      {/* ── Tabla ── */}
      {loading ? (
        <p>Cargando...</p>
      ) : movimientos.length === 0 ? (
        <p style={{ color: '#888' }}>Sin movimientos.</p>
      ) : (
        <div className="table-wrapper">
        <table className="acc-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Tipo</th>
              <th>Monto</th>
              <th>Descripcion</th>
              <th>Fecha</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {movimientos.map(mov => (
              <tr
                key={mov.id}
                className={mov.tipo === 'INGRESO' ? 'mov-row-entrada' : 'mov-row-salida'}
              >
                <td className="mov-id">{mov.id}</td>
                <td>
                  <span className={`tipo-badge ${mov.tipo === 'INGRESO' ? 'tipo-entrada' : 'tipo-salida'}`}>
                    {mov.tipo === 'INGRESO' ? 'Ingreso' : 'Egreso'}
                  </span>
                </td>
                <td className={`cantidad-mov ${mov.tipo === 'INGRESO' ? 'cantidad-positiva' : 'cantidad-negativa'}`}>
                  {formatMonto(mov.monto)}
                </td>
                <td className="mov-motivo" title={mov.descripcion}>{mov.descripcion}</td>
                <td className="mov-fecha">{formatFecha(mov.fecha)}</td>
                <td>
                  {confirmBorrar === mov.id ? (
                    <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <button className="btn-danger" onClick={() => confirmarBorrar(mov.id)}>Confirmar</button>
                      <button className="btn-secondary" onClick={() => setConfirmBorrar(null)}>No</button>
                    </span>
                  ) : (
                    <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <button className="btn-secondary" onClick={() => iniciarEdicion(mov)}>Editar</button>
                      <button className="btn-danger" onClick={() => setConfirmBorrar(mov.id)}>Borrar</button>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}

      {/* ── Paginación ── */}
      <div className="paginacion" style={{ marginTop: 16 }}>
        <button className="btn-secondary" disabled={pagina === 0} onClick={() => cargar(pagina - 1, filtroTipo, fechaDesde, fechaHasta)}>
          Anterior
        </button>
        <span style={{ margin: '0 12px', fontSize: '0.9rem', color: '#555' }}>Pág. {pagina + 1}</span>
        <button className="btn-secondary" disabled={!hayMas} onClick={() => cargar(pagina + 1, filtroTipo, fechaDesde, fechaHasta)}>
          Siguiente
        </button>
      </div>
    </div>
  )
}
