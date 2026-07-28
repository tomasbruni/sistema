import React, {useCallback, useState} from 'react'
import {useDropzone} from 'react-dropzone'
import styles from './mydropzone.module.css'

export default function MyDropzone() {
  const [imagenes, setImagenes] = useState([])

  const onDrop = useCallback(acceptedFiles => {
    setImagenes(prev => [...prev, ...acceptedFiles])
  }, [])

  const {getRootProps, getInputProps, isDragActive} = useDropzone({onDrop, multiple: true})

  const files = imagenes.map((file, i) => (
    <li key={`${file.path}-${i}`}>
      {file.path} - {file.size} bytes
    </li>
  ));

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
      {files}
      {/* botón enviar */}
    </div>
  )
}

