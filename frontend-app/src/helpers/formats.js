export const formatPrecio = (n) => `$${Number(n).toLocaleString('es-AR')}`

export const formatFecha = (iso) =>
  new Date(iso).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
