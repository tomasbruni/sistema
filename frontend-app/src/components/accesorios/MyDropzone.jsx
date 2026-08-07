import React, {useCallback, useEffect, useState} from 'react'
import {useDropzone} from 'react-dropzone'
import styles from './mydropzone.module.css'

export default function MyDropzone() {
  // guardamos { file, preview } para crear la object URL UNA sola vez por imagen
  const [imagenes, setImagenes] = useState([])
  const [subiendo, setSubiendo] = useState(false)

  const onDrop = useCallback(acceptedFiles => {
    const nuevas = acceptedFiles.map(file => ({
      file,
      preview: URL.createObjectURL(file),
    }))
    setImagenes(prev => [...prev, ...nuevas])
  }, [])

  const {getRootProps, getInputProps, isDragActive} = useDropzone({onDrop, multiple: true})

  const eliminarImagen = (index) => {
    setImagenes(prev => {
      // liberamos la object URL de la imagen que sacamos
      URL.revokeObjectURL(prev[index].preview)
      return prev.filter((_, i) => i !== index)
    })
  }

  // al desmontar el componente, liberamos todas las object URLs que queden
  useEffect(() => {
    return () => {
      imagenes.forEach(img => URL.revokeObjectURL(img.preview))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // sketch: subir las imágenes al backend
  const subirImagenes = async () => {
    if (imagenes.length === 0) return
    setSubiendo(true)
    try {
      const formData = new FormData()
      imagenes.forEach(({file}) => formData.append('imagenes', file))

      // TODO: reemplazar por la llamada real a la API (authFetch en api.js)
      // const res = await subirImagenesAccesorio(formData)

      // TODO: manejar la respuesta (ids/urls devueltos por el backend)

      // limpiamos el estado y liberamos las URLs tras subir con éxito
      imagenes.forEach(img => URL.revokeObjectURL(img.preview))
      setImagenes([])
    } catch (err) {
      console.error('Error al subir las imágenes', err)
      // TODO: mostrar alerta al usuario
    } finally {
      setSubiendo(false)
    }
  }

  return (
    <div className={styles.dropzoneContainer}>
      <div className={styles.dropzone} {...getRootProps()}>
        <input className={styles.dropzoneInput} {...getInputProps()} />
        {
          isDragActive ?
            <p>Drop the files here ...</p> :
            <p>Drag 'n' drop some files here, or click to select files</p>
        }
      </div>

      <ul className={styles.listaImagenes}>
        {imagenes.map((img, i) => (
          <li className={styles.imagenItem} key={`${img.file.name}-${i}`}>
            <button
              type="button"
              className={styles.botonEliminar}
              onClick={() => eliminarImagen(i)}
              aria-label={`Eliminar ${img.file.name}`}
            >
              ×
            </button>
            <img
              className={styles.imagen}
              src={img.preview}
              alt={img.file.name}
            />
          </li>
        ))}
      </ul>

      <button
        type="button"
        className={styles.botonSubir}
        onClick={subirImagenes}
        disabled={imagenes.length === 0 || subiendo}
      >
        {subiendo ? 'Subiendo...' : 'Subir imágenes'}
      </button>
    </div>
  )
}
