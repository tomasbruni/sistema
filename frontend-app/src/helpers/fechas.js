// Los usuarios operan en hora argentina: toda conversión instante → día se hace en esta zona,
// sin depender del huso horario configurado en la PC.
export const TZ_AR = 'America/Argentina/Buenos_Aires'

// Día 'YYYY-MM-DD' (en hora argentina) de un instante (ISO con zona o Date).
export const fechaAR = (instante) => new Date(instante).toLocaleDateString('en-CA', { timeZone: TZ_AR })

export const hoyAR = () => fechaAR(new Date())

// 'YYYY-MM-DD' → 'DD/MM/YYYY'
export const isoADmy = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : '')

// Máximo de días por mes (febrero con 29: el bisiesto se valida cuando está el año).
const DIAS_MES = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

// 'DD/MM/AAAA' → 'YYYY-MM-DD', o null si no es una fecha real. El año va siempre con 4 dígitos.
export const dmyAIso = (dmy) => {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(dmy || '')
  if (!m) return null
  const [dia, mes, anio] = [Number(m[1]), Number(m[2]), Number(m[3])]
  if (anio < 2000 || anio > 2099) return null
  // Date.UTC desborda los días inexistentes (29/02 de año no bisiesto → 01/03): si no vuelve igual, es inválida.
  const d = new Date(Date.UTC(anio, mes - 1, dia))
  if (d.getUTCFullYear() !== anio || d.getUTCMonth() !== mes - 1 || d.getUTCDate() !== dia) return null
  return `${m[3]}-${m[2]}-${m[1]}`
}

// ¿Los dígitos tipeados hasta ahora pueden ser el comienzo de una fecha dd/mm/aaaa válida?
const prefijoValido = (digitos) => {
  const [d1, d2, m1, m2] = [...digitos.slice(0, 4)].map(Number)
  if (digitos.length >= 1 && d1 > 3) return false
  if (digitos.length >= 2) {
    const dia = d1 * 10 + d2
    if (dia < 1 || dia > 31) return false
  }
  if (digitos.length >= 3 && m1 > 1) return false
  if (digitos.length >= 4) {
    const mes = m1 * 10 + m2
    if (mes < 1 || mes > 12) return false
    if (d1 * 10 + d2 > DIAS_MES[mes - 1]) return false
  }
  // Año 20xx
  if (digitos.length >= 5 && digitos[4] !== '2') return false
  if (digitos.length >= 6 && digitos[5] !== '0') return false
  return true
}

// Máscara dd/mm/aaaa: se tipean sólo los dígitos y las barras se agregan solas.
// La barra final se agrega sólo al escribir (el texto creció), así el Backspace la borra normalmente.
// Devuelve null si el dígito tipeado haría imposible la fecha (día > 31, mes > 12, 31/04...).
export const mascaraFecha = (texto, anterior = '') => {
  const digitos = texto.replace(/\D/g, '').slice(0, 8)
  if (!prefijoValido(digitos)) return null
  const creciendo = texto.length > anterior.length
  let out = digitos.slice(0, 2)
  if (digitos.length > 2 || (creciendo && digitos.length === 2)) out += '/'
  out += digitos.slice(2, 4)
  if (digitos.length > 4 || (creciendo && digitos.length === 4)) out += '/'
  out += digitos.slice(4)
  return out
}
