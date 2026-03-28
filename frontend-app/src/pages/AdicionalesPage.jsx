import { useState } from 'react'
import './AdicionalesPage.css'
import { useAlerta } from '../hooks/useAlerta'
import SeccionTipos from '../components/secciones/SeccionTipos'
import SeccionSubtipos from '../components/secciones/SeccionSubtipos'
import SeccionMarcas from '../components/secciones/SeccionMarcas'
import SeccionModelos from '../components/secciones/SeccionModelos'
import SeccionLocales from '../components/secciones/SeccionLocales'
import SeccionComisiones from '../components/secciones/SeccionComisiones'

const SECCIONES = [
  { key: 'tipos',    label: 'Tipos de accesorio' },
  { key: 'subtipos', label: 'Subtipos de accesorio' },
  { key: 'marcas',   label: 'Marcas' },
  { key: 'modelos',  label: 'Modelos de celular' },
  { key: 'locales',  label: 'Locales' }, 
  { key: 'comisiones', label: 'Comisiones' },
]

export default function AdicionalesPage() {
  const { alerta, mostrarAlerta } = useAlerta()
  const [seccion, setSeccion]     = useState('tipos')

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Adicionales</h2>
      </div>

      {alerta && <div className={`alerta alerta-${alerta.tipo}`}>{alerta.msg}</div>}

      <div className="adicionales-tabs">
        {SECCIONES.map(s => (
          <button
            key={s.key}
            className={`tab-btn ${seccion === s.key ? 'tab-btn-activo' : ''}`}
            onClick={() => setSeccion(s.key)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {seccion === 'tipos'    && <SeccionTipos    mostrarAlerta={mostrarAlerta} />}
      {seccion === 'subtipos' && <SeccionSubtipos mostrarAlerta={mostrarAlerta} />}
      {seccion === 'marcas'   && <SeccionMarcas   mostrarAlerta={mostrarAlerta} />}
      {seccion === 'modelos'  && <SeccionModelos  mostrarAlerta={mostrarAlerta} />}
      {seccion === 'locales'  && <SeccionLocales mostrarAlerta={mostrarAlerta} />}
      {seccion === 'comisiones' && <SeccionComisiones mostrarAlerta={mostrarAlerta} />}
    </div>
  )
}
