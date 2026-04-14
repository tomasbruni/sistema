import { useState, useEffect } from 'react'
import { api } from '../api/api'
import { useAlerta } from '../hooks/useAlerta'
import useSelectOptions from '../hooks/useSelectOptions'
import SearchableSelect from '../components/SearchableSelect/SearchableSelect'
import './AccesoriosPage.css'
import './ImportarExcelPage.css'

export default function ImportarExcelPage() {
  const { alerta, mostrarAlerta, cerrarAlerta } = useAlerta()
  const { options, buscadorSelect } = useSelectOptions(['tipos'])

  // ── Datos de selects simples ──────────────────────────────────────────────
  const [locales,  setLocales]  = useState([])
  const [usuarios, setUsuarios] = useState([])

  // ── Subtipos del tipo elegido, para los inputs de precio ─────────────────
  const [subtipos, setSubtipos] = useState([])

  // ── Campos del formulario ─────────────────────────────────────────────────
  const [archivo,       setArchivo]       = useState(null)
  const [tipoId,        setTipoId]        = useState(null)
  const [localId,       setLocalId]       = useState('')
  const [receptorId,    setReceptorId]    = useState('')
  const [observaciones, setObservaciones] = useState('')
  // { [NOMBRE_SUBTIPO]: precio_string }
  const [precios, setPrecios] = useState({})

  // ── Estado de la operación ────────────────────────────────────────────────
  const [loading,   setLoading]   = useState(false)
  const [resultado, setResultado] = useState(null)

  // ── Carga inicial ─────────────────────────────────────────────────────────
  useEffect(() => {
    buscadorSelect('tipos', '')
    api.listarLocales().then(setLocales).catch(() => {})
    api.listarUsuarios().then(setUsuarios).catch(() => {})
  }, [])

  // ── Cuando cambia el tipo, cargar subtipos y resetear precios ─────────────
  useEffect(() => {
    if (!tipoId) {
      setSubtipos([])
      setPrecios({})
      return
    }
    api.listarSubtipos({ tipo_id: tipoId })
      .then(data => {
        setSubtipos(data)
        // Un input vacío por cada subtipo; el usuario solo completa los que usa
        const init = {}
        data.forEach(s => { init[s.nombre.toUpperCase()] = '' })
        setPrecios(init)
      })
      .catch(() => mostrarAlerta('error', 'No se pudieron cargar los subtipos'))
  }, [tipoId])

  const handlePrecio = (nombre, valor) => {
    setPrecios(prev => ({ ...prev, [nombre]: valor }))
  }

  // ── Validación ────────────────────────────────────────────────────────────
  const validar = () => {
    if (!archivo)    return 'Seleccioná un archivo'
    if (!tipoId)     return 'Seleccioná un tipo de accesorio'
    if (!localId)    return 'Seleccioná un local'
    if (!receptorId) return 'Seleccioná un receptor'

    const algunPrecio = Object.values(precios).some(v => v !== '')
    if (!algunPrecio) return 'Ingresá al menos un precio'

    const invalido = Object.entries(precios).find(
      ([, v]) => v !== '' && (isNaN(Number(v)) || Number(v) <= 0)
    )
    if (invalido) return `Precio inválido en "${invalido[0]}"`

    return null
  }

  // ── Envío ─────────────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault()
    const error = validar()
    if (error) { mostrarAlerta('error', error); return }

    // Solo pasar al backend los subtipos que tienen precio cargado
    const preciosJson = JSON.stringify(
      Object.fromEntries(
        Object.entries(precios)
          .filter(([, v]) => v !== '')
          .map(([k, v]) => [k, Number(v)])
      )
    )

    const form = new FormData()
    form.append('archivo',       archivo)
    form.append('tipo_id',       tipoId)
    form.append('local_id',      localId)
    form.append('receptor_id',   receptorId)
    form.append('precios',       preciosJson)
    form.append('observaciones', observaciones)

    setLoading(true)
    setResultado(null)
    try {
      const data = await api.importarExcel(form)
      setResultado(data)
      if (data.errores?.length > 0) {
        mostrarAlerta('warning', `Completado con ${data.errores.length} error(es)`)
      } else {
        mostrarAlerta('success', 'Importación exitosa')
      }
    } catch (err) {
      mostrarAlerta('error', err.message)
    } finally {
      setLoading(false)
    }
  }

  const descargarReporte = () => {
    const lineas = [
      `REPORTE DE IMPORTACIÓN`,
      `Fecha: ${new Date().toLocaleString('es-AR')}`,
      `Archivo: ${archivo?.name ?? '—'}`,
      ``,
      `── RESUMEN ──────────────────────────────────────`,
      `Marcas creadas:           ${resultado.marcas_creadas}`,
      `Marcas existentes:        ${resultado.marcas_existentes}`,
      `Modelos creados:          ${resultado.modelos_creados}`,
      `Modelos existentes:       ${resultado.modelos_existentes}`,
      `Accesorios creados:       ${resultado.accesorios_creados}`,
      `Accesorios omitidos:      ${resultado.accesorios_omitidos}`,
      `Combinaciones esperadas:  ${resultado.combinaciones_esperadas}`,
      `Combinaciones procesadas: ${resultado.accesorios_creados + resultado.accesorios_omitidos}`,
      `Lote de ingreso:          ${resultado.ingreso_lote_id ? `#${resultado.ingreso_lote_id}` : '—'}`,
      `Ítems ingresados:         ${resultado.items_ingresados}`,
      `Unidades totales:         ${resultado.unidades_totales}`,
    ]

    if (resultado.advertencias?.length > 0) {
      lineas.push(``, `── ADVERTENCIAS (${resultado.advertencias.length}) ─────────────────────`)
      resultado.advertencias.forEach(a => lineas.push(`  - ${a}`))
    }

    if (resultado.errores?.length > 0) {
      lineas.push(``, `── ERRORES (${resultado.errores.length}) ──────────────────────────────`)
      resultado.errores.forEach(e => lineas.push(`  - ${e.fila}: ${e.motivo}`))
    }

    const blob = new Blob([lineas.join('\n')], { type: 'text/plain;charset=utf-8' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `importacion_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="page-container" style={{ position: 'relative' }}>

      {/* Overlay que bloquea la página mientras se importa */}
      {loading && (
        <div className="importar-overlay">
          <div className="importar-spinner-box">
            <div className="importar-spinner" />
            <p>Importando, por favor esperá...</p>
          </div>
        </div>
      )}
      {alerta && (
        <div className={`alerta alerta-${alerta.tipo}`}>
          <span>{alerta.msg}</span>
          <button className="alerta-cerrar" onClick={cerrarAlerta}>✕</button>
        </div>
      )}

      <div className="page-header">
        <h2>Importar accesorios desde Excel / ODS</h2>
      </div>

      {/* ── Formulario ─────────────────────────────────────────────────────── */}
      <div className="form-card">
        <form className="acc-form" onSubmit={handleSubmit}>

          {/* Archivo */}
          <div className="form-group">
            <label>Archivo (.xlsx o .ods)</label>
            <input
              type="file"
              accept=".xlsx,.xls,.ods"
              onChange={e => setArchivo(e.target.files[0] || null)}
            />
            <span className="campo-ayuda">
              Columnas requeridas: <strong>MARCA</strong>, <strong>MODELO</strong>
              {' '}y una columna por subtipo con la cantidad de stock.
            </span>
          </div>

          <div className="form-row">
            {/* Tipo — SearchableSelect */}
            <div className="form-group">
              <label>Tipo de accesorio</label>
              <SearchableSelect
                options={options.tipos}
                value={tipoId}
                onChange={setTipoId}
                onSearch={t => buscadorSelect('tipos', t)}
                placeholder="Buscar tipo..."
              />
            </div>

            {/* Local — select normal */}
            <div className="form-group">
              <label>Local de ingreso</label>
              <select value={localId} onChange={e => setLocalId(e.target.value)}>
                <option value="">— Seleccioná —</option>
                {locales.map(l => (
                  <option key={l.local_id} value={l.local_id}>{l.nombre}</option>
                ))}
              </select>
            </div>

            {/* Receptor — select normal */}
            <div className="form-group">
              <label>Receptor</label>
              <select value={receptorId} onChange={e => setReceptorId(e.target.value)}>
                <option value="">— Seleccioná —</option>
                {usuarios.map(u => (
                  <option key={u.usuario_id} value={u.usuario_id}>{u.nombre}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Observaciones */}
          <div className="form-group">
            <label>Observaciones (opcional)</label>
            <input
              type="text"
              value={observaciones}
              onChange={e => setObservaciones(e.target.value)}
              placeholder="Ej: Ingreso inicial temporada 2026"
            />
          </div>

          {/* Precios por subtipo — aparecen al elegir el tipo */}
          {subtipos.length > 0 && (
            <div className="precios-card">
              <p className="precios-titulo">
                Precio por subtipo — completar solo los que estén en el archivo
              </p>
              <div className="precios-grid">
                {subtipos.map(s => {
                  const nombre = s.nombre.toUpperCase()
                  return (
                    <div className="form-group" key={s.subtipo_id}>
                      <label>{s.nombre}</label>
                      <input
                        type="number"
                        min="0"
                        placeholder="Precio $"
                        value={precios[nombre] ?? ''}
                        onChange={e => handlePrecio(nombre, e.target.value)}
                      />
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Importando...' : 'Importar'}
            </button>
          </div>
        </form>
      </div>

      {/* ── Resultado ──────────────────────────────────────────────────────── */}
      {resultado && (
        <div className="form-card">
          <div className="resultado-header">
            <h3>Resultado</h3>
            <button className="btn btn-secondary btn-sm" onClick={descargarReporte}>
              ⬇ Descargar reporte
            </button>
          </div>

          <div className="resultado-grid">
            <ResultadoFila label="Marcas creadas"      valor={resultado.marcas_creadas}      variante="ok" />
            <ResultadoFila label="Marcas existentes"   valor={resultado.marcas_existentes}   variante="gris" />
            <ResultadoFila label="Modelos creados"     valor={resultado.modelos_creados}     variante="ok" />
            <ResultadoFila label="Modelos existentes"  valor={resultado.modelos_existentes}  variante="gris" />
            <ResultadoFila label="Accesorios creados"  valor={resultado.accesorios_creados}  variante="ok" />
            <ResultadoFila label="Accesorios omitidos" valor={resultado.accesorios_omitidos} variante="gris" />
            <ResultadoFila
              label="Lote de ingreso"
              valor={resultado.ingreso_lote_id ? `#${resultado.ingreso_lote_id}` : '—'}
            />
            <ResultadoFila label="Ítems ingresados"   valor={resultado.items_ingresados}  variante="ok" />
            <ResultadoFila label="Unidades totales"   valor={resultado.unidades_totales}  variante="ok" />
          </div>

          {/* Verificación: combinaciones procesadas vs esperadas */}
          {(() => {
            const procesadas = resultado.accesorios_creados + resultado.accesorios_omitidos
            const esperadas  = resultado.combinaciones_esperadas
            const ok         = procesadas === esperadas
            return (
              <div className={`verificacion-banner ${ok ? 'verificacion-ok' : 'verificacion-error'}`}>
                {ok
                  ? `✓ Todas las combinaciones procesadas (${procesadas} / ${esperadas})`
                  : `⚠ Solo se procesaron ${procesadas} de ${esperadas} combinaciones esperadas — revisá los errores`
                }
              </div>
            )
          })()}

          {/* Advertencias sobre columnas ignoradas */}
          {resultado.advertencias?.length > 0 && (
            <div className="advertencias-lista">
              <p className="advertencias-titulo">Advertencias ({resultado.advertencias.length})</p>
              <ul>
                {resultado.advertencias.map((adv, i) => (
                  <li key={i}>{adv}</li>
                ))}
              </ul>
            </div>
          )}

          {resultado.errores?.length > 0 && (
            <div className="errores-lista">
              <p className="errores-titulo">Errores ({resultado.errores.length})</p>
              <ul>
                {resultado.errores.map((err, i) => (
                  <li key={i}><strong>{err.fila}</strong>: {err.motivo}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Componente auxiliar para cada fila del resumen ────────────────────────────
function ResultadoFila({ label, valor, variante }) {
  return (
    <div className="resultado-fila">
      <span className="resultado-label">{label}</span>
      <span className={`resultado-valor ${variante ? `resultado-${variante}` : ''}`}>
        {valor}
      </span>
    </div>
  )
}
