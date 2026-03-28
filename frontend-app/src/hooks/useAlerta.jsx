import { useState } from "react"

export const useAlerta = () => {
  const [alerta, setAlerta] = useState(null)

  const mostrarAlerta = (tipo, msg) => {
    setAlerta({ tipo, msg })
  }

  const cerrarAlerta = () => setAlerta(null)

  return { alerta, mostrarAlerta, cerrarAlerta }
}