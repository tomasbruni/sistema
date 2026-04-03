
import { useState } from 'react'
import './StockPage.css'
import { api } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import useListaFiltrada from '../hooks/useListaFiltrada'
import useSelectOptions from '../hooks/useSelectOptions'
import SearchableSelect from '../components/SearchableSelect/SearchableSelect'
import SelectorLocalObs from '../components/stock/SelectorLocalObs.jsx'
import AgregarProducto from '../components/stock/AgregarProducto.jsx'
import CarritoProductos from '../components/stock/CarritoProductos.jsx'
import { useAuth } from '../hooks/useAuth.jsx'
import { descargarIngresoPdf, descargarTransferenciaPdf } from '../helpers/pdf'
// ─── MODO DE VISTA ────────────────────────────────────────────────────────────
// 'lista'        → tabla de stock con acciones de ajuste/egreso
// 'ingreso'      → carrito de ingreso por lote
// 'transferencia'→ carrito de transferencia por lote
 
// ─── FORM VACÍO PARA ÍTEM DEL CARRITO ────────────────────────────────────────
const itemVacio = { accesorio_id: null, accesorio_data: null, cantidad: 1 }
 
// ─── COMPONENTE PRINCIPAL ────────────────────────────────────────────────────
export default function StockPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()
 
  // ── Lista + filtros ───────────────────────────────────────────────────────
  const {
    items: stock, loadingLista,
    pagina, hayMas, irAPagina,
    busqueda, handleBusqueda,
    filtroTipoId, filtroSubtipoId, filtroLocalId, filtroActivo,
    handleFiltroTipo, handleFiltroSubtipo, handleFiltroLocal, handleFiltroActivo,
    tiposFiltro, subtiposFiltro, locales, usuarios,
    limpiarFiltros, hayFiltrosActivos, refetch,
  } = useListaFiltrada((p) => api.listarStock(p), { conLocales: true, conUsuarios: true })
 
  // ── Modo actual ───────────────────────────────────────────────────────────
  const [modo, setModo] = useState('lista')
 
  // ── Acciones sobre ítem de la tabla (ajuste / egreso) ─────────────────────
  const [accion, setAccion]                     = useState(null) // 'ajustar' | 'egreso'
  const [itemSeleccionado, setItemSeleccionado] = useState(null)
  const [loadingForm, setLoadingForm]           = useState(false)
  const [formAjuste, setFormAjuste]             = useState({ cantidad_nueva: '', motivo: '' })
  const [formEgreso, setFormEgreso]             = useState({ cantidad: '', motivo: '' })
 
  // ── Carrito compartido (ingreso y transferencia) ───────────────────────────
  const [carrito, setCarrito]         = useState([])  // [{ _key, accesorio_id, nombre, sku, cantidad }]
  const [formItem, setFormItem]       = useState(itemVacio)
  const [localId, setLocalId]         = useState(null)
  const [localOrigenId, setLocalOrigenId]   = useState(null)
  const [localDestinoId, setLocalDestinoId] = useState(null)
  const [observaciones, setObservaciones]   = useState('')
  const [loadingConfirmar, setLoadingConfirmar] = useState(false)
  const [receptorId, setReceptorId] = useState(null)


  const { options, buscadorSelect } = 
          useSelectOptions(['accesorios','tipos', 'subtipos'])
 
  const [loadingExport, setLoadingExport] = useState(false)
 
  // auth
  const { rol } = useAuth()

  // ─── Helpers ──────────────────────────────────────────────────────────────
  const handleExportar = async () => {
    setLoadingExport(true)
    try {
      const blob = await api.exportarStock({
        buscar: busqueda, tipo_id: filtroTipoId, subtipo_id: filtroSubtipoId,
        local_id: filtroLocalId, activo: filtroActivo,
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'stock.xlsx'
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      mostrarAlerta('error', `Error al exportar: ${err.message}`)
    } finally {
      setLoadingExport(false)
    }
  }
 
  // ─── Navegación entre modos ───────────────────────────────────────────────
  const abrirIngreso = () => {
    setCarrito([])
    setFormItem(itemVacio)
    setLocalId(locales[0]?.local_id ?? null)
    setObservaciones('')
    buscadorSelect('accesorios', '')
    setAccion(null)
    setItemSeleccionado(null)
    setModo('ingreso')
  }
 
  const abrirTransferencia = () => {
    setCarrito([])
    setFormItem(itemVacio)
    setLocalOrigenId(locales[0]?.local_id ?? null)
    setLocalDestinoId(locales[1]?.local_id ?? null)
    setObservaciones('')
    buscadorSelect('accesorios', '')
    setAccion(null)
    setItemSeleccionado(null)
    setModo('transferencia')
  }
 
  const volverALista = () => {
    setModo('lista')
    setAccion(null)
    setReceptorId(null)
    setLocalId(null)
    setItemSeleccionado(null)
    setCarrito([])
    setObservaciones(null)
    setFormItem(itemVacio)
  }
 
  // ─── Carrito: agregar ítem ────────────────────────────────────────────────
  const handleAgregarItem = () => {
    if (!formItem.accesorio_id || !formItem.accesorio_data) {
      mostrarAlerta('error', 'Seleccioná un accesorio.')
      return
    }
    const cantidad = parseInt(formItem.cantidad)
    if (!cantidad || cantidad <= 0) {
      mostrarAlerta('error', 'La cantidad debe ser mayor a cero.')
      return
    }
 
    const existe = carrito.find(c => c.accesorio_id === formItem.accesorio_id)
    if (existe) {
      // Sumamos la cantidad si ya está en el carrito
      // en realidad cambio la cantidad, el ingreso es fijo
      setCarrito(prev => prev.map(c =>
        c.accesorio_id === formItem.accesorio_id
          ? { ...c, cantidad: + cantidad }
          : c
      ))
    } else {
      setCarrito(prev => [...prev, {
        _key:         `acc-${formItem.accesorio_id}`,
        accesorio_id: formItem.accesorio_id,
        nombre:       formItem.accesorio_data.nombre,
        sku:          formItem.accesorio_data.sku,
        cantidad,
      }])
    }
    setFormItem(itemVacio)
    buscadorSelect('accesorios', '')
  }
 
  const handleEliminarDelCarrito = (key) =>
    setCarrito(prev => prev.filter(c => c._key !== key))
 
  const handleCantidadCarrito = (key, valor) => {
    const n = parseInt(valor)
    if (!n || n <= 0) return
    setCarrito(prev => prev.map(c => c._key === key ? { ...c, cantidad: n } : c))
  }
 
  // ─── Confirmar ingreso de lote ────────────────────────────────────────────
  const handleConfirmarIngreso = async () => {
    if (carrito.length === 0) { mostrarAlerta('error', 'Agregá al menos un producto.'); return }
    if (!localId)             { mostrarAlerta('error', 'Seleccioná un local.');         return }
 
    setLoadingConfirmar(true)
    try {
      const payload = {
        local_id:     localId,
        receptor_id: receptorId,
        observaciones: observaciones || null,
        productos: carrito.map(c => ({
          accesorio_id:     c.accesorio_id,
          cantidad_ingreso: c.cantidad,
        })),
      }
      const res = await api.ingresarLote(payload)
      mostrarAlerta('success', `Lote #${res.ingreso_lote_id} ingresado con éxito.`)
      refetch()
      volverALista()
      descargarIngresoPdf(res.ingreso_lote_id, (msg) => mostrarAlerta('error', msg))
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingConfirmar(false)
    }
  }

  // ─── Confirmar transferencia de lote ─────────────────────────────────────
  const handleConfirmarTransferencia = async () => {
    if (carrito.length === 0)          { mostrarAlerta('error', 'Agregá al menos un producto.'); return }
    if (!localOrigenId)                { mostrarAlerta('error', 'Seleccioná el local de origen.'); return }
    if (!localDestinoId)               { mostrarAlerta('error', 'Seleccioná el local de destino.'); return }
    if (localOrigenId === localDestinoId) { mostrarAlerta('error', 'El origen y destino no pueden ser el mismo local.'); return }
 
    setLoadingConfirmar(true)
    try {
      const payload = {
        local_origen_id:  localOrigenId,
        local_destino_id: localDestinoId,
        observaciones:    observaciones || null,
        productos: carrito.map(c => ({
          accesorio_id:         c.accesorio_id,
          cantidad_a_transferir: c.cantidad,
        })),
      }
      const res = await api.transferirLote(payload)
      mostrarAlerta('success', `Transferencia #${res.transferencia_id} registrada con éxito.`)
      refetch()
      volverALista()
      descargarTransferenciaPdf(res.transferencia_id, (msg) => mostrarAlerta('error', msg))
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingConfirmar(false)
    }
  }
 
  // ─── Acciones sobre la tabla (ajuste / egreso) ────────────────────────────
  const abrirAjuste = (item) => {
    setModo('lista')
    setItemSeleccionado(item)
    setFormAjuste({ cantidad_nueva: item.cantidad, motivo: '' })
    setAccion('ajustar')
  }
 
  const abrirEgreso = (item) => {
    setModo('lista')
    setItemSeleccionado(item)
    setFormEgreso({ cantidad: '', motivo: '' })
    setAccion('egreso')
  }
 
  const cancelarAccion = () => {
    setAccion(null)
    setItemSeleccionado(null)
  }
 
  const handleAjuste = async (e) => {
    e.preventDefault()
    setLoadingForm(true)
    try {
      const res = await api.ajustarStock({
        accesorio_id:   itemSeleccionado.accesorio_id,
        local_id:       itemSeleccionado.local_id,
        cantidad_nueva: parseInt(formAjuste.cantidad_nueva),
        motivo:         formAjuste.motivo,
      })
      const f = new Date(res.fecha).toLocaleString('es-AR', {
        day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
      })
      mostrarAlerta('success',
        `Ajuste: ${res.stock_anterior} → ${res.stock_nuevo} (${res.diferencia > 0 ? '+' : ''}${res.diferencia}) — ${f}`
      )
      cancelarAccion()
      refetch()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingForm(false)
    }
  }
 
  const handleEgreso = async (e) => {
    e.preventDefault()
    setLoadingForm(true)
    try {
      const res = await api.egresoStock({
        accesorio_id:    itemSeleccionado.accesorio_id,
        local_id:        itemSeleccionado.local_id,
        tipo_movimiento: 'SALIDA',
        cantidad:        parseInt(formEgreso.cantidad),
        motivo:          formEgreso.motivo || null,
      })
      const f = new Date(res.movimiento.fecha).toLocaleString('es-AR', {
        day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
      })
      mostrarAlerta('success',
        `Egreso de ${formEgreso.cantidad} unidades. Stock nuevo: ${res.stock.cantidad_actual} — ${f}`
      )
      cancelarAccion()
      refetch()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingForm(false)
    }
  }
 
  // ─── RENDER ───────────────────────────────────────────────────────────────
  const hayFormActivo = accion && itemSeleccionado
 
  return (
    <div className="page-container">
 
      {/* ── Header ── */}
      <div className="page-header">
        <h2>
          {modo === 'lista'         && 'Inventario'}
          {modo === 'ingreso'       && 'Ingreso de lote'}
          {modo === 'transferencia' && 'Transferencia de lote'}
        </h2>
 
        {modo === 'lista' && !hayFormActivo && (
          <div style={{ display: 'flex', gap: 10 }}>
            {rol === 'admin' && <button className="btn btn-primary"    onClick={abrirIngreso}>+ Ingresar lote</button>}
            <button className="btn btn-transferir" onClick={abrirTransferencia}>⇄ Transferir</button>
          </div>
        )}
 
        {(modo === 'ingreso' || modo === 'transferencia') && (
          <button className="btn btn-secondary" onClick={volverALista} disabled={loadingConfirmar}>
            ← Volver
          </button>
        )}
      </div>
 
      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.msg}</span>
          <button className="alerta-cerrar" onClick={cerrarAlerta}>✕</button>
        </div>
      )}
 
      {/* ══════════════════════════════════════════════════════════════════════
          MODO INGRESO DE LOTE
      ══════════════════════════════════════════════════════════════════════ */}
      {modo === 'ingreso' && (
        <>
          {/* ── Selector de local + observaciones ── */}
          <SelectorLocalObs
            localId={localId}
            setLocalId={setLocalId}
            receptorId={receptorId}
            setReceptorId={setReceptorId}
            usuarios={usuarios}
            observaciones={observaciones}
            setObservaciones={setObservaciones}
            locales={locales}
            showReceptor={true}
          />

          {/* ── Formulario para agregar ítem ── */}
          <AgregarProducto
            options={options}
            formItem={formItem}
            setFormItem={setFormItem}
            buscadorSelect={buscadorSelect}
            handleAgregarItem={handleAgregarItem}
          ></AgregarProducto>
 
          {/* ── Carrito ── */}
          <CarritoProductos
            carrito={carrito}
            titulo="Productos a ingresar"
            onConfirmar={handleConfirmarIngreso}
            loading={loadingConfirmar}
            disabled={!localId}
            textoBoton="✓ Confirmar ingreso"
            classBoton="btn btn-primary"
            handleCantidadCarrito={handleCantidadCarrito}
            handleEliminarDelCarrito={handleEliminarDelCarrito}
          />
        </>
      )}
 
      {/* ══════════════════════════════════════════════════════════════════════
          MODO TRANSFERENCIA DE LOTE
      ══════════════════════════════════════════════════════════════════════ */}
      {modo === 'transferencia' && (
        <>
          {/* ── Selector de locales + observaciones ── */}
          <SelectorLocalObs
            mode="transferencia"
            localOrigenId={localOrigenId}
            setLocalOrigenId={setLocalOrigenId}
            localDestinoId={localDestinoId}
            setLocalDestinoId={setLocalDestinoId}
            observaciones={observaciones}
            setObservaciones={setObservaciones}
            locales={locales}
          />
 
          {/* ── Formulario para agregar ítem ── */}
          <AgregarProducto
            options={options}
            formItem={formItem}
            setFormItem={setFormItem}
            buscadorSelect={buscadorSelect}
            handleAgregarItem={handleAgregarItem}
          ></AgregarProducto>
 
          {/* ── Carrito ── */}
          <CarritoProductos
            carrito={carrito}
            titulo="Productos a transferir"
            onConfirmar={handleConfirmarTransferencia}
            loading={loadingConfirmar}
            disabled={!localOrigenId || !localDestinoId}
            textoBoton="⇄ Confirmar transferencia"
            classBoton="btn btn-transferir"
            handleCantidadCarrito={handleCantidadCarrito}
            handleEliminarDelCarrito={handleEliminarDelCarrito}
          />
        </>
      )}
 
      {/* ══════════════════════════════════════════════════════════════════════
          MODO LISTA
      ══════════════════════════════════════════════════════════════════════ */}
      {modo === 'lista' && (
        <>
          {/* ── Form inline sobre ítem seleccionado ── */}
          {hayFormActivo && (
            <div className="form-card">
              <h3>{accion === 'ajustar' ? 'Ajustar stock' : 'Egreso de stock'}</h3>
              <p className="modal-subtitulo" style={{ marginBottom: 16 }}>
                <strong>{itemSeleccionado.accesorio_nombre}</strong>
                {' — '}{itemSeleccionado.local_nombre}
                <br />
                <span className="modal-stock-actual">Stock actual: <strong>{itemSeleccionado.cantidad}</strong></span>
              </p>
 
              {/* ── AJUSTE ── */}
              {accion === 'ajustar' && (
                <form onSubmit={handleAjuste} className="acc-form">
                  <div className="form-row">
                    <div className="form-group">
                      <label>Nueva cantidad *</label>
                      <input
                        type="number" min={0}
                        value={formAjuste.cantidad_nueva}
                        onChange={e => setFormAjuste(p => ({ ...p, cantidad_nueva: e.target.value }))}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Motivo *</label>
                      <input
                        type="text"
                        placeholder="Ej: Inventario físico del 10/03"
                        value={formAjuste.motivo}
                        onChange={e => setFormAjuste(p => ({ ...p, motivo: e.target.value }))}
                        required
                      />
                    </div>
                  </div>
                  <div className="form-actions">
                    <button type="button" className="btn btn-secondary" onClick={cancelarAccion} disabled={loadingForm}>Cancelar</button>
                    <button type="submit" className="btn btn-primary" disabled={loadingForm}>
                      {loadingForm ? 'Guardando...' : 'Confirmar ajuste'}
                    </button>
                  </div>
                </form>
              )}
 
              {/* ── EGRESO ── */}
              {accion === 'egreso' && (
                <form onSubmit={handleEgreso} className="acc-form">
                  <div className="form-row">
                    <div className="form-group">
                      <label>Cantidad a egresar *</label>
                      <input
                        type="number" min={1} max={itemSeleccionado.cantidad}
                        value={formEgreso.cantidad}
                        onChange={e => setFormEgreso(p => ({ ...p, cantidad: e.target.value }))}
                        required
                      />
                      <span className="field-hint">Máximo: {itemSeleccionado.cantidad}</span>
                    </div>
                    <div className="form-group">
                      <label>Motivo</label>
                      <input
                        type="text" placeholder="Opcional"
                        value={formEgreso.motivo}
                        onChange={e => setFormEgreso(p => ({ ...p, motivo: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div className="form-actions">
                    <button type="button" className="btn btn-secondary" onClick={cancelarAccion} disabled={loadingForm}>Cancelar</button>
                    <button type="submit" className="btn btn-danger" disabled={loadingForm}>
                      {loadingForm ? 'Egresando...' : '⬇ Confirmar egreso'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}
 
          {/* ── Buscador y filtros (se ocultan mientras hay form abierto) ── */}
          {!hayFormActivo && (
            <>
              <div className="lista-toolbar">
                <input
                  className="buscador"
                  type="search"
                  placeholder="Buscar por nombre de accesorio..."
                  value={busqueda}
                  onChange={handleBusqueda}
                />
                <button
                  className="btn btn-export"
                  onClick={handleExportar}
                  disabled={loadingExport}
                >
                  {loadingExport ? 'Exportando...' : '⬇ Exportar Excel'}
                </button>
              </div>
 
              <div className="filtros-panel">
                <span className="filtros-label">Filtrar por:</span>
 
                <div className="filtros-row">
                  <span className="filtros-sublabel">Estado:</span>
                  <div className="filtros-chips">
                    {[{ valor: true, label: 'Activos' }, { valor: false, label: 'Inactivos' }].map(({ valor, label }) => (
                      <button
                        key={label}
                        className={`filtro-chip ${filtroActivo === valor ? 'filtro-chip-activo' : ''}`}
                        onClick={() => handleFiltroActivo(valor)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
 
                {locales.length > 0 && (
                  <div className="filtros-row">
                    <span className="filtros-sublabel">Local:</span>
                    <div className="filtros-chips">
                      {locales.map(l => (
                        <button
                          key={l.local_id}
                          className={`filtro-chip ${filtroLocalId === l.local_id ? 'filtro-chip-activo' : ''}`}
                          onClick={() => handleFiltroLocal(l.local_id)}
                        >
                          {l.nombre}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
 
                {tiposFiltro.length > 0 && (
                  <div className="filtros-row">
                    <span className="filtros-sublabel">Tipo:</span>
                    <SearchableSelect
                        options={options.tipos}
                        value={filtroTipoId}
                        onChange={(val) => {
                          handleFiltroTipo(val) // se encarga useTabla con el id del objeto seleccionado
                        }}
                        onSearch={(t) => buscadorSelect('tipos', t)}
                        placeholder="Filtrar por tipo"
                      />
                  </div>
                )}
 
                {filtroTipoId && subtiposFiltro.length > 0 && (
                  <div className="filtros-subtipos">
                    <span className="filtros-sublabel">Subtipo:</span>
                    {/* ss maneja su busqueda interna, cuando se selecciona
                    un value, usa la f que le paso que es hfiltro
                    ese setea un filtro de useTabla q modifica el listado
                    principal de stock en funcion del id q le paso */}
                    <div className='ss-filtro-subtipo'>
                      <SearchableSelect
                          options={options.subtipos}
                          value={filtroSubtipoId}
                          onChange={(id) => {
                            handleFiltroSubtipo(id)
                          }}
                          onSearch={(t) => buscadorSelect('subtipos', t)}
                          placeholder="Filtrar por subtipo"
                        />
                    </div>
                  </div>
                )}
 
                {hayFiltrosActivos && (
                  <button className="btn-limpiar-filtros" onClick={limpiarFiltros}>✕ Limpiar filtros</button>
                )}
              </div>
            </>
          )}
 
          {/* ── Tabla ── */}
          {loadingLista ? (
            <p className="empty-msg">Cargando...</p>
          ) : stock.length === 0 ? (
            <p className="empty-msg">
              {busqueda ? `Sin resultados para "${busqueda}".` : 'No hay stock registrado.'}
            </p>
          ) : (
            <>
              <div className="table-wrapper">
                <table className="acc-table">
                  <thead>
                    <tr>
                      <th>SKU</th>
                      <th>Accesorio</th>
                      <th>Local</th>
                      <th>Cantidad</th>
                      {rol === 'admin' && <th>Acciones</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {stock.map(item => (
                      <tr
                        key={item.id}
                        className={[
                          item.cantidad === 0 ? 'row-sin-stock' : '',
                          itemSeleccionado?.id === item.id ? 'row-seleccionada' : '',
                        ].join(' ')}
                      >
                        <td><span className="sku-badge">{item.accesorio_sku}</span></td>
                        <td>{item.accesorio_nombre}</td>
                        <td>{item.local_nombre}</td>
                        <td>
                          <span className={`cantidad-badge ${
                            item.cantidad === 0 ? 'cantidad-cero'
                            : item.cantidad <= 3 ? 'cantidad-baja'
                            : 'cantidad-ok'
                          }`}>
                            {item.cantidad}
                          </span>
                        </td>
                          {rol === 'admin' &&
                          <td className="acciones-cell">
                          <button className="btn btn-sm btn-secondary" onClick={() => abrirAjuste(item)}>Ajustar</button>
                          <button className="btn btn-sm btn-danger"    onClick={() => abrirEgreso(item)}>⬇ Egreso</button>
                        </td>}
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
        </>
      )}
    </div>
  )
}
 