import { useState } from "react"
import { api } from "../api/api"

function useSelectOptions(names) {
  const initialState = Object.fromEntries(
    names.map(name => [name, []])
  )
  const [options, setOptions] = useState(initialState)

  const setOption = (name, value) => {
    setOptions(prev => ({ ...prev, [name]: value }))
  }

  const buscadorSelect = async (name, termino = "", extra = {}) => {
    const { tipo_id = null, estado = null, marca_celular_id = null, local_id = null } = extra
    let data = []

    if (name === "accesorios") {
      data = await api.listarAccesorios({ buscar: termino })
      setOption("accesorios", data.map(a => ({
        value: a.accesorio_id,
        label: `${a.nombre} — $${a.precio.toLocaleString('es-AR')}`,
        _raw: a,
      })))
    }
    else if (name === "tipos") {
      data = await api.listarTipos({ buscar: termino })
      setOption("tipos", data.map(t => ({ value: t.tipo_id, label: t.nombre })))
    }
    else if (name === "subtipos") {
      data = await api.listarSubtipos({ buscar: termino, tipo_id })
      setOption("subtipos", data.map(s => ({ value: s.subtipo_id, label: s.nombre })))
    }
    else if (name === "marcas") {
      data = await api.listarMarcas({ buscar: termino })
      setOption("marcas", data.map(m => ({ value: m.marca_id, label: m.nombre })))
    }
    // Marcas de celulares (tabla nueva)
    else if (name === "marcasCelulares") {
      data = await api.listarMarcasCelulares({ buscar: termino })
      setOption("marcasCelulares", data.map(m => ({ value: m.marca_celular_id, label: m.nombre })))
    }
    // Modelos filtrados por marca si se pasa marca_celular_id
    else if (name === "modelos") {
      data = await api.listarModelos({ buscar: termino, marca_celular_id })
      setOption("modelos", data.map(m => ({ value: m.modelo_celular_id, label: m.nombre })))
    }
    else if (name === "celulares") {
      data = await api.listarCelulares({ imei: termino, estado, local_id })
      setOption("celulares", data.map(c => ({
        value: c.celular_id,
        label: `IMEI: ${c.imei} — $${c.precio.toLocaleString('es-AR')}`,
        _raw: c,
      })))
    }
    else if (name === "chips") {
      data = await api.listarChips({ buscar: termino, estado })
      setOption("chips", data.map(c => ({
        value: c.chip_id,
        label: `${c.compania} — Serie: ${c.numero_serie} — $${c.precio.toLocaleString('es-AR')}`,
        _raw: c,
      })))
    }
  }

  return { options, setOption, buscadorSelect }
}

export default useSelectOptions