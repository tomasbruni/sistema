import { useState } from "react"
import { api } from "../api/api"

function useSelectOptions(names) {

  const initialState = Object.fromEntries(
    names.map(name => [name, []])
  )

  const [options, setOptions] = useState(initialState)

  const setOption = (name, value) => {
    setOptions(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const buscadorSelect = async (name, termino = "", tipo_id = null, estado = null) => {
    let data = []

    if (name === "accesorios") {
      data = await api.listarAccesorios({ buscar: termino })
      setOption(
        "accesorios",
        data.map(a => ({
          value: a.accesorio_id,
          label: `${a.nombre} — $${a.precio.toLocaleString('es-AR')}`,
          _raw:  a, // necesario para el precio
        }))
      )
    }

    else if (name === "tipos") {
      data = await api.listarTipos({ buscar: termino })
      setOption(
        "tipos",
        data.map(t => ({ value: t.tipo_id, label: t.nombre }))
      )
    }

    else if (name === "subtipos") {
      data = await api.listarSubtipos({ buscar: termino, tipo_id })
      setOption(
        "subtipos",
        data.map(s => ({ value: s.subtipo_id, label: s.nombre }))
      )
    }

    else if (name === "marcas") {
      data = await api.listarMarcas({ buscar: termino })
      setOption(
        "marcas",
        data.map(m => ({ value: m.marca_id, label: m.nombre }))
      )
    }

    else if (name === "modelos") {
      data = await api.listarModelos({ buscar: termino })
      setOption(
        "modelos",
        data.map(m => ({ value: m.modelo_id, label: `${m.marca} ${m.modelo}` }))
      )
    }

    else if (name === "celulares") {
      data = await api.listarCelulares({ imei: termino, estado })
      setOption(
        "celulares",
        data.map(c => ({
          value: c.celular_id,
          label: `IMEI: ${c.imei} — $${c.precio.toLocaleString('es-AR')}`,
          _raw:  c,// necesario para el precio
        }))
      )
    }

    else if (name === "chips") {
      data = await api.listarChips({ buscar: termino, estado })
      setOption(
        "chips",
        data.map(c => ({
          value: c.chip_id,
          label: `${c.compania} — Serie: ${c.numero_serie} — $${c.precio.toLocaleString('es-AR')}`,
          _raw:  c,
        }))
      )
    }
  }

  return { options, setOption, buscadorSelect }
}

export default useSelectOptions