import React, {useCallback, useEffect, useState} from 'react'
import {useDropzone} from 'react-dropzone'
import styles from './mydropzone.module.css'

/**
 * Componente controlado de subida de imágenes.
 * El padre es dueño del estado (`imagenes`, `subiendo`) y de la llamada a la API.
 *
 * Props:
 *  - imagenes:    File[]              lista actual de archivos (controlada por el padre)
 *  - setImagenes: (File[]) => void    se llama con la nueva lista al agregar/eliminar
 *  - subiendo:    boolean             deshabilita el botón mientras el padre sube
 *  - onSubir:     () => void          el padre dispara la subida real
 */
export default function MyDropzone({imagenes = [], setImagenes, subiendo = false, onSubir}) {
  // las object URLs para preview se derivan de `imagenes` y se liberan al cambiar/desmontar
  const [previews, setPreviews] = useState([])

  useEffect(() => {
    const urls = imagenes.map(file => URL.createObjectURL(file))
    setPreviews(urls)
    return () => urls.forEach(url => URL.revokeObjectURL(url))
  }, [imagenes])

  const onDrop = useCallback(acceptedFiles => {
    setImagenes([...imagenes, ...acceptedFiles])
  }, [imagenes, setImagenes])

  const {getRootProps, getInputProps, isDragActive} = useDropzone({onDrop, multiple: true})

  const eliminarImagen = (index) => {
    setImagenes(imagenes.filter((_, i) => i !== index))
  }

  return (
    <div className={styles.dropzoneContainer}>
      <div className={styles.dropzone} {...getRootProps()}>
        <input className={styles.dropzoneInput} {...getInputProps()} />
        {
          isDragActive ?
            <p>Soltá las imágenes acá</p> :
            <p>Arrastrá imágenes o clickeá para seleccionar</p>
        }
      </div>

      <ul className={styles.listaImagenes}>
        {imagenes.map((file, i) => (
          <li className={styles.imagenItem} key={`${file.name}-${i}`}>
            <button
              type="button"
              className={styles.botonEliminar}
              onClick={() => eliminarImagen(i)}
              aria-label={`Eliminar ${file.name}`}
            >
              ×
            </button>
            <img
              className={styles.imagen}
              src={previews[i]}
              alt={file.name}
            />
          </li>
        ))}
      </ul>

      <button
        type="button"
        className={styles.botonSubir}
        onClick={onSubir}
        disabled={imagenes.length === 0 || subiendo}
      >
        {subiendo ? 'Subiendo...' : 'Subir imágenes'}
      </button>
    </div>
  )
}
