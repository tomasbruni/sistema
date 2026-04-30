import { createContext, useState, useEffect, useCallback, useRef } from 'react'

// ─── CONTEXTO ─────────────────────────────────────────────────────────────────
// Guarda: { token, nombre, rol, usuarioId } en localStorage para persistir entre recargas.
// Expone: login(datos), logout(), y los cuatro valores.

const AuthContext = createContext(null)

// El usuario inicia sesión → guardás en localStorage
// Recarga la página
// React vuelve a montar AuthProvider
// useState(() => localStorage.getItem(...)):
// recupera el token
// useAuth() ya tiene token → RutaPrivada deja pasar

export function AuthProvider({ children }) {
  // Inicializar desde localStorage si ya había una sesión guardada
  const [token,     setToken]     = useState(() => localStorage.getItem('token')     ?? null)
  const [nombre,    setNombre]    = useState(() => localStorage.getItem('nombre')    ?? null)
  const [rol,       setRol]       = useState(() => localStorage.getItem('rol')       ?? null)
  const [usuarioId, setUsuarioId] = useState(() => {
    const v = localStorage.getItem('usuario_id')
    return v !== null ? Number(v) : null
  })
  const [expirada, setExpirada] = useState(null)
  
  // flag para que solo 1 evento dispare logout,
  // se procesa un evento por vez, entonces el primero es el que deslogea,
  // los demas lo hacen innecesariamente
  // (fetch dispara el evento y se hacen varios fetch concurrentes)
  // sincrono a diferencia del estado, la siguiente ejecucion lo ve
  const alreadyLoggedOut = useRef(false)

  const login = (datos) => {
    localStorage.setItem('token', datos.access_token)
    localStorage.setItem('nombre', datos.nombre)
    localStorage.setItem('rol', datos.rol)
    localStorage.setItem('usuario_id', datos.usuario_id)

    setToken(datos.access_token)
    setNombre(datos.nombre)
    setRol(datos.rol)
    setUsuarioId(datos.usuario_id)

    alreadyLoggedOut.current = false   
    setExpirada(null)                 
  }

  // cuando cambia el estado de authContext, 
  // se crea de nuevo logout, 
  // distinto al logout del primer render que es usado por el evento
  // por eso useCallback
  // no pasa nada pq no es en funcion del estado actual

  const logout = useCallback((source = 'manual') => {
    // se usa useRef y no setState porque:
    // setState(prev => true) lo unico que le dice es en funcion de que estado aplicar el nuevo estado, 
    // pero a la hora de leer el estado, la actualizacion puede no estar aplicada, porque se hace en batches
    // lo unico que hace eso es poner en fila el setState (le da un lugar en la secuencia de actualizaciones), pero no lo aplica
    // por eso el primer setState no va a afectar al estado que leen los que le siguen,
    // solo afecta al estado que leen los que le siguen a la hora de actualizar (react puede esperar a que terminen todos los eventos y despues aplicar la actualizacion del estado)
    // en cambio useRef se aplica al momento, y si un evento lo cambia los demas que le siguen (son secuenciales) leen el valor cambiado
    if (alreadyLoggedOut.current) return
    alreadyLoggedOut.current = true

    localStorage.removeItem('token')
    localStorage.removeItem('nombre')
    localStorage.removeItem('rol')
    localStorage.removeItem('usuario_id')

    setToken(null)
    setNombre(null)
    setRol(null)
    setUsuarioId(null)

    if (source === '401') {
      setExpirada('Sesión expirada, vuelva a iniciar sesión')
    } else {
      setExpirada(null)
    }
  }, [])
    
  useEffect(() => {
    // esta recibe el evento y le pasa el detail a logout
    const handler = (e) => {
      const source = e.detail?.source
      logout(source)
    }

    window.addEventListener('auth:logout', handler)
    return () => window.removeEventListener('auth:logout', handler)
  }, [logout])

  return (
    <AuthContext.Provider value={{ token, nombre, rol, usuarioId, expirada, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export default AuthContext