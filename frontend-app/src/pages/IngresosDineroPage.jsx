import { useState, useEffect } from 'react'
import { api, LIMIT } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import { descargarResponse } from '../helpers/descargar'
import { hoyAR } from '../helpers/fechas'
import InputFecha from '../components/InputFecha/InputFecha'
import './AccesoriosPage.css'
import './MovimientosPage.css'

// `fecha` viene como 'YYYY-MM-DD' (sin hora): se formatea sin pasar por Date para no correr el día.
const formatFecha = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : '—')

const formatMonto = (monto) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', minimumFractionDigits: 2 }).format(monto || 0)

// Fechas siempre en hora argentina (no la del navegador), igual que el backend.
const inicioMesActual = () => `${hoyAR().slice(0, 7)}-01`

const formVacio = () => ({ fecha: hoyAR(), monto: '', descripcion: '' })

const TOTALES_VACIO = { total: 0, cantidad: 0 }

export default function IngresosDineroPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()

  const [ingresos, setIngresos] = useState([])
  const [totales, setTotales] = useState(TOTALES_VACIO)
  const [loading, setLoading] = useState(false)
  const [pagina, setPagina] = useState(0)
  const [hayMas, setHayMas] = useState(false)

  // Por defecto acotamos al mes actual: los totales siempre son de un período, nunca de toda la historia.
  const [fechaDesde, setFechaDesde] = useState(inicioMesActual())
  const [fechaHasta, setFechaHasta] = useState(hoyAR())
  const [descargando, setDescargando] = useState(false)

  const [form, setForm] = useState(formVacio())
  const [editando, setEditando] = useState(null)
  const [guardando, setGuardando] = useState(false)
  const [confirmBorrar, setConfirmBorrar] = useState(null)

  useEffect(() => {
    cargar(0, fechaDesde, fechaHasta)
  }, [])

  const cargar = async (pag, desde, hasta) => {
    setLoading(true)
    try {
      const filtros = { fecha_desde: desde || null, fecha_hasta: hasta || null }
      const [data, tot] = await Promise.all([
        api.listarIngresosDinero({ offset: pag * LIMIT, limit: LIMIT + 1, ...filtros }),
        api.totalesIngresosDinero(filtros),
      ])
      setHayMas(data.length > LIMIT)
      setIngresos(data.slice(0, LIMIT))
      setTotales(tot)
      setPagina(pag)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoading(false)
    }
  }

  const aplicarFiltros = () => cargar(0, fechaDesde, fechaHasta)

  const exportarExcel = async () => {
    if (!fechaDesde || !fechaHasta) {
      mostrarAlerta('warning', 'Elegí el rango de fechas (desde y hasta) para exportar')
      return
    }
    if (fechaDesde > fechaHasta) {
      mostrarAlerta('warning', 'La fecha "desde" no puede ser posterior a "hasta"')
      return
    }
    setDescargando(true)
    try {
      const res = await api.descargarIngresosDineroExcel({ fecha_desde: fechaDesde, fecha_hasta: fechaHasta })
      await descargarResponse(res, `ingresos_dinero_${fechaDesde}_${fechaHasta}.xlsx`)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setDescargando(false)
    }
  }

  const validar = () => {
    if (!form.fecha) return 'Completá la fecha del ingreso'
    if (!(parseFloat(form.monto) > 0)) return 'Ingresá un monto mayor a 0'
    if (!form.descripcion.trim()) return 'Completá la descripción'
    return null
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const error = validar()
    if (error) {
      mostrarAlerta('warning', error)
      return
    }
    setGuardando(true)
    try {
      const payload = { fecha: form.fecha, monto: form.monto, descripcion: form.descripcion.trim() }
      if (editando !== null) {
        await api.actualizarIngresoDinero(editando, payload)
        mostrarAlerta('success', 'Ingreso actualizado')
      } else {
        await api.crearIngresoDinero(payload)
        mostrarAlerta('success', 'Ingreso registrado')
      }
      // Mantenemos la fecha para cargar varios del mismo día seguidos.
      setForm({ ...formVacio(), fecha: form.fecha })
      setEditando(null)
      aplicarFiltros()
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setGuardando(false)
    }
  }

  const iniciarEdicion = (ing) => {
    setEditando(ing.id)
    setForm({ fecha: ing.fecha || '', monto: String(ing.monto ?? ''), descripcion: ing.descripcion || '' })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const cancelarEdicion = () => {
    setEditando(null)
    setForm(formVacio())
  }

  const confirmarBorrar = async (id) => {
    try {
      await api.eliminarIngresoDinero(id)
      mostrarAlerta('success', 'Ingreso eliminado')
      setConfirmBorrar(null)
      aplicarFiltros()
    } catch (e) {
      mostrarAlerta('error', e.message)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Ingresos de dinero</h2>
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.msg}</span>
          <button className="alerta-cerrar" onClick={cerrarAlerta}>&times;</button>
        </div>
      )}

      {/* ── Formulario ── */}
      <div className="form-card">
        <h3>{editando !== null ? 'Editar ingreso' : 'Nuevo ingreso'}</h3>
        <form className="acc-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label>Fecha</label>
              <InputFecha value={form.fecha} onChange={fecha => setForm(f => ({ ...f, fecha }))} />
            </div>
            <div className="form-group">
              <label>Monto ($)</label>
              <input
                type="number" step="0.01" min="0" placeholder="0.00"
                value={form.monto}
                onChange={e => setForm(f => ({ ...f, monto: e.target.value }))}
              />
            </div>
            <div className="form-group" style={{ flex: 2 }}>
              <label>Descripción</label>
              <input
                type="text"
                placeholder="Ej: aporte de socio, reintegro, cobro de alquiler..."
                value={form.descripcion}
                onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button type="submit" className="btn btn-primary" disabled={guardando}>
              {guardando ? 'Guardando...' : editando !== null ? 'Guardar cambios' : 'Registrar'}
            </button>
            {editando !== null && (
              <button type="button" className="btn btn-secondary" onClick={cancelarEdicion}>
                Cancelar
              </button>
            )}
          </div>
        </form>
      </div>

      {/* ── Filtros + exportar ── */}
      <div className="filtros-row" style={{ marginBottom: 12, flexWrap: 'wrap' }}>
        <div className="fecha-inputs">
          <div className="fecha-group">
            <span className="fecha-label">Desde</span>
            <input type="date" className="fecha-input" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} />
          </div>
          <span className="fecha-separador">—</span>
          <div className="fecha-group">
            <span className="fecha-label">Hasta</span>
            <input type="date" className="fecha-input" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} />
          </div>
          <button className="btn btn-secondary" style={{ marginTop: 16 }} onClick={aplicarFiltros}>Filtrar</button>
          <button
            className="btn btn-secondary" style={{ marginTop: 16 }}
            onClick={() => {
              const desde = inicioMesActual(), hasta = hoyAR()
              setFechaDesde(desde); setFechaHasta(hasta)
              cargar(0, desde, hasta)
            }}
          >
            Mes actual
          </button>
          <button className="btn btn-primary" style={{ marginTop: 16 }} disabled={descargando} onClick={exportarExcel}>
            {descargando ? 'Generando...' : 'Exportar Excel'}
          </button>
        </div>
      </div>

      {/* ── Totales (según filtros) ── */}
      <div className="filtros-row" style={{ marginBottom: 12, gap: 16, flexWrap: 'wrap' }}>
        <span className="tipo-badge" style={{ background: '#e6f4ea', color: '#1e7e34' }}>
          Total ingresado: {formatMonto(totales.total)}
        </span>
        <span className="tipo-badge" style={{ background: '#e8e8f0', color: '#1a1a2e' }}>
          {totales.cantidad} ingreso(s)
        </span>
      </div>

      {/* ── Tabla ── */}
      {loading ? (
        <p>Cargando...</p>
      ) : ingresos.length === 0 ? (
        <p style={{ color: '#888' }}>Sin ingresos.</p>
      ) : (
        <div className="table-wrapper">
          <table className="acc-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Fecha</th>
                <th>Monto</th>
                <th>Descripción</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {ingresos.map(ing => (
                <tr key={ing.id}>
                  <td className="mov-id">{ing.id}</td>
                  <td className="mov-fecha">{formatFecha(ing.fecha)}</td>
                  <td className="cantidad-mov">{formatMonto(ing.monto)}</td>
                  <td className="mov-motivo" title={ing.descripcion || ''}>{ing.descripcion || '—'}</td>
                  <td>
                    {confirmBorrar === ing.id ? (
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <button className="btn btn-danger" onClick={() => confirmarBorrar(ing.id)}>Confirmar</button>
                        <button className="btn btn-secondary" onClick={() => setConfirmBorrar(null)}>No</button>
                      </span>
                    ) : (
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <button className="btn btn-secondary" onClick={() => iniciarEdicion(ing)}>Editar</button>
                        <button className="btn btn-danger" onClick={() => setConfirmBorrar(ing.id)}>Borrar</button>
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
        <button className="btn btn-secondary" disabled={pagina === 0} onClick={() => cargar(pagina - 1, fechaDesde, fechaHasta)}>
          Anterior
        </button>
        <span style={{ margin: '0 12px', fontSize: '0.9rem', color: '#555' }}>Pág. {pagina + 1}</span>
        <button className="btn btn-secondary" disabled={!hayMas} onClick={() => cargar(pagina + 1, fechaDesde, fechaHasta)}>
          Siguiente
        </button>
      </div>
    </div>
  )
}
