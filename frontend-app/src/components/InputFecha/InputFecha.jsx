import { useState } from 'react'
import { isoADmy, dmyAIso, mascaraFecha } from '../../helpers/fechas'

// Input de fecha tipeable en formato dd/mm/aaaa (año siempre con 4 dígitos).
// `value` y `onChange` trabajan en ISO 'YYYY-MM-DD' ('' mientras la fecha esté incompleta o sea inválida).
export default function InputFecha({ value, onChange, style, ...props }) {
  const [texto, setTexto] = useState(() => isoADmy(value))
  const [valorPrevio, setValorPrevio] = useState(value)

  // Cambio de `value` desde afuera (editar un gasto, resetear el form): mostramos esa fecha,
  // salvo que ya sea la que representa lo tipeado (no pisamos al usuario mientras escribe).
  if (value !== valorPrevio) {
    setValorPrevio(value)
    if ((dmyAIso(texto) || '') !== (value || '')) setTexto(isoADmy(value))
  }

  const handleChange = (e) => {
    const nuevo = mascaraFecha(e.target.value, texto)
    if (nuevo === null) return   // dígito imposible (día > 31, mes > 12...): se ignora
    setTexto(nuevo)
    onChange(dmyAIso(nuevo) || '')
  }

  const invalida = texto.replace(/\D/g, '').length === 8 && !dmyAIso(texto)

  return (
    <>
      <input
        type="text"
        inputMode="numeric"
        placeholder="dd/mm/aaaa"
        maxLength={10}
        value={texto}
        onChange={handleChange}
        style={invalida ? { ...style, borderColor: '#c0392b' } : style}
        title={invalida ? 'Fecha inválida' : undefined}
        {...props}
      />
      {invalida && <span style={{ fontSize: '0.8rem', color: '#c0392b' }}>Fecha inválida</span>}
    </>
  )
}
