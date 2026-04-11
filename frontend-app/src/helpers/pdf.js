import { api } from '../api/api'

const _descargar = async (blob, filename, onError) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export const descargarIngresoPdf = async (ingreso_lote_id, onError) => {
  try {
    const blob = await api.generarIngresoPdf(ingreso_lote_id)
    await _descargar(blob, `ingreso_${ingreso_lote_id}.pdf`)
  } catch (err) {
    onError?.(`Error al generar PDF: ${err.message}`)
  }
}

export const descargarIngresoChipsPdf = async (ingreso_lote_chip_id, onError) => {
  try {
    const blob = await api.generarIngresoChipsPdf(ingreso_lote_chip_id)
    await _descargar(blob, `ingreso_chips_${ingreso_lote_chip_id}.pdf`)
  } catch (err) {
    onError?.(`Error al generar PDF: ${err.message}`)
  }
}

export const descargarTransferenciaPdf = async (transferencia_id, onError) => {
  try {
    const blob = await api.generarTransferenciaPdf(transferencia_id)
    await _descargar(blob, `transferencia_${transferencia_id}.pdf`)
  } catch (err) {
    onError?.(`Error al generar PDF: ${err.message}`)
  }
}
