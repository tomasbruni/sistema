import { useState, useRef, useCallback } from 'react'

/**
 * Hook genérico para secciones CRUD simples.
 *
 * @param {Function} fetchFn     - async (termino: string) => array de items
 * @param {Object}   formInicial - estado inicial del formulario
 */
export default function useCrudSeccion(fetchFn, formInicial) {
  // maneja el formulario y los items q se muestran segun busqueda
  const [items, setItems]               = useState([])
  const [loading, setLoading]           = useState(false)
  const [form, setForm]                 = useState(formInicial)
  const [editandoId, setEditandoId]     = useState(null)
  const [mostrarForm, setMostrarForm]   = useState(false)
  const [busqueda, setBusqueda]         = useState('')
  const debounceRef                     = useRef(null)

  const fetchItems = useCallback(async (termino = '') => {
    setLoading(true)
    try {
      const data = await fetchFn(termino)
      setItems(data)
    } finally {
      setLoading(false)
    }
  }, [fetchFn])

  const handleBusqueda = (e) => {
    const val = e.target.value
    setBusqueda(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => fetchItems(val), 400)
  }

  const abrirCrear = () => {
    setForm(formInicial)
    setEditandoId(null)
    setMostrarForm(true)
  }

  const abrirEditar = (id, datosForm) => {
    setForm(datosForm)
    setEditandoId(id)
    setMostrarForm(true)
  }

  const cancelar = () => {
    setMostrarForm(false)
    setEditandoId(null)
    setForm(formInicial)
  }

  const setFormField = (field) => (value) =>
    setForm(prev => ({ ...prev, [field]: value }))

  return {
    // estado
    items, loading,
    form, setForm, setFormField,
    editandoId,
    mostrarForm,
    busqueda,
    // acciones
    fetchItems,
    handleBusqueda,
    abrirCrear,
    abrirEditar,
    cancelar,
  }
}
