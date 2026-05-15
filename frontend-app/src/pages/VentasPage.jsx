import { useState, useEffect } from 'react'
import './AccesoriosPage.css'
import './VentasPage.css'
import { api, LIMIT } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import SearchableSelect from '../components/SearchableSelect/SearchableSelect'
import  useSelectOptions from '../hooks/useSelectOptions/'
import {useAuth} from '../hooks/useAuth'
import { useModalDetalle } from '../hooks/ventas/useModalDetalles'
import ModalDetalle from '../components/ventas/ModalDetalle'
import { formatFecha, formatPrecio } from '../helpers/formats'

// ─── COMPONENTE PRINCIPAL ─────────────────────────────────────────────────────
export default function VentasPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()
  const {rol} = useAuth()

  // ── Modo ──────────────────────────────────────────────────────────────────
  const [modo, setModo] = useState('listado') // 'listado' | 'creacion'
  const [tipoOperacion, setTipoOperacion] = useState('VENTA') // 'VENTA' | 'DEVOLUCION'

  // ── Listado ───────────────────────────────────────────────────────────────
  const [ventas, setVentas]             = useState([])
  const [loadingLista, setLoadingLista] = useState(false)
  const [pagina, setPagina]             = useState(0)
  const [hayMas, setHayMas]             = useState(false)

  // ── Locales ───────────────────────────────────────────────────────────────
  const [locales, setLocales]   = useState([])
  const [localId, setLocalId]   = useState(null)

  // ── Creación: carrito ─────────────────────────────────────────────────────
  const [productos, setProductos] = useState([])
  // productos: [{ _key, tipo, id, label, precio_unitario, cantidad, imei?, numero_serie? }]

  // ── Creación: 3 formularios independientes ────────────────────────────────
  const [formAccAbierto, setFormAccAbierto]   = useState(false)
  const [formAccId, setFormAccId]             = useState(null)
  const [formAccData, setFormAccData]         = useState(null)
  const [formAccPrecio, setFormAccPrecio]     = useState('')
  const [formAccCantidad, setFormAccCantidad] = useState(1)

  const [formCelAbierto, setFormCelAbierto]   = useState(false)
  const [formCelId, setFormCelId]             = useState(null)
  const [formCelData, setFormCelData]         = useState(null)
  const [formCelPrecio, setFormCelPrecio]     = useState('')

  const [formChipAbierto, setFormChipAbierto] = useState(false)
  const [formChipId, setFormChipId]           = useState(null)
  const [formChipData, setFormChipData]       = useState(null)
  const [formChipPrecio, setFormChipPrecio]   = useState('')

  // Opciones de los SearchableSelect via hook compartido
  const { options, buscadorSelect } = useSelectOptions(['accesoriosConStock', 'celulares', 'chips'])

  // ── Creación: pago ────────────────────────────────────────────────────────
  const [medioPago, setMedioPago]           = useState('efectivo') // 'efectivo' | 'electronico' | 'ambos'
  const [montoEfectivo, setMontoEfectivo]   = useState('')
  const [montoElectronico, setMontoElectronico] = useState('')

  // ── Loading confirmar ─────────────────────────────────────────────────────
  const [loadingConfirmar, setLoadingConfirmar] = useState(false)

  // ── Total derivado (nunca estado) ─────────────────────────────────────────
  const total = productos.reduce(
    (acc, p) => acc + p.precio_unitario * p.cantidad, 0
  )

  const [usuarios, setUsuarios] = useState([])
  const [usuarioId, setUsuarioId] = useState(null)

  const {modalItem, modalAbierto, loadingModal, abrirModal, cerrarModal} = useModalDetalle(api.getDetallesVenta)

  const [cuotas, setCuotas] = useState(1);
  const [medioPagoElectronico, setMedioPagoElectronico] = useState("QR");

  // ── Fecha de venta (solo admin puede modificar) ───────────────────────────
  const hoyArgentina = () => new Date().toLocaleDateString('en-CA', { timeZone: 'America/Argentina/Buenos_Aires' })
  const [fechaVenta, setFechaVenta] = useState(hoyArgentina)
  
  // ─── Caja diaria ──────────────────────────────────────────────────────────────
  const [fechaCaja, setFechaCaja] = useState('')
  const [loadingCaja, setLoadingCaja] = useState(false)

  // ─── Sobrante / Faltante ──────────────────────────────────────────────────────
  const [sobrante, setSobrante] = useState('')
  const [faltante, setFaltante] = useState('')
  const [loadingSF, setLoadingSF] = useState(false)

  const handleGenerarCajaDiaria = async () => {
    if (!localId) { mostrarAlerta('error', 'Seleccioná un local.'); return }
    if (!fechaCaja) { mostrarAlerta('error', 'Seleccioná una fecha.'); return }
    setLoadingCaja(true)
    try {
      const blob = await api.generarCajaDiaria({
        local_id: localId,
        ...(rol === 'admin' && { usuario_id: usuarioId }),
        fecha: fechaCaja,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `caja_${fechaCaja}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      mostrarAlerta('error', `Error al generar caja: ${err.message}`)
    } finally {
      setLoadingCaja(false)
    }
  }

  const handleGuardarSF = async () => {
    if (!localId) { mostrarAlerta('error', 'Seleccioná un local.'); return }
    if (rol === 'admin' && !fechaCaja) { mostrarAlerta('error', 'Seleccioná una fecha.'); return }
    if (parseInt(sobrante) > 0 && parseInt(faltante) > 0) {
      mostrarAlerta('error', 'No podés ingresar sobrante y faltante al mismo tiempo.')
      return
    }
    setLoadingSF(true)
    try {
      const body = {
        local_id: localId,
        sobrante: parseInt(sobrante) || 0,
        faltante: parseInt(faltante) || 0,
        ...(rol === 'admin' && { usuario_id: usuarioId }),
        ...(rol === 'admin' && { fecha: fechaCaja }),
      }
      await api.upsertSobranteFaltante(body)
      mostrarAlerta('success', 'Sobrante/faltante guardado.')
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingSF(false)
    }
  }

  // ─── Formulario egresos ────────────────────────────────────────────────────────
  const [formEgresoAbierto, setFormEgresoAbierto] = useState(false);
  const [montoEgreso, setMontoEgreso] = useState('');
  const [descripcionEgreso, setDescripcionEgreso] = useState('');

  const abrirFormEgresos = () => {
    setFormEgresoAbierto(true)
  }

  const cerrarFormEgresos = () => {
    setFormEgresoAbierto(false)
    setMontoEgreso('')
    setDescripcionEgreso('')
  }


  // ─── Efectos ──────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchUsuarios()
    fetchLocales()
  }, [])

  useEffect(() => {
    if (localId !== null) {
      fetchVentas(0)
    }
  }, [localId, fechaCaja, usuarioId])

  // ─── Usuarios ──────────────────────────────────────────────────────────────
  const fetchUsuarios = async () => {
    try {
      const data = await api.listarUsuarios()
      setUsuarios(data)
      if (data.length > 0) setUsuarioId(data[0].usuario_id)
    } catch (err) {
      mostrarAlerta('error', `Error al cargar usuarios: ${err.message}`)
    }
  }

  // ─── Locales ──────────────────────────────────────────────────────────────
  const fetchLocales = async () => {
    try {
      const data = await api.listarLocales({tipo: "LOCAL"})
      setLocales(data)
      if (data.length > 0) setLocalId(data[0].local_id)
    } catch (err) {
      mostrarAlerta('error', `Error al cargar locales: ${err.message}`)
    }
  }

  // ─── Listado ──────────────────────────────────────────────────────────────
  const fetchVentas = async (pag) => {
    setLoadingLista(true)
    try {
      const data = await api.listarVentas({ skip: pag * 10, limit: 10 + 1, local_id: localId, fecha: fechaCaja, usuario_id: usuarioId})
      setHayMas(data.length > 10)
      setVentas(data.slice(0, 10))
    } catch (err) {
      mostrarAlerta('error', `Error al cargar ventas: ${err.message}`)
    } finally {
      setLoadingLista(false)
    }
  }

  const irAPagina = (nueva) => {
    setPagina(nueva)
    fetchVentas(nueva)
  }

  // ─── Formulario egresos ────────────────────────────────────────────────────────


  // ─── Modo creación ────────────────────────────────────────────────────────
  const abrirCreacion = (tipo) => {
    setTipoOperacion(tipo)
    setProductos([])
    setFormAccAbierto(false); setFormCelAbierto(false); setFormChipAbierto(false)
    setMedioPago('efectivo')
    setMontoEfectivo('')
    setMontoElectronico('')
    setMedioPagoElectronico('QR')
    setCuotas(1)
    setFechaVenta(hoyArgentina())
    cerrarFormEgresos()
    setModo('creacion')
  }

  const volverAListado = () => {
    setModo('listado')
    setFormAccAbierto(false); setFormCelAbierto(false); setFormChipAbierto(false)
  }

  // ─── Formulario inline de producto ───────────────────────────────────────
  // ─── Abrir formularios ────────────────────────────────────────────────────

  const cerrarTodos = () => {
    setFormAccAbierto(false)
    setFormCelAbierto(false)
    setFormChipAbierto(false)
  }

  const abrirFormAcc = () => {
    cerrarTodos()
    setFormAccAbierto(true)
    setFormAccId(null); setFormAccData(null); setFormAccPrecio(''); setFormAccCantidad(1)
    buscadorSelect('accesoriosConStock', '', { local_id: localId })
  }
  const cerrarFormAcc = () => {
    setFormAccAbierto(false)
    setFormAccId(null); setFormAccData(null); setFormAccPrecio(''); setFormAccCantidad(1)
  }
  const limpiarFormAcc = () => {
    setFormAccId(null); setFormAccData(null); setFormAccPrecio(''); setFormAccCantidad(1)
  }

  const abrirFormCel = () => {
    cerrarTodos()
    setFormCelAbierto(true)
    setFormCelId(null); setFormCelData(null); setFormCelPrecio('')
    buscadorSelect('celulares', { estado: tipoOperacion === 'VENTA' ? 'DISPONIBLE' : 'VENDIDO' , local_id: localId })
  }
  const cerrarFormCel = () => {
    setFormCelAbierto(false)
    setFormCelId(null); setFormCelData(null); setFormCelPrecio('')
  }

  const abrirFormChip = () => {
    cerrarTodos()
    setFormChipAbierto(true)
    setFormChipId(null); setFormChipData(null); setFormChipPrecio('')
    buscadorSelect('chips', '',  {estado: tipoOperacion === 'VENTA' ? 'DISPONIBLE' : 'VENDIDO' , local_id: localId})
  }
  const cerrarFormChip = () => {
    setFormChipAbierto(false)
    setFormChipId(null); setFormChipData(null); setFormChipPrecio('')
  }

  // ─── Selección en cada SearchableSelect ──────────────────────────────────
  const handleSeleccionAcc = (id) => {
    setFormAccId(id)
    const found = options.accesoriosConStock.find(o => o.value === id)
    setFormAccData(found?._raw ?? null)
    setFormAccPrecio(found?._raw?.precio ?? '')
  }

  const handleSeleccionCel = (id) => {
    setFormCelId(id)
    const found = options.celulares.find(o => o.value === id)
    setFormCelData(found?._raw ?? null)
    setFormCelPrecio(found?._raw?.precio ?? '')
  }

  const handleSeleccionChip = (id) => {
    setFormChipId(id)
    const found = options.chips.find(o => o.value === id)
    setFormChipData(found?._raw ?? null)
    setFormChipPrecio(found?._raw?.precio ?? '')
  }

  // ─── Agregar cada tipo al carrito ─────────────────────────────────────────
  const handleAgregarAcc = () => {
    if (!formAccId || !formAccData) { mostrarAlerta('error', 'Seleccioná un accesorio.'); return }
    const precio   = parseInt(formAccPrecio)
    const cantidad = parseInt(formAccCantidad)
    if (!precio || precio <= 0)     { mostrarAlerta('error', 'El precio debe ser mayor a cero.'); return }
    if (!cantidad || cantidad <= 0) { mostrarAlerta('error', 'La cantidad debe ser mayor a cero.'); return }
    const existe = productos.find(p => p.tipo === 'accesorio' && p.id === formAccId)
    if (existe) {
      // el estado deberia ser inmutable, no puedo mutar un estado que ya existe
      // debo crear uno nuevo
      setProductos(prev => prev.map(p =>
        p.tipo === 'accesorio' && p.id === formAccId
          ? { ...p, cantidad: p.cantidad + cantidad }
          : p
      ))
    } else {
      setProductos(prev => [...prev, {
        _key: `acc-${formAccId}`,
        tipo: 'accesorio',
        id: formAccId,
        label: formAccData.nombre,
        precio_unitario: precio,
        cantidad,
      }])
    }
    limpiarFormAcc()
  }

  const handleAgregarCel = () => {
    if (!formCelId || !formCelData) { mostrarAlerta('error', 'Seleccioná un celular.'); return }
    const precio = parseInt(formCelPrecio)
    if (!precio || precio <= 0) { mostrarAlerta('error', 'El precio debe ser mayor a cero.'); return }
    if (productos.find(p => p.tipo === 'celular' && p.id === formCelId)) {
      mostrarAlerta('error', 'Este celular ya fue agregado.'); return
    }
    setProductos(prev => [...prev, {
      _key: `cel-${formCelId}`,
      tipo: 'celular',
      id: formCelId,
      label: `IMEI: ${formCelData.imei}`,
      precio_unitario: precio,
      cantidad: 1,
      imei: formCelData.imei,
    }])
    cerrarFormCel()
  } 

  const handleAgregarChip = () => {
    if (!formChipId || !formChipData) { mostrarAlerta('error', 'Seleccioná un chip.'); return }
    const precio = parseInt(formChipPrecio)
    if (!precio || precio <= 0) { mostrarAlerta('error', 'El precio debe ser mayor a cero.'); return }
    if (productos.find(p => p.tipo === 'chip' && p.id === formChipId)) {
      mostrarAlerta('error', 'Este chip ya fue agregado.'); return
    }
    setProductos(prev => [...prev, {
      _key: `chip-${formChipId}`,
      tipo: 'chip',
      id: formChipId,
      label: `${formChipData.compania} — Serie: ${formChipData.numero_serie}`,
      precio_unitario: precio,
      cantidad: 1,
      numero_serie: formChipData.numero_serie,
    }])
    cerrarFormChip()
  }

  // ─── Editar carrito inline ────────────────────────────────────────────────
  const handleCantidadCarrito = (key, valor) => {
    const n = parseInt(valor)
    if (!n || n <= 0) return
    setProductos(prev => prev.map(p => p._key === key ? { ...p, cantidad: n } : p))
  }

  const handlePrecioCarrito = (key, valor) => {
    const n = parseInt(valor)
    if (!n || n <= 0) return
    setProductos(prev => prev.map(p => p._key === key ? { ...p, precio_unitario: n } : p))
  }

  const handleEliminar = (key) => {
    setProductos(prev => prev.filter(p => p._key !== key))
  }

  // ─── Confirmar venta ──────────────────────────────────────────────────────
  const handleConfirmar = async () => {
    // Validaciones
    if (productos.length === 0) {
      mostrarAlerta('error', 'Agregá al menos un producto.')
      return
    }
    if (total <= 0) {
      mostrarAlerta('error', 'El total debe ser mayor a cero.')
      return
    }
    if (!localId) {
      mostrarAlerta('error', 'No hay un local seleccionado.')
      return
    }
    if (rol == 'admin' && !usuarioId) {
      mostrarAlerta('error', 'No hay usuario seleccionado.')
      return
    }

    if (medioPago === 'electronico' && !medioPagoElectronico) {
      mostrarAlerta('error', 'Seleccioná un medio de pago electrónico.')
      return
    }

    if (medioPago === 'electronico' && !cuotas) {
      mostrarAlerta('error', 'Seleccioná cantidad de cuotas.')
      return
    }

    if (medioPago === 'ambos'  && !medioPagoElectronico) {
      mostrarAlerta('error', 'Seleccioná el medio de pago electrónico.')
      return
    }

    if (medioPagoElectronico !== 'CREDITO' && cuotas > 1) {
      mostrarAlerta('error', 'Las cuotas solo aplican a pagos con tarjeta de crédito.')
      return
    }

    // Construir pagos
    let pagos = []
    if (medioPago === 'efectivo') {
      pagos = [{ medio_de_pago: 'EFECTIVO', importe: total }]
    } else if (medioPago === 'electronico') {
      pagos = [{ medio_de_pago: medioPagoElectronico, importe: total, cuotas: cuotas }]
    } else {
      // ambos
      const ef  = parseInt(montoEfectivo)  || 0
      const el  = parseInt(montoElectronico) || 0
      if (ef + el !== total) {
        mostrarAlerta('error', `La suma de los pagos ($${(ef + el).toLocaleString('es-AR')}) no coincide con el total ($${total.toLocaleString('es-AR')}).`)
        return
      }
      if (ef > 0)  pagos.push({ medio_de_pago: 'EFECTIVO',    importe: ef })
      if (el > 0)  pagos.push({ medio_de_pago: medioPagoElectronico, importe: el, cuotas: cuotas })
    }

    // Construir payload
    const payload = {
      local_id:   localId,
      tipo:       tipoOperacion,
      pagos,
      detalles_accesorios: productos
        .filter(p => p.tipo === 'accesorio')
        .map(p => ({ accesorio_id: p.id, precio_unitario: p.precio_unitario, cantidad: p.cantidad })),
      detalles_celulares: productos
        .filter(p => p.tipo === 'celular')
        .map(p => ({ celular_id: p.id, imei: p.imei, precio_unitario: p.precio_unitario })),
      detalles_chips: productos
        .filter(p => p.tipo === 'chip')
        .map(p => ({ chip_id: p.id, numero_serie: p.numero_serie, precio_unitario: p.precio_unitario })),
      ...(rol === 'admin' && { usuario_id: usuarioId }), // si es admin el usuario es seleccionado
      ...(rol === 'admin' && { fecha_ingreso: fechaVenta }),
    }

    setLoadingConfirmar(true)
    try {
      await api.crearVenta(payload)
      mostrarAlerta('success', tipoOperacion === 'VENTA' ? 'Venta registrada correctamente.' : 'Devolución registrada correctamente.')
      setPagina(0)
      fetchVentas(0)
      volverAListado()
    } catch (err) {
      mostrarAlerta('error', `Error: ${err.message}`)
    } finally {
      setLoadingConfirmar(false)
    }
  }

  const handleConfirmarEgreso = async () => {
    if (!montoEgreso || !descripcionEgreso) {
      mostrarAlerta('error', 'Ingresar monto y descripcion')
      return
    };

    if (!localId) {
      mostrarAlerta('error', 'No hay un local seleccionado.')
      return
    }
    if (rol == 'admin' && !usuarioId) {
      mostrarAlerta('error', 'No hay usuario seleccionado.')
      return
    }
    console.log("CROBAL")
    try {
      await api.crearEgreso({
        monto: parseInt(montoEgreso),
        descripcion: descripcionEgreso,
        local_id: localId,
        ...(rol === 'admin' && { usuario_id: usuarioId }), // si es admin el usuario es seleccionado
        ...(rol === 'admin' && { fecha: fechaCaja }),
      });
      mostrarAlerta('success', 'Egreso registrado correctamente')
      setLoadingConfirmar(true)
      setMontoEgreso('');
      setDescripcionEgreso('');
      cerrarFormEgresos();
      } catch (err) {
        mostrarAlerta('error', `Error: ${err.message}`)
      } finally {
        setLoadingConfirmar(false)
    }
  };

  // ─── RENDER ───────────────────────────────────────────────────────────────
  return (
    <div className="page-container">

      {/* ── Header ── */}
      <div className="page-header">
        <h2>
          {modo === 'listado'  && 'Ventas'}
          {modo === 'creacion' && tipoOperacion === 'VENTA'      && 'Nueva venta'}
          {modo === 'creacion' && tipoOperacion === 'DEVOLUCION' && 'Nueva devolución'}
        </h2>
        {modo === 'listado' && (
          <div className="page-header-acciones">
            <button className="btn btn-primary"   onClick={() => abrirCreacion('VENTA')}>+ Nueva venta</button>
            <button className="btn btn-devolucion" onClick={() => abrirCreacion('DEVOLUCION')}>↩ Nueva devolución</button>
            <button className="btn btn-egreso" onClick={() => abrirFormEgresos()}>Nuevo egreso</button>
          </div>
        )}
        {modo === 'creacion' && (
          <button className="btn btn-secondary" onClick={volverAListado} disabled={loadingConfirmar}>
            ← Volver
          </button>
        )}
      </div>

      {/* FORMULARIO EGRESO */}
      {modo === 'listado' && formEgresoAbierto &&  
        <div className="form-card">
          <div className='form-row'>
            <div className="form-group" style={{ maxWidth: 280 }}>
              <label>Local</label>
              <select value={localId ?? ''} onChange={e => setLocalId(parseInt(e.target.value))}>
                {locales.map(l => (
                  <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
                ))}
              </select>
            </div>

            {rol === 'admin' && 
            <div className='form-group'>
              <label>Vendedor</label>
              <select value={usuarioId ?? ''} onChange={e => setUsuarioId(parseInt(e.target.value))}>
                {usuarios.map(l => (
                  <option key={l.usuario_id} value={l.usuario_id}>{l.nombre}</option>
                ))}
              </select>
            </div>}

            <div className="form-group" style={{ maxWidth: 280 }}>
              <label>Monto:</label>
              <input
                type="number" min={1}
                value={montoEgreso}
                onChange={e => setMontoEgreso(e.target.value)}
                placeholder="$"
              />
            </div>

            <div className="form-group" style={{ maxWidth: 280 }}>
              <label>Descripcion:</label>
              <input
                type='text'
                value={descripcionEgreso}
                onChange={e => setDescripcionEgreso(e.target.value)}
                placeholder="$"
              />
            </div>
            
            <div className="form-actions">
              <button className="btn btn-secondary" onClick={handleConfirmarEgreso}>Confirmar</button>
              <button className="btn btn-primary"   onClick={cerrarFormEgresos}>Cancelar</button>
            </div>

          </div>
        </div>
      }

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.msg}</span>
          <button className="alerta-cerrar" onClick={cerrarAlerta}>✕</button>
        </div>
      )}
      {/* ══════════════════════════════════════════════════════════════════════
          MODO CREACIÓN
      ══════════════════════════════════════════════════════════════════════ */}
      {modo === 'creacion' && (
        <>
          {/* ── Local ── */}
          
          <div className="form-card">
            <div className='form-row'>
              <div className="form-group" style={{ maxWidth: 280 }}>
                <label>Local</label>
                <select value={localId ?? ''} onChange={e => setLocalId(parseInt(e.target.value))}>
                  {locales.map(l => (
                    <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
                  ))}
                </select>
              </div>

              {/* {Cuando el value del <select> no coincide con ninguna opción, el navegador:
                   selecciona automáticamente la primera opción disponible } */}
              {rol === 'admin' &&
              <div className='form-group'>
                <label>Vendedor</label>
                <select value={usuarioId ?? ''} onChange={e => setUsuarioId(parseInt(e.target.value))}>
                  {usuarios.map(l => (
                    <option key={l.usuario_id} value={l.usuario_id}>{l.nombre}</option>
                  ))}
                </select>
              </div>}

              {rol === 'admin' &&
              <div className='form-group' style={{ maxWidth: 180 }}>
                <label>Fecha de venta</label>
                <input
                  type="date"
                  value={fechaVenta}
                  max={hoyArgentina()}
                  onChange={e => setFechaVenta(e.target.value)}
                />
              </div>}
            </div>
          </div>
          

          {/* ── 3 Botones siempre visibles ── */}
          <div className="venta-agregar-btns">
            <button className="btn btn-secondary" onClick={formAccAbierto  ? cerrarFormAcc  : abrirFormAcc}>
              {formAccAbierto  ? '✕ Accesorio' : '+ Accesorio'}
            </button>
            <button className="btn btn-secondary" onClick={formCelAbierto  ? cerrarFormCel  : abrirFormCel}>
              {formCelAbierto  ? '✕ Celular'   : '+ Celular'}
            </button>
            <button className="btn btn-secondary" onClick={formChipAbierto ? cerrarFormChip : abrirFormChip}>
              {formChipAbierto ? '✕ Chip'      : '+ Chip'}
            </button>
          </div>

          {/* ── Formulario Accesorio ── */}
          {formAccAbierto && (
            <div className="form-card">
              <h3>Agregar accesorio</h3>
              <div className="form-row">
                <div className="form-group" style={{ flex: 2 }}>
                  <label>Accesorio *</label>
                  <SearchableSelect
                    options={options.accesoriosConStock}
                    value={formAccId}
                    onChange={handleSeleccionAcc}
                    onSearch={(t) => buscadorSelect('accesoriosConStock', t, { local_id: localId })}
                    placeholder="Buscar por nombre..."
                  />
                </div>
                {formAccData && (
                  <div className="form-group" style={{ maxWidth: 110 }}>
                    <label>Stock disponible</label>
                    <input type="text" readOnly value={formAccData.stock ?? 0} />
                  </div>
                )}
                <div className="form-group">
                  <label>Precio unitario *</label>
                  <input
                    type="number" min={1}
                    value={formAccPrecio}
                    onChange={e => setFormAccPrecio(e.target.value)}
                    placeholder="$"
                  />
                </div>
                <div className="form-group" style={{ maxWidth: 90 }}>
                  <label>Cantidad *</label>
                  <input
                    type="number" min={1}
                    value={formAccCantidad}
                    onChange={e => setFormAccCantidad(e.target.value)}
                  />
                </div>
              </div>
              <div className="form-actions">
                <button className="btn btn-secondary" onClick={cerrarFormAcc}>Cancelar</button>
                <button className="btn btn-primary"   onClick={handleAgregarAcc}>Agregar</button>
              </div>
            </div>
          )}

          {/* ── Formulario Celular ── */}
          {formCelAbierto && (
            <div className="form-card">
              <h3>Agregar celular</h3>
              <div className="form-row">
                <div className="form-group" style={{ flex: 2 }}>
                  <label>Celular (IMEI) *</label>
                  <SearchableSelect
                    options={options.celulares}
                    value={formCelId}
                    onChange={handleSeleccionCel}
                    onSearch={(t) => buscadorSelect('celulares', t, { estado: tipoOperacion === 'VENTA' ? 'DISPONIBLE' : 'VENDIDO' , local_id: localId })}
                    placeholder="Buscar por IMEI..."
                  />
                </div>
                <div className="form-group">
                  <label>Precio unitario *</label>
                  <input
                    type="number" min={1}
                    value={formCelPrecio}
                    onChange={e => setFormCelPrecio(e.target.value)}
                    placeholder="$"
                  />
                </div>
              </div>
              <div className="form-actions">
                <button className="btn btn-secondary" onClick={cerrarFormCel}>Cancelar</button>
                <button className="btn btn-primary"   onClick={handleAgregarCel}>Agregar</button>
              </div>
            </div>
          )}

          {/* ── Formulario Chip ── */}
          {formChipAbierto && (
            <div className="form-card">
              <h3>Agregar chip</h3>
              <div className="form-row">
                <div className="form-group" style={{ flex: 2 }}>
                  <label>Chip (N° de serie) *</label>
                  <SearchableSelect
                    options={options.chips}
                    value={formChipId}
                    onChange={handleSeleccionChip}
                    onSearch={(t) => buscadorSelect('chips', t,  {estado: tipoOperacion === 'VENTA' ? 'DISPONIBLE' : 'VENDIDO' , local_id: localId})}
                    placeholder="Buscar por número de serie..."
                  />
                </div>
                <div className="form-group">
                  <label>Precio unitario *</label>
                  <input
                    type="number" min={1}
                    value={formChipPrecio}
                    onChange={e => setFormChipPrecio(e.target.value)}
                    placeholder="$"
                  />
                </div>
              </div>
              <div className="form-actions">
                <button className="btn btn-secondary" onClick={cerrarFormChip}>Cancelar</button>
                <button className="btn btn-primary"   onClick={handleAgregarChip}>Agregar</button>
              </div>
            </div>
          )}

          {/* ── Tabla carrito ── */}
          {productos.length > 0 && (
            <div className="form-card">
              <h3>Productos</h3>
              <div className="table-wrapper">
                <table className="acc-table">
                  <thead>
                    <tr>
                      <th>Tipo</th>
                      <th>Producto</th>
                      <th>Cant.</th>
                      <th>Precio unit.</th>
                      <th>Subtotal</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {productos.map(p => (
                      <tr key={p._key}>
                        <td><span className={`tipo-badge tipo-${p.tipo}`}>{p.tipo === 'accesorio' ? 'acc' : p.tipo === 'celular' ? 'cel' : 'chip'}</span></td>
                        <td>{p.label}</td>
                        <td>
                          {p.tipo === 'accesorio' ? (
                            <input
                              className="input-carrito"
                              type="number"
                              min={1}
                              value={p.cantidad}
                              onChange={e => handleCantidadCarrito(p._key, e.target.value)}
                            />
                          ) : (
                            <span>1</span>
                          )}
                        </td>
                        <td>
                          <input
                            className="input-carrito"
                            type="number"
                            min={1}
                            value={p.precio_unitario}
                            onChange={e => handlePrecioCarrito(p._key, e.target.value)}
                          />
                        </td>
                        <td>{formatPrecio(p.precio_unitario * p.cantidad)}</td>
                        <td>
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={() => handleEliminar(p._key)}
                          >
                            Eliminar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Total */}
              <div className="venta-total">
                <span>Total</span>
                <strong>{formatPrecio(total)}</strong>
              </div>
            </div>
          )}

          {/* ── Medio de pago ── */}
          {productos.length > 0 && (
            <div className="form-card">
              <h3>Medio de pago</h3>
              <div className="form-row">
                <div className="form-group" style={{ maxWidth: 200 }}>
                  <label>Medio</label>
                  <select value={medioPago} onChange={e => setMedioPago(e.target.value)}>
                    <option value="efectivo">Efectivo</option>
                    <option value="electronico">Electrónico</option>
                    <option value="ambos">Ambos</option>
                  </select>
                </div>

                {medioPago === 'electronico' && (
                  <> 
                    <div className="form-group" style={{ maxWidth: 200 }}>
                      <label>Forma de pago</label>
                      <select value={medioPagoElectronico ?? ''} onChange={e => setMedioPagoElectronico(e.target.value)}>
                        <option value="" disabled>Seleccionar...</option>
                        <option value="QR">QR</option>
                        <option value="DEBITO">Débito</option>
                        <option value="TRANSFERENCIA">Transferencia</option>
                        <option value="CREDITO">Crédito</option>
                      </select>
                    </div>
                    <div className="form-group" style={{ maxWidth: 200 }}>
                      <label>Cuotas</label>
                      <select 
                        value={cuotas} 
                        onChange={e => setCuotas(Number(e.target.value))}
                      >
                        <option value={1}>1</option>
                        <option value={3}>3</option>
                        <option value={6}>6</option>
                        <option value={12}>12</option>
                      </select>
                    </div>
                  </>
                )}

                {medioPago === 'ambos' && (
                  <>
                    <div className="form-group">
                      <label>Monto efectivo</label>
                      <input
                        type="number"
                        min={0}
                        value={montoEfectivo}
                        onChange={e => setMontoEfectivo(e.target.value)}
                        placeholder="$"
                      />
                    </div>
                    <div className="form-group">
                      <label>Monto electrónico</label>
                      <input
                        type="number"
                        min={0}
                        value={montoElectronico}
                        onChange={e => setMontoElectronico(e.target.value)}
                        placeholder="$"
                      />
                    </div>
                    <div className="form-group" style={{ maxWidth: 200 }}>
                      <label>Forma de pago</label>
                      <select value={medioPagoElectronico ?? ''} onChange={e => setMedioPagoElectronico(e.target.value)}>
                        <option value="" disabled>Seleccionar...</option>
                        <option value="QR">QR</option>
                        <option value="DEBITO">Débito</option>
                        <option value="TRANSFERENCIA">Transferencia</option>
                        <option value="CREDITO">Crédito</option>
                      </select>
                    </div>
                    <div className="form-group" style={{ maxWidth: 200 }}>
                      <label>Cuotas </label>
                      <select value={cuotas} onChange={e => setCuotas(e.target.value)}>
                        <option value={1}>1</option>
                        <option value={3}>3</option>
                        <option value={6}>6</option>
                        <option value={12}>12</option>
                      </select>
                    </div>
                  </>
                )}
              </div>

              {/* Indicador de suma si es ambos */}
              {medioPago === 'ambos' && (
                (() => {
                  const ef = parseInt(montoEfectivo)  || 0
                  const el = parseInt(montoElectronico) || 0
                  const suma = ef + el
                  const ok = suma === total
                  return (
                    <p className={`venta-pago-hint ${ok ? 'hint-ok' : 'hint-error'}`}>
                      Suma de pagos: {formatPrecio(suma)} / Total: {formatPrecio(total)}
                      {ok ? ' ✓' : ' — no coincide'}
                    </p>
                  )
                })()
              )}

              <div className="form-actions" style={{ marginTop: 16 }}>
                <button
                  className="btn btn-primary"
                  onClick={handleConfirmar}
                  disabled={loadingConfirmar || productos.length === 0}
                >
                  {loadingConfirmar
                    ? 'Registrando...'
                    : tipoOperacion === 'VENTA' ? 'Confirmar venta' : 'Confirmar devolución'}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          MODO LISTADO
      ══════════════════════════════════════════════════════════════════════ */}
      {modo === 'listado' && (
        <>
          {loadingLista ? (
            <p className="empty-msg">Cargando...</p>
          ) : ventas.length === 0 ? (
            <p className="empty-msg">No hay ventas registradas.</p>
          ) : (
            <>
              <div className="table-wrapper">
                <table className="acc-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Fecha</th>
                      <th>Tipo</th>
                      <th>Pagos</th>
                      <th>Total</th>
                      <th>Detalles</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ventas.map(v => (
                      <tr key={v.venta_id} className={v.tipo === 'DEVOLUCION' ? 'row-devolucion' : ''}>
                        <td>{v.venta_id}</td>
                        <td>{formatFecha(v.fecha_ingreso)}</td>
                        <td>
                          <span className={`tipo-badge tipo-${v.tipo.toLowerCase()}`}>
                            {v.tipo}
                          </span>
                        </td>
                        <td className="venta-pagos-cell">
                          {v.pagos.map((p, i) => (
                            <span key={i} className="pago-badge">
                              {p.medio_de_pago}: {formatPrecio(p.importe)}
                            </span>
                          ))}
                        </td>
                        <td><strong>{formatPrecio(v.monto_total)}</strong></td>
                        <td><button 
                            className='btn-ver-detalle' 
                            onClick={() => abrirModal(v.venta_id)} 
                            disabled={loadingModal}
                          >
                            {loadingModal ? "Cargando..." : "Ver detalle"}
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

              {/* el modal, fuera de la tabla */}
              {modalAbierto && (
                <ModalDetalle
                  detalles={modalItem}
                  admin={rol === 'admin' ? true : false}
                  onClose={cerrarModal}
                />
              )}
            </>
          )}

          {/* ── Caja diaria ── */}
          <div className="caja-diaria-footer">
            <div className="form-group" style={{ maxWidth: 200 }}>
              <label>Local</label>
              <select value={localId ?? ''} onChange={e => setLocalId(parseInt(e.target.value))}>
                {locales.map(l => (
                  <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
                ))}
              </select>
            </div>
            {rol === 'admin' && (
              <div className="form-group" style={{ maxWidth: 200 }}>
                <label>Vendedor</label>
                <select value={usuarioId ?? ''} onChange={e => setUsuarioId(parseInt(e.target.value))}>
                  {usuarios.map(u => (
                    <option key={u.usuario_id} value={u.usuario_id}>{u.nombre}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="form-group" style={{ maxWidth: 180 }}>
              <label>Fecha</label>
              <input type="date" value={fechaCaja} onChange={e => setFechaCaja(e.target.value)} />
            </div>
            <div className="form-group" style={{ maxWidth: 130 }}>
              <label>Sobrante</label>
              <input
                type="number" min={0}
                value={sobrante}
                onChange={e => setSobrante(e.target.value)}
                placeholder="$"
                disabled={parseInt(faltante) > 0}
              />
            </div>
            <div className="form-group" style={{ maxWidth: 130 }}>
              <label>Faltante</label>
              <input
                type="number" min={0}
                value={faltante}
                onChange={e => setFaltante(e.target.value)}
                placeholder="$"
                disabled={parseInt(sobrante) > 0}
              />
            </div>
            <button
              className="btn btn-secondary"
              onClick={handleGuardarSF}
              disabled={loadingSF}
            >
              {loadingSF ? 'Guardando...' : 'Guardar sobrante/faltante'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={handleGenerarCajaDiaria}
              disabled={loadingCaja}
            >
              {loadingCaja ? 'Generando...' : 'Generar caja diaria'}
            </button>

          </div>
        </>
      )}
    </div>
  )
}