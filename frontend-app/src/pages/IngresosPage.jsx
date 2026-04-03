import React, { useState, useEffect } from 'react';
import {useAlerta} from '../hooks/useAlerta'
import {LIMIT, api} from '../api/api'
import { formatFecha } from '../helpers/formats'
import { descargarIngresoPdf } from '../helpers/pdf'
import { useModalDetalle } from '../hooks/ventas/useModalDetalles'; 
import ModalIngresoLote from '../components/ingresos/ModalIngresoLote';


function IngresosPage() {
  const { alerta, mostrarAlerta } = useAlerta()
  const [loadingPdf, setLoadingPdf] = useState(null) // ingreso_lote_id en curso

  const descargarPdf = async (ingreso_lote_id) => {
    setLoadingPdf(ingreso_lote_id)
    await descargarIngresoPdf(ingreso_lote_id, (msg) => mostrarAlerta('error', msg))
    setLoadingPdf(null)
  }
  const [ingresos, setIngresos]         = useState([])
  const [loadingLista, setLoadingLista] = useState(false)
  const { modalAbierto, modalItem, loadingModal, abrirModal, cerrarModal } = useModalDetalle(api.getDetalleIngreso)
  const [pagina, setPagina]             = useState(0)
  const [hayMas, setHayMas]             = useState(false)
  const [fechaDesde, setFechaDesde]     = useState('')
  const [fechaHasta, setFechaHasta]     = useState('')
  const [locales, setLocales]           = useState([])
  const [filtroLocalId, setFiltroLocalId] = useState('')

  useEffect(() => {
    fetchIngresos(0)
    api.listarLocales().then(setLocales).catch(() => {})
  }, []) // tira warning porque tiene miedo de usar una version vieja de fetchIngresos

  const fetchIngresos = async (pag, overrides = {}) => {
    setLoadingLista(true)
    const params = {
      skip:        pag * LIMIT,
      limit:       LIMIT + 1,
      local_id:    filtroLocalId || null,
      fecha_desde: fechaDesde || null,
      fecha_hasta: fechaHasta || null,
      ...overrides,
    }
    try {
      const data = await api.listarIngresos(params)
      const items = data.items ?? data
      setHayMas(items.length > LIMIT)
      setIngresos(items.slice(0, LIMIT))
    } catch (err) {
      mostrarAlerta('error', `Error al cargar ingresos: ${err.message}`)
    } finally {
      setLoadingLista(false)
    }
  }

  const irAPagina = (nueva) => { setPagina(nueva); fetchIngresos(nueva) }

  return (
    <div className="page-container">
      {alerta}
      <div className='page-header'>
        <h2>Ingresos</h2>
        {/* Filtros */}
        <div className="form-row" style={{padding: 5}}>
          <div className="form-group" style={{ maxWidth: 200 }}>
            <label>Local</label>
            <select
              className="filtro-select"
              value={filtroLocalId}
              onChange={(e) => {
                setFiltroLocalId(e.target.value)
                fetchIngresos(0, { local_id: e.target.value || null })
                setPagina(0)
              }}
            >
              <option value="">Todos</option>
              {locales.map(l => (
                <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ maxWidth: 200 }}>
            <label>Desde</label>
            <input
              type="date"
              className="filtro-input"
              value={fechaDesde}
              onChange={(e) => {
                setFechaDesde(e.target.value)
                fetchIngresos(0, { fecha_desde: e.target.value || null })
                setPagina(0)
              }}
            />
          </div>
          <div className="form-group" style={{ maxWidth: 200 }}>
            <label>Hasta</label>
            <input
            type="date"
            className="filtro-input"
            value={fechaHasta}
            onChange={(e) => {
              setFechaHasta(e.target.value)
              fetchIngresos(0, { fecha_hasta: e.target.value || null })
              setPagina(0)
            }}
            />
          </div>
        </div>
      </div>

      {/* Tabla */}
      {loadingLista ? (
        <p className="empty-msg">Cargando...</p>
      ) : ingresos.length === 0 ? (
        <p className="empty-msg">No hay ingresos registrados.</p>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="acc-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Fecha</th>
                  <th>Receptor</th>
                  <th>Local</th>
                  <th>Observaciones</th>
                  <th>Detalles</th>
                </tr>
              </thead>
              <tbody>
                {ingresos.map(ing => (
                  <tr key={ing.ingreso_lote_id}>
                    <td>{ing.ingreso_lote_id}</td>
                    <td>{formatFecha(ing.fecha)}</td>
                    <td>{ing.nombre_receptor ?? '—'}</td>
                    <td>{ing.local ?? '—'}</td>
                    <td className="obs-cell">{ing.observaciones ?? '—'}</td>
                    <td style={{ display: 'flex', gap: 6 }}>
                      <button
                        className="btn-ver-detalle"
                        onClick={() => abrirModal(ing.ingreso_lote_id)}
                        disabled={loadingModal}
                      >
                        {loadingModal ? 'Cargando...' : 'Ver detalle'}
                      </button>
                      <button
                        className="btn-ver-detalle"
                        onClick={() => descargarPdf(ing.ingreso_lote_id)}
                        disabled={loadingPdf === ing.ingreso_lote_id}
                      >
                        {loadingPdf === ing.ingreso_lote_id ? 'Generando...' : 'PDF'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="paginacion">
            <button className="btn btn-secondary btn-sm" onClick={() => irAPagina(pagina - 1)} disabled={pagina === 0}>← Anterior</button>
            <span className="pagina-info">Página {pagina + 1}</span>
            <button className="btn btn-secondary btn-sm" onClick={() => irAPagina(pagina + 1)} disabled={!hayMas}>Siguiente →</button>
          </div>
        </>
      )}

      {/* Modal */}
      {modalAbierto && <ModalIngresoLote datos={modalItem} onClose={cerrarModal} />}
    </div>
  )
}

export default IngresosPage;
