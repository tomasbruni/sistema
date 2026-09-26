import { useState, useEffect, useMemo } from 'react'
import { api, LIMIT } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import { descargarResponse } from '../helpers/descargar'
import './AccesoriosPage.css'
import './MovimientosPage.css'

const formatFecha = (fechaStr) => {
  if (!fechaStr) return '—'
  return new Date(fechaStr).toLocaleDateString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  })
}

const formatMonto = (monto) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', minimumFractionDigits: 2 }).format(monto || 0)

const num = (v) => (v === '' || v === null || v === undefined ? null : parseFloat(v))
// Sumas en centavos enteros para que la diferencia contra el total no arrastre errores de float.
const centavos = (v) => Math.round((num(v) || 0) * 100)

// Fecha local en formato YYYY-MM-DD (evita el corrimiento de día de toISOString, que usa UTC).
const isoLocal = (d) => {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
const inicioMesActual = () => { const d = new Date(); return isoLocal(new Date(d.getFullYear(), d.getMonth(), 1)) }
const hoyLocal = () => isoLocal(new Date())
// Meses en formato 'YYYY-MM' (se comparan bien como string).
const mesActual = () => hoyLocal().slice(0, 7)
const mesPasado = () => { const d = new Date(); return isoLocal(new Date(d.getFullYear(), d.getMonth() - 1, 1)).slice(0, 7) }
const mesDeFecha = (iso) => (iso ? isoLocal(new Date(iso)).slice(0, 7) : '')
const formatMes = (yyyymm) => (yyyymm ? `${yyyymm.slice(5, 7)}/${yyyymm.slice(0, 4)}` : '')

// Alícuotas de IVA: cada una con su neto y su IVA (autocalculado, editable).
// `principal`: se muestra en el formulario; el resto va en "Más conceptos".
const ALICUOTAS = [
  { key: '105', label: '10,5%', rate: 0.105 },
  { key: '21', label: '21%', rate: 0.21, principal: true },
  { key: '27', label: '27%', rate: 0.27 },
]
const calcIva = (neto, rate) => {
  const n = num(neto)
  if (n === null) return ''
  return (Math.round(n * rate * 100) / 100).toFixed(2)
}

// Columnas del libro IVA compras (el total del comprobante es la suma de todas).
const COLUMNAS_IMPORTE = [
  'neto_105', 'neto_21', 'neto_27', 'iva_105', 'iva_21', 'iva_27',
  'exento', 'percepcion_iva', 'percepcion_iibb_bsas', 'percepcion_iibb_caba',
  'otros_impuestos', 'no_gravado',
]
// Columna donde va el importe de una factura C (igual que COLUMNA_IMPORTE_C en el backend).
const COLUMNA_IMPORTE_C = 'no_gravado'

// Conceptos extra de la factura. `soloA`: no aplican a factura C (no discrimina IVA).
// `principal`: se muestra en el formulario; el resto va en "Más conceptos".
const OTROS_CONCEPTOS = [
  { key: 'percepcion_iibb_bsas', label: 'Percepción IIBB Bs As', principal: true },
  { key: 'percepcion_iibb_caba', label: 'Percepción IIBB Capital', principal: true },
  { key: 'otros_impuestos', label: 'Otros impuestos', ayuda: "incluye 'conceptos no gravados' de tickets de combustible", principal: true },
  { key: 'exento', label: 'Exento' },
  { key: 'no_gravado', label: 'No gravado', ayuda: 'no cargar acá lo que ya va en otros impuestos', soloA: true },
  { key: 'percepcion_iva', label: 'Percepción IVA', soloA: true },
]
// Campos que viven en el desplegable: si alguno tiene valor, se abre al editar.
const CAMPOS_DESPLEGABLE = [
  ...ALICUOTAS.filter(a => !a.principal).flatMap(a => [`neto_${a.key}`, `iva_${a.key}`]),
  ...OTROS_CONCEPTOS.filter(o => !o.principal).map(o => o.key),
]

const IMPORTES_VACIOS = Object.fromEntries(COLUMNAS_IMPORTE.map(c => [c, '']))
const IVA_MANUAL_VACIO = { '105': false, '21': false, '27': false }

const FORM_VACIO = {
  tipo: 'REAL',
  tipo_factura: 'A',
  proveedor_fiscal_id: '',
  punto_venta: '',
  numero_comprobante: '',
  comprada: false,
  porcentaje_real: '',
  total: '',
  ...IMPORTES_VACIOS,
  descripcion: '',
  fecha: '',     // factura: fecha de emisión
  periodo: '',   // factura: mes de imputación 'YYYY-MM'
}

const TOTALES_VACIO = { total_real: 0, total_blanco: 0, iva_a_favor: 0, percepciones_iibb: 0, cantidad: 0 }

// Campos de monto que se resetean al cambiar de tipo de gasto / factura,
// para no arrastrar valores de un tipo a otro.
const MONTOS_VACIOS = { total: '', ...IMPORTES_VACIOS, porcentaje_real: '', comprada: false }

const PROVEEDOR_VACIO = { razon_social: '', cuit: '' }

export default function GastosPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()

  const [gastos, setGastos] = useState([])
  const [totales, setTotales] = useState(TOTALES_VACIO)
  const [loading, setLoading] = useState(false)
  const [pagina, setPagina] = useState(0)
  const [hayMas, setHayMas] = useState(false)

  const [filtroTipo, setFiltroTipo] = useState(null)          // REAL | FACTURA
  const [filtroFactura, setFiltroFactura] = useState(null)    // A | C
  // Por defecto acotamos al mes actual: los totales siempre son de un período, nunca de toda la historia.
  const [fechaDesde, setFechaDesde] = useState(inicioMesActual())
  const [fechaHasta, setFechaHasta] = useState(hoyLocal())
  const [periodoLibro, setPeriodoLibro] = useState(mesActual())
  const [descargando, setDescargando] = useState(false)

  const [form, setForm] = useState(FORM_VACIO)
  const [ivaManual, setIvaManual] = useState(IVA_MANUAL_VACIO)  // el usuario editó el IVA de esa alícuota a mano
  const [verOtros, setVerOtros] = useState(false)
  const [periodoManual, setPeriodoManual] = useState(false)  // el usuario cambió el período a mano
  const [editando, setEditando] = useState(null)
  const [guardando, setGuardando] = useState(false)
  const [confirmBorrar, setConfirmBorrar] = useState(null)

  // Proveedores fiscales
  const [proveedores, setProveedores] = useState([])
  const [busquedaProv, setBusquedaProv] = useState('')
  const [listaProvAbierta, setListaProvAbierta] = useState(false)
  const [nuevoProv, setNuevoProv] = useState(null)   // null = cerrado | { razon_social, cuit }
  const [guardandoProv, setGuardandoProv] = useState(false)

  useEffect(() => {
    cargar(0, filtroTipo, filtroFactura, fechaDesde, fechaHasta)
    cargarProveedores()
  }, [])

  const cargarProveedores = async () => {
    try {
      setProveedores(await api.listarProveedoresFiscales({ limit: 500 }))
    } catch (e) {
      mostrarAlerta('error', e.message)
    }
  }

  const filtrosActuales = (tipo, factura, desde, hasta) => ({
    tipo: tipo || null,
    tipo_factura: factura || null,
    fecha_desde: desde || null,
    fecha_hasta: hasta || null,
  })

  const cargar = async (pag, tipo, factura, desde, hasta) => {
    setLoading(true)
    try {
      const filtros = filtrosActuales(tipo, factura, desde, hasta)
      const [data, tot] = await Promise.all([
        api.listarGastos({ offset: pag * LIMIT, limit: LIMIT + 1, ...filtros }),
        api.totalesGastos(filtros),
      ])
      setHayMas(data.length > LIMIT)
      setGastos(data.slice(0, LIMIT))
      setTotales(tot)
      setPagina(pag)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setLoading(false)
    }
  }

  const aplicarFiltros = () => cargar(0, filtroTipo, filtroFactura, fechaDesde, fechaHasta)

  const handleFiltroTipo = (tipo) => {
    const nuevo = filtroTipo === tipo ? null : tipo
    const nuevaFactura = tipo === 'FACTURA' ? filtroFactura : null
    setFiltroTipo(nuevo)
    setFiltroFactura(nuevaFactura)
    cargar(0, nuevo, nuevaFactura, fechaDesde, fechaHasta)
  }

  const handleFiltroFactura = (f) => {
    const nuevo = filtroFactura === f ? null : f
    setFiltroFactura(nuevo)
    setFiltroTipo('FACTURA')
    cargar(0, 'FACTURA', nuevo, fechaDesde, fechaHasta)
  }

  const descargarIvaCompras = async () => {
    if (!periodoLibro) {
      mostrarAlerta('warning', 'Elegí el período del libro')
      return
    }
    setDescargando(true)
    try {
      const res = await api.descargarIvaCompras({ periodo: periodoLibro })
      await descargarResponse(res, `iva_compras_${periodoLibro}.xlsx`)
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setDescargando(false)
    }
  }

  // ── Proveedor: búsqueda y alta inline ──
  const proveedorSel = proveedores.find(p => String(p.proveedor_fiscal_id) === String(form.proveedor_fiscal_id))
  const proveedoresFiltrados = useMemo(() => {
    const q = busquedaProv.trim().toLowerCase()
    const qDigitos = q.replace(/\D/g, '')
    if (!q) return proveedores.slice(0, 8)
    return proveedores.filter(p =>
      p.razon_social.toLowerCase().includes(q) ||
      (qDigitos && p.cuit.replace(/-/g, '').includes(qDigitos))
    ).slice(0, 8)
  }, [busquedaProv, proveedores])

  const elegirProveedor = (p) => {
    setForm(f => ({ ...f, proveedor_fiscal_id: p.proveedor_fiscal_id }))
    setBusquedaProv('')
    setListaProvAbierta(false)
  }

  const guardarNuevoProveedor = async () => {
    if (!nuevoProv.razon_social.trim() || !nuevoProv.cuit.trim()) {
      mostrarAlerta('warning', 'Completá razón social y CUIT')
      return
    }
    setGuardandoProv(true)
    try {
      let creado
      try {
        creado = await api.crearProveedorFiscal(nuevoProv)
      } catch (e) {
        // Hay comprobantes reales con CUIT mal tipeado: se puede guardar igual confirmando.
        if (!e.message.startsWith('CUIT_DIGITO_INVALIDO')) throw e
        if (!window.confirm('El dígito verificador del CUIT no coincide. ¿Guardarlo igual?')) return
        creado = await api.crearProveedorFiscal({ ...nuevoProv, forzar: true })
      }
      setProveedores(ps => [...ps, creado].sort((a, b) => a.razon_social.localeCompare(b.razon_social)))
      elegirProveedor(creado)
      setNuevoProv(null)
      mostrarAlerta('success', 'Proveedor creado')
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setGuardandoProv(false)
    }
  }

  const esFactura = form.tipo === 'FACTURA'
  const esFacturaA = esFactura && form.tipo_factura === 'A'
  const esFacturaC = esFactura && form.tipo_factura === 'C'

  // ── Preview en vivo: suma de columnas vs total impreso, y aportes ──
  const c = (k) => centavos(form[k])
  const sumaColumnas = COLUMNAS_IMPORTE.reduce((acc, k) => acc + c(k), 0)
  const totalDeclarado = centavos(form.total)
  const diferencia = totalDeclarado - sumaColumnas   // > 0: falta cargar algo | < 0: sobra
  const aporteBlanco = c('neto_105') + c('neto_21') + c('neto_27') + c('exento') + c('otros_impuestos') + c('no_gravado')
  const aporteIva = c('iva_105') + c('iva_21') + c('iva_27') + c('percepcion_iva')
  const aportePercIibb = c('percepcion_iibb_bsas') + c('percepcion_iibb_caba')
  const aporteReal = form.comprada ? Math.round(totalDeclarado * (num(form.porcentaje_real) || 0) / 100) : 0

  const setNeto = (key, rate, valor) => {
    setForm(f => ({
      ...f,
      [`neto_${key}`]: valor,
      [`iva_${key}`]: ivaManual[key] ? f[`iva_${key}`] : calcIva(valor, rate),
    }))
  }

  const construirPayload = () => {
    const base = {
      tipo: form.tipo,
      descripcion: form.descripcion.trim() || null,
      fecha: form.fecha || null,
      total: form.total || null,
    }
    if (form.tipo === 'REAL') return base

    const importes = Object.fromEntries(COLUMNAS_IMPORTE.map(k => [k, form[k] || '0']))
    return {
      ...base,
      tipo_factura: form.tipo_factura,
      periodo: form.periodo ? `${form.periodo}-01` : null,
      proveedor_fiscal_id: form.proveedor_fiscal_id || null,
      punto_venta: form.punto_venta.trim(),
      numero_comprobante: form.numero_comprobante.trim(),
      ...importes,
      comprada: esFacturaA && form.comprada,
      porcentaje_real: esFacturaA && form.comprada ? num(form.porcentaje_real) : null,
    }
  }

  const validar = () => {
    if (form.tipo === 'REAL') {
      if (!form.descripcion.trim()) return 'Completá la descripción'
      if (!num(form.total)) return 'Ingresá el total del gasto'
      return null
    }
    if (!form.proveedor_fiscal_id) return 'Elegí el proveedor'
    if (!form.punto_venta.trim() || !form.numero_comprobante.trim()) return 'Completá punto de venta y número de comprobante'
    if (!form.fecha) return 'Completá la fecha de emisión de la factura'
    if (!form.periodo) return 'Elegí el período de imputación'
    if (form.periodo < form.fecha.slice(0, 7)) return 'El período de imputación no puede ser anterior al mes de emisión'
    if (!num(form.total)) return 'Ingresá el total del comprobante tal como figura impreso'
    if (esFacturaA) {
      if (!ALICUOTAS.some(a => num(form[`neto_${a.key}`]))) return 'Ingresá al menos un neto gravado'
      if (form.comprada) {
        const p = num(form.porcentaje_real)
        if (p === null) return 'Ingresá el porcentaje real de la factura comprada'
        if (p < 0 || p > 100) return 'El porcentaje debe estar entre 0 y 100'
      }
    }
    // La diferencia contra el total la valida el backend (422 con el detalle).
    return null
  }

  const resetForm = (f) => {
    // Persistimos tipo de gasto y tipo de factura para cargar varios seguidos.
    setForm({ ...FORM_VACIO, tipo: f.tipo, tipo_factura: f.tipo_factura })
    setIvaManual(IVA_MANUAL_VACIO)
    setVerOtros(false)
    setPeriodoManual(false)
    setBusquedaProv('')
    setNuevoProv(null)
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
      const payload = construirPayload()
      if (editando !== null) {
        await api.actualizarGasto(editando, payload)
        mostrarAlerta('success', 'Gasto actualizado')
      } else {
        await api.crearGasto(payload)
        mostrarAlerta('success', 'Gasto registrado')
      }
      resetForm(form)
      setEditando(null)
      aplicarFiltros()
    } catch (e) {
      mostrarAlerta('error', e.message)
    } finally {
      setGuardando(false)
    }
  }

  const iniciarEdicion = (g) => {
    const str = (v) => (v != null && Number(v) !== 0 ? String(v) : '')
    setEditando(g.id)
    setForm({
      tipo: g.tipo,
      tipo_factura: g.tipo_factura || 'A',
      proveedor_fiscal_id: g.proveedor_fiscal_id || '',
      punto_venta: g.punto_venta || '',
      numero_comprobante: g.numero_comprobante || '',
      comprada: g.comprada,
      porcentaje_real: g.porcentaje_real != null ? String(g.porcentaje_real) : '',
      total: str(g.total),
      ...Object.fromEntries(COLUMNAS_IMPORTE.map(k => [k, str(g[k])])),
      descripcion: g.descripcion || '',
      fecha: g.fecha ? isoLocal(new Date(g.fecha)) : '',
      periodo: g.periodo ? g.periodo.slice(0, 7) : '',
    })
    // Si el período ya difería de la emisión, cambiar la fecha no lo arrastra.
    setPeriodoManual(!!g.periodo && g.periodo.slice(0, 7) !== mesDeFecha(g.fecha))
    setIvaManual({ '105': true, '21': true, '27': true })  // preservamos el IVA guardado, no lo recalculamos
    setVerOtros(CAMPOS_DESPLEGABLE.some(k => Number(g[k])))
    setNuevoProv(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const cancelarEdicion = () => {
    setEditando(null)
    resetForm(form)
  }

  const confirmarBorrar = async (id) => {
    try {
      await api.eliminarGasto(id)
      mostrarAlerta('success', 'Gasto eliminado')
      setConfirmBorrar(null)
      aplicarFiltros()
    } catch (e) {
      mostrarAlerta('error', e.message)
    }
  }

  const descripcionTipo = (g) => {
    if (g.tipo === 'REAL') return 'Real'
    if (g.tipo_factura === 'A') return g.comprada ? `Factura A comprada (${g.porcentaje_real}%)` : 'Factura A'
    return 'Factura C'
  }

  const inputMonto = (key, props = {}) => (
    <input
      type="number" step="0.01" min="0" placeholder="0.00"
      value={form[key]}
      onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
      {...props}
    />
  )

  const ayudaStyle = { color: '#888', fontWeight: 400 }

  const filaAlicuota = (a) => (
    <div className="form-row" key={a.key}>
      <div className="form-group">
        <label>Neto gravado {a.label} ($)</label>
        <input
          type="number" step="0.01" min="0" placeholder="0.00"
          value={form[`neto_${a.key}`]}
          onChange={e => setNeto(a.key, a.rate, e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>IVA {a.label} ($) <span style={ayudaStyle}>· auto, editable</span></label>
        <input
          type="number" step="0.01" min="0" placeholder="0.00"
          value={form[`iva_${a.key}`]}
          onChange={e => { setIvaManual(m => ({ ...m, [a.key]: true })); setForm(f => ({ ...f, [`iva_${a.key}`]: e.target.value })) }}
        />
      </div>
    </div>
  )

  const campoConcepto = (o) => (
    <div className="form-group" key={o.key} style={{ minWidth: 200 }}>
      <label>
        {o.label} ($)
        {o.ayuda && <span style={ayudaStyle}> · {o.ayuda}</span>}
      </label>
      {inputMonto(o.key)}
    </div>
  )

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Gastos</h2>
      </div>

      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.msg}</span>
          <button className="alerta-cerrar" onClick={cerrarAlerta}>&times;</button>
        </div>
      )}

      {/* ── Formulario ── */}
      <div className="form-card">
        <h3>{editando !== null ? 'Editar gasto' : 'Nuevo gasto'}</h3>
        <form className="acc-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label>Tipo de gasto</label>
              <select value={form.tipo} onChange={e => { setIvaManual(IVA_MANUAL_VACIO); setForm(f => ({ ...f, ...MONTOS_VACIOS, tipo: e.target.value })) }}>
                <option value="REAL">Real (plata que salió)</option>
                <option value="FACTURA">Factura (en blanco)</option>
              </select>
            </div>
            {esFactura && (
              <div className="form-group">
                <label>Tipo de factura</label>
                <select value={form.tipo_factura} onChange={e => { setIvaManual(IVA_MANUAL_VACIO); setForm(f => ({ ...f, ...MONTOS_VACIOS, tipo_factura: e.target.value })) }}>
                  <option value="A">Factura A</option>
                  <option value="C">Factura C</option>
                </select>
              </div>
            )}
          </div>

          {/* Gasto real: total */}
          {form.tipo === 'REAL' && (
            <div className="form-group">
              <label>Total ($)</label>
              {inputMonto('total')}
            </div>
          )}

          {/* ── Factura: datos del comprobante ── */}
          {esFactura && (
            <>
              <div className="form-row">
                <div className="form-group" style={{ flex: 2, position: 'relative' }}>
                  <label>Proveedor</label>
                  {proveedorSel && !listaProvAbierta ? (
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span style={{ flex: 1 }}>
                        <strong>{proveedorSel.razon_social}</strong>{' '}
                        <span style={{ color: '#666' }}>· CUIT {proveedorSel.cuit}</span>
                      </span>
                      <button type="button" className="btn btn-secondary" onClick={() => setListaProvAbierta(true)}>Cambiar</button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input
                        type="text"
                        style={{ flex: 1 }}
                        placeholder="Buscar por razón social o CUIT..."
                        value={busquedaProv}
                        onFocus={() => setListaProvAbierta(true)}
                        onChange={e => { setBusquedaProv(e.target.value); setListaProvAbierta(true) }}
                      />
                      <button
                        type="button" className="btn btn-secondary"
                        onClick={() => { setNuevoProv({ ...PROVEEDOR_VACIO, razon_social: busquedaProv }); setListaProvAbierta(false) }}
                      >
                        + Nuevo
                      </button>
                    </div>
                  )}
                  {listaProvAbierta && (
                    <div style={{
                      position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
                      background: '#fff', border: '1px solid #ddd', borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,.08)',
                    }}>
                      {proveedoresFiltrados.length === 0 ? (
                        <div style={{ padding: '8px 12px', color: '#888' }}>Sin resultados. Usá “+ Nuevo”.</div>
                      ) : proveedoresFiltrados.map(p => (
                        <div
                          key={p.proveedor_fiscal_id}
                          style={{ padding: '8px 12px', cursor: 'pointer' }}
                          onMouseDown={e => { e.preventDefault(); elegirProveedor(p) }}
                        >
                          {p.razon_social} <span style={{ color: '#888' }}>· {p.cuit}</span>
                        </div>
                      ))}
                      <div
                        style={{ padding: '6px 12px', textAlign: 'right', borderTop: '1px solid #eee', cursor: 'pointer', color: '#666' }}
                        onMouseDown={e => { e.preventDefault(); setListaProvAbierta(false) }}
                      >
                        Cerrar
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {nuevoProv && (
                <div className="form-row" style={{ alignItems: 'flex-end', background: '#f7f7fb', padding: 8, borderRadius: 6 }}>
                  <div className="form-group" style={{ flex: 2 }}>
                    <label>Razón social</label>
                    <input
                      type="text"
                      value={nuevoProv.razon_social}
                      onChange={e => setNuevoProv(p => ({ ...p, razon_social: e.target.value }))}
                    />
                  </div>
                  <div className="form-group">
                    <label>CUIT</label>
                    <input
                      type="text" placeholder="30-12345678-9"
                      value={nuevoProv.cuit}
                      onChange={e => setNuevoProv(p => ({ ...p, cuit: e.target.value }))}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
                    <button type="button" className="btn btn-primary" disabled={guardandoProv} onClick={guardarNuevoProveedor}>
                      {guardandoProv ? 'Guardando...' : 'Crear proveedor'}
                    </button>
                    <button type="button" className="btn btn-secondary" onClick={() => setNuevoProv(null)}>Cancelar</button>
                  </div>
                </div>
              )}

              <div className="form-row">
                <div className="form-group">
                  <label>Punto de venta</label>
                  <input
                    type="text" placeholder="Ej: 5382"
                    value={form.punto_venta}
                    onChange={e => setForm(f => ({ ...f, punto_venta: e.target.value }))}
                  />
                </div>
                <div className="form-group">
                  <label>N° de comprobante</label>
                  <input
                    type="text" placeholder="Ej: 2228"
                    value={form.numero_comprobante}
                    onChange={e => setForm(f => ({ ...f, numero_comprobante: e.target.value }))}
                  />
                </div>
                <div className="form-group">
                  <label>Fecha de emisión</label>
                  <input
                    type="date"
                    value={form.fecha}
                    onChange={e => {
                      const fecha = e.target.value
                      setForm(f => ({ ...f, fecha, periodo: periodoManual ? f.periodo : fecha.slice(0, 7) }))
                    }}
                  />
                </div>
                <div className="form-group">
                  <label>Período de imputación <span style={ayudaStyle}>· mes del libro IVA</span></label>
                  <input
                    type="month"
                    min={form.fecha ? form.fecha.slice(0, 7) : undefined}
                    value={form.periodo}
                    onChange={e => { setPeriodoManual(true); setForm(f => ({ ...f, periodo: e.target.value })) }}
                  />
                </div>
              </div>
              {form.periodo && form.periodo < mesPasado() && (
                <p style={{ fontSize: '0.85rem', color: '#a85a1a', margin: '0 0 4px' }}>
                  ⚠ ¿Ese período ya está presentado? Si es así, imputala al mes actual.
                </p>
              )}
            </>
          )}

          {/* Factura A: alícuota principal (21%) */}
          {esFacturaA && ALICUOTAS.filter(a => a.principal).map(filaAlicuota)}

          {/* Factura C: importe */}
          {esFacturaC && (
            <div className="form-group">
              <label>Importe ($) <span style={ayudaStyle}>· la factura C no discrimina IVA</span></label>
              {inputMonto(COLUMNA_IMPORTE_C)}
            </div>
          )}

          {esFactura && (
            <>
              {/* Percepciones IIBB y otros impuestos */}
              <div className="form-row" style={{ flexWrap: 'wrap' }}>
                {OTROS_CONCEPTOS.filter(o => o.principal).map(campoConcepto)}
              </div>

              {/* Más conceptos (colapsable): resto de alícuotas y conceptos poco usados */}
              <button
                type="button" className="btn btn-secondary" style={{ alignSelf: 'flex-start' }}
                onClick={() => setVerOtros(v => !v)}
              >
                {verOtros ? '▾' : '▸'} Más conceptos ({esFacturaA ? 'IVA 10,5% y 27%, exento, no gravado, percepción IVA' : 'exento'})
              </button>
              {verOtros && (
                <>
                  {esFacturaA && ALICUOTAS.filter(a => !a.principal).map(filaAlicuota)}
                  <div className="form-row" style={{ flexWrap: 'wrap' }}>
                    {OTROS_CONCEPTOS
                      .filter(o => !o.principal && !(o.soloA && esFacturaC))
                      .map(campoConcepto)}
                  </div>
                </>
              )}

              <div className="form-row" style={{ alignItems: 'center' }}>
                <div className="form-group">
                  <label>Total del comprobante ($) <span style={ayudaStyle}>· tal como figura impreso</span></label>
                  {inputMonto('total')}
                </div>
                {esFacturaA && (
                  <>
                    <div className="form-group" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                      <input
                        id="comprada" type="checkbox"
                        checked={form.comprada}
                        onChange={e => setForm(f => ({ ...f, comprada: e.target.checked }))}
                      />
                      <label htmlFor="comprada" style={{ margin: 0 }}>Factura comprada</label>
                    </div>
                    {form.comprada && (
                      <div className="form-group">
                        <label>% real sobre el total</label>
                        <input
                          type="number" step="1" min="0" max="100" placeholder="0"
                          value={form.porcentaje_real}
                          onChange={e => setForm(f => ({ ...f, porcentaje_real: e.target.value }))}
                        />
                      </div>
                    )}
                  </>
                )}
              </div>

              <p style={{ fontSize: '0.85rem', color: '#555', margin: '4px 0' }}>
                Suma de columnas: <strong>{formatMonto(sumaColumnas / 100)}</strong>
                {' · '}Total declarado: <strong>{formatMonto(totalDeclarado / 100)}</strong>
                {' · '}
                {form.total === '' ? (
                  <span style={{ color: '#888' }}>cargá el total para comparar</span>
                ) : diferencia === 0 ? (
                  <strong style={{ color: '#1e7e34' }}>✓ cierra</strong>
                ) : (
                  <strong style={{ color: '#c0392b' }}>
                    {diferencia > 0 ? 'falta' : 'sobra'} {formatMonto(Math.abs(diferencia) / 100)}
                  </strong>
                )}
              </p>
              <p style={{ fontSize: '0.85rem', color: '#555', margin: '4px 0' }}>
                Aporta a blanco: <strong>{formatMonto(aporteBlanco / 100)}</strong>
                {' · '}IVA a favor: <strong>{formatMonto(aporteIva / 100)}</strong>
                {aportePercIibb > 0 && <>{' · '}Percep. IIBB: <strong>{formatMonto(aportePercIibb / 100)}</strong></>}
                {form.comprada && esFacturaA && <>{' · '}Aporta a real: <strong>{formatMonto(aporteReal / 100)}</strong></>}
              </p>
            </>
          )}

          <div className="form-row">
            <div className="form-group" style={{ flex: 2 }}>
              <label>{esFactura ? 'Concepto (opcional)' : 'Descripción'}</label>
              <input
                type="text"
                placeholder={esFactura ? 'Ej: combustible, mercadería...' : 'Ej: alquiler, proveedor, servicios...'}
                value={form.descripcion}
                onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))}
              />
            </div>
            {!esFactura && (
              <div className="form-group">
                <label>Fecha</label>
                <input
                  type="date"
                  value={form.fecha}
                  onChange={e => setForm(f => ({ ...f, fecha: e.target.value }))}
                />
              </div>
            )}
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

      {/* ── Filtros ── */}
      <div className="filtros-row" style={{ marginBottom: 12, flexWrap: 'wrap' }}>
        {['REAL', 'FACTURA'].map(t => (
          <button
            key={t}
            className={`filtro-chip ${filtroTipo === t ? 'filtro-chip-activo' : ''}`}
            onClick={() => handleFiltroTipo(t)}
          >
            {t === 'REAL' ? 'Reales' : 'Facturas'}
          </button>
        ))}
        {['A', 'C'].map(f => (
          <button
            key={f}
            className={`filtro-chip ${filtroFactura === f ? 'filtro-chip-activo' : ''}`}
            onClick={() => handleFiltroFactura(f)}
          >
            Factura {f}
          </button>
        ))}
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
              const desde = inicioMesActual(), hasta = hoyLocal()
              setFechaDesde(desde); setFechaHasta(hasta); setFiltroTipo(null); setFiltroFactura(null)
              cargar(0, null, null, desde, hasta)
            }}
          >
            Mes actual
          </button>
        </div>
        <span style={{ fontSize: '0.8rem', color: '#888', alignSelf: 'center' }}>
          Las facturas se filtran por período de imputación; los gastos reales, por fecha.
        </span>
      </div>

      {/* ── Libro IVA compras (por mes de imputación) ── */}
      <div className="filtros-row" style={{ marginBottom: 12, alignItems: 'flex-end', gap: 8 }}>
        <div className="fecha-group">
          <span className="fecha-label">Libro IVA Compras</span>
          <input type="month" className="fecha-input" value={periodoLibro} onChange={e => setPeriodoLibro(e.target.value)} />
        </div>
        <button className="btn btn-primary" disabled={descargando} onClick={descargarIvaCompras}>
          {descargando ? 'Generando...' : 'Descargar IVA Compras'}
        </button>
      </div>

      {/* ── Totales (según filtros) ── */}
      <div className="filtros-row" style={{ marginBottom: 12, gap: 16, flexWrap: 'wrap' }}>
        <span className="tipo-badge" style={{ background: '#e6f4ea', color: '#1e7e34' }}>
          Total real: {formatMonto(totales.total_real)}
        </span>
        <span className="tipo-badge" style={{ background: '#e8eefc', color: '#1a3fa8' }}>
          Facturado en blanco: {formatMonto(totales.total_blanco)}
        </span>
        <span className="tipo-badge" style={{ background: '#fdf0e6', color: '#a85a1a' }}>
          IVA a favor: {formatMonto(totales.iva_a_favor)}
        </span>
        <span className="tipo-badge" style={{ background: '#f3e8fc', color: '#6a1aa8' }}>
          Percep. IIBB: {formatMonto(totales.percepciones_iibb)}
        </span>
        <span className="tipo-badge" style={{ background: '#e8e8f0', color: '#1a1a2e' }}>
          {totales.cantidad} gasto(s)
        </span>
      </div>

      {/* ── Tabla ── */}
      {loading ? (
        <p>Cargando...</p>
      ) : gastos.length === 0 ? (
        <p style={{ color: '#888' }}>Sin gastos.</p>
      ) : (
        <div className="table-wrapper">
          <table className="acc-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Fecha</th>
                <th>Tipo</th>
                <th>Proveedor</th>
                <th>Comprobante</th>
                <th>Total</th>
                <th>→ Real</th>
                <th>→ Blanco</th>
                <th>→ IVA</th>
                <th>Concepto</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {gastos.map(g => (
                <tr key={g.id}>
                  <td className="mov-id">{g.id}</td>
                  <td className="mov-fecha">
                    {formatFecha(g.fecha)}
                    {g.periodo && g.periodo.slice(0, 7) !== mesDeFecha(g.fecha) && (
                      <div>
                        <span className="tipo-badge" style={{ background: '#fdf0e6', color: '#a85a1a', fontSize: '0.75rem' }}>
                          imputada {formatMes(g.periodo.slice(0, 7))}
                        </span>
                      </div>
                    )}
                  </td>
                  <td><span className="tipo-badge">{descripcionTipo(g)}</span></td>
                  <td>
                    {g.proveedor_razon_social ? (
                      <>
                        {g.proveedor_razon_social}
                        <div style={{ fontSize: '0.8rem', color: '#888' }}>{g.proveedor_cuit}</div>
                      </>
                    ) : '—'}
                  </td>
                  <td>{g.numero_comprobante ? `${g.punto_venta}-${g.numero_comprobante}` : '—'}</td>
                  <td className="cantidad-mov">{formatMonto(g.total)}</td>
                  <td className="cantidad-mov">{Number(g.aporte_real) ? formatMonto(g.aporte_real) : '—'}</td>
                  <td className="cantidad-mov">{Number(g.aporte_blanco) ? formatMonto(g.aporte_blanco) : '—'}</td>
                  <td className="cantidad-mov">{Number(g.aporte_iva) ? formatMonto(g.aporte_iva) : '—'}</td>
                  <td className="mov-motivo" title={g.descripcion || ''}>{g.descripcion || '—'}</td>
                  <td>
                    {confirmBorrar === g.id ? (
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <button className="btn btn-danger" onClick={() => confirmarBorrar(g.id)}>Confirmar</button>
                        <button className="btn btn-secondary" onClick={() => setConfirmBorrar(null)}>No</button>
                      </span>
                    ) : (
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <button className="btn btn-secondary" onClick={() => iniciarEdicion(g)}>Editar</button>
                        <button className="btn btn-danger" onClick={() => setConfirmBorrar(g.id)}>Borrar</button>
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
        <button className="btn btn-secondary" disabled={pagina === 0} onClick={() => cargar(pagina - 1, filtroTipo, filtroFactura, fechaDesde, fechaHasta)}>
          Anterior
        </button>
        <span style={{ margin: '0 12px', fontSize: '0.9rem', color: '#555' }}>Pág. {pagina + 1}</span>
        <button className="btn btn-secondary" disabled={!hayMas} onClick={() => cargar(pagina + 1, filtroTipo, filtroFactura, fechaDesde, fechaHasta)}>
          Siguiente
        </button>
      </div>
    </div>
  )
}
