// Descarga un archivo a partir de la Response cruda de authFetch.
// Toma el nombre del header Content-Disposition; si no viene, usa `fallback`.
export const descargarResponse = async (res, fallback) => {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Error ${res.status}`)
  }
  const blob = await res.blob()
  const cd   = res.headers.get('Content-Disposition') ?? ''
  const url  = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href     = url
  link.download = cd.match(/filename="?([^"]+)"?/)?.[1] ?? fallback
  link.click()
  URL.revokeObjectURL(url)
}
