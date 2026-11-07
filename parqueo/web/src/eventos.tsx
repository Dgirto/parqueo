import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api, type Estado, type Evento, type Lectura } from './api'

interface Vivo {
  conectado: boolean
  estado: Estado | null
  ultima: Lectura | null
  /** Sube con cada cambio de datos: las pantallas lo usan para volver a consultar. */
  version: number
}

const Contexto = createContext<Vivo>({ conectado: false, estado: null, ultima: null, version: 0 })

export const useVivo = () => useContext(Contexto)

export function ProveedorVivo({ children }: { children: ReactNode }) {
  const [conectado, setConectado] = useState(false)
  const [estado, setEstado] = useState<Estado | null>(null)
  const [ultima, setUltima] = useState<Lectura | null>(null)
  const [version, setVersion] = useState(0)
  const reintento = useRef(0)

  useEffect(() => {
    let cerrado = false
    let ws: WebSocket | undefined
    let temporizador: number | undefined

    const conectar = () => {
      const esquema = location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${esquema}://${location.host}/api/eventos`)
      ws.onopen = () => {
        reintento.current = 0
        setConectado(true)
        setVersion((v) => v + 1)
      }
      ws.onmessage = (m) => {
        const e: Evento = JSON.parse(m.data)
        if (e.tipo === 'deteccion') {
          if (e.accion === 'ENTRADA' || e.accion === 'SALIDA') {
            setUltima(e)
            setVersion((v) => v + 1)
          }
        } else if (e.tipo === 'cambio') {
          setVersion((v) => v + 1)
        } else if (e.tipo === 'estado') {
          setEstado((a) => (a ? { ...a, ...e.estado } : a))
        }
      }
      ws.onclose = () => {
        setConectado(false)
        if (cerrado) return
        reintento.current += 1
        temporizador = window.setTimeout(conectar, Math.min(8000, 500 * 2 ** reintento.current))
      }
    }

    conectar()
    return () => {
      cerrado = true
      window.clearTimeout(temporizador)
      ws?.close()
    }
  }, [])

  useEffect(() => {
    let vivo = true
    const leer = () => api.estado().then((e) => vivo && setEstado(e)).catch(() => {})
    leer()
    const id = window.setInterval(leer, 3000)
    return () => {
      vivo = false
      window.clearInterval(id)
    }
  }, [])

  const valor = useMemo(() => ({ conectado, estado, ultima, version }), [conectado, estado, ultima, version])
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>
}
