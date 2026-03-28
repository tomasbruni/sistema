import { useState, useEffect, useRef } from 'react';
import './SearchableSelect.css'

// ─── SEARCHABLE SELECT ───────────────────────────────────────────────────────
// Props:
//   options     → [{ value, label }]
//   value       → id seleccionado (number | null)
//   onChange    → fn(value: number | null)
//   onSearch    → fn(termino: string) — dispara búsqueda server-side con debounce
//   placeholder → string
//   disabled    → boolean
//
// Teclado soportado:
//   ArrowDown / ArrowUp → navegar opciones
//   Enter               → confirmar opción resaltada
//   Escape              → cerrar y restaurar valor previo
//   Tab                 → confirmar opción resaltada si hay una, sino cierra
export default function SearchableSelect({ options, value, onChange, onSearch, placeholder = 'Buscar...', disabled = false }) {
  const [inputVal, setInputVal]   = useState('')
  const [abierto, setAbierto]     = useState(false)
  const [indiceActivo, setIndiceActivo] = useState(-1)
  const debounceRef               = useRef(null)
  const wrapperRef                = useRef(null)
  const listRef                   = useRef(null)

  //restaurar es redundante
  const cerrar = ({ restaurar = false } = {}) => {
    setAbierto(false)
    setIndiceActivo(-1)
    if (restaurar) {
      if (value != null && value !== '') {
        const encontrada = options.find(o => String(o.value) === String(value))
        setInputVal(encontrada ? encontrada.label : '')
      } else {
        setInputVal('')
      }
    }
  }
  
  // Cuando cambia el value desde afuera (ej: abrir edición), sincronizar el label
  // osea cuando selecciono tambien,
  useEffect(() => {
    if (value == null || value === '') {
      setInputVal('')
      return
    } // si no es null, busco el label
    const encontrada = options.find(o => String(o.value) === String(value))
    if (encontrada) setInputVal(encontrada.label)
  }, [value])

  // Cerrar al hacer click fuera
  useEffect(() => {
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        cerrar({ restaurar: true })
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [value, options])

  // Cuando cambia el índice activo, hacer scroll al ítem para que sea visible
  useEffect(() => {
    if (!listRef.current || indiceActivo < 0) return
    const item = listRef.current.querySelectorAll('.ss-option')[indiceActivo]
    item?.scrollIntoView({ block: 'nearest' })
  }, [indiceActivo])

  // ── Helpers ────────────────────────────────────────────────────────────────


  const confirmarIndice = (idx) => {
    const opcion = options[idx]
    if (!opcion) return
    setInputVal(opcion.label)
    onChange(opcion.value) // siempre con opcion.value, que es el id
    setAbierto(false)
    setIndiceActivo(-1)
  }

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleInput = (e) => {
    const val = e.target.value
    setInputVal(val)
    setAbierto(true)
    setIndiceActivo(-1)
    if (!val.trim()) onChange(null)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => onSearch(val), 350)
  }

  const handleFocus = () => {
    setAbierto(true)
    if (!inputVal.trim()) onSearch('')
  }

  const handleSelect = (opcion) => {
    setInputVal(opcion.label)
    onChange(opcion.value)
    setAbierto(false)
    setIndiceActivo(-1)
  }

  const handleKeyDown = (e) => {
    if (!abierto) {
      // Abrir el dropdown con cualquier tecla de navegación
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        setAbierto(true)
        setIndiceActivo(0)
        e.preventDefault()
      }
      return
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setIndiceActivo(prev => (prev + 1) % options.length)
        break

      case 'ArrowUp':
        e.preventDefault()
        setIndiceActivo(prev => (prev <= 0 ? options.length - 1 : prev - 1))
        break

      case 'Enter':
        e.preventDefault()
        if (indiceActivo >= 0) {
          confirmarIndice(indiceActivo)
        }
        break

      case 'Tab':
        // Si hay una opción resaltada, confirmarla antes de saltar al siguiente campo
        if (indiceActivo >= 0) {
          e.preventDefault()
          confirmarIndice(indiceActivo)
        } else {
          // Sin opción resaltada, simplemente cerrar y dejar que Tab navegue
          cerrar({ restaurar: true })
        }
        break

      case 'Escape':
        e.preventDefault()
        cerrar({ restaurar: true })
        break
    }
  }

  return (
    <div className="ss-wrapper" ref={wrapperRef}>
      <input
        className="ss-input"
        type="text"
        value={inputVal}
        onChange={handleInput}
        onFocus={handleFocus}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        aria-expanded={abierto}
        aria-autocomplete="list"
      />
      {abierto && !disabled && (
        <ul className="ss-dropdown" ref={listRef} role="listbox">
          {options.length === 0 ? (
            <li className="ss-empty">Sin resultados</li>
          ) : (
            options.map((o, idx) => (
              <li
                key={o.value}
                role="option"
                aria-selected={String(o.value) === String(value)}
                className={[
                  'ss-option',
                  String(o.value) === String(value) ? 'ss-option-selected' : '',
                  idx === indiceActivo ? 'ss-option-activo' : '',
                ].join(' ').trim()}
                onMouseDown={() => handleSelect(o)}
                onMouseEnter={() => setIndiceActivo(idx)}
              >
                {o.label}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}