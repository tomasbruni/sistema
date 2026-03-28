import { useState } from "react" 

export const useModalDetalle = (fetchFn) => {
  // ── Modal de cada venta ─────────────────────────────────────────
  const [modalAbierto, setModalAbierto] = useState(false)
  const [modalItem, setModalItem] = useState(null)
  const [loadingModal, setLoadingModal] = useState(false)

  const abrirModal = async (venta_id) => {
    setLoadingModal(true)
    try {
      const detalles = await fetchFn(venta_id)
      setModalItem(detalles)
      setModalAbierto(true)
    } catch (err) {
      console.error(err)
    } finally {
      setLoadingModal(false)
    }
  }

  const cerrarModal = () => {
    setModalItem(null)
    setModalAbierto(false)
  }

  return {modalAbierto, setModalAbierto, modalItem, setModalItem, loadingModal, setLoadingModal, abrirModal, cerrarModal}
}