import { ArrowDownLeft, ArrowUpRight, Circle, CircleCheck } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import type { Ticket } from './api'

export function Placa({ valor, grande = false }: { valor: string; grande?: boolean }) {
  return (
    <span className={grande ? 'placa placa--grande' : 'placa'} aria-label={`Placa ${valor}`}>
      <i aria-hidden="true" />
      {valor}
      <i aria-hidden="true" />
    </span>
  )
}

export function Accion({ tipo }: { tipo: 'ENTRADA' | 'SALIDA' }) {
  const Icono = tipo === 'ENTRADA' ? ArrowDownLeft : ArrowUpRight
  return (
    <span className={`accion accion--${tipo.toLowerCase()}`}>
      <Icono size={15} aria-hidden="true" />
      {tipo === 'ENTRADA' ? 'Entrada' : 'Salida'}
    </span>
  )
}

export function EstadoTicket({ estado }: { estado: Ticket['estado'] }) {
  return estado === 'ACTIVO' ? (
    <span className="estado estado--activo">
      <Circle size={9} fill="currentColor" aria-hidden="true" /> Dentro
    </span>
  ) : (
    <span className="estado">
      <CircleCheck size={14} aria-hidden="true" /> Cerrado
    </span>
  )
}

export function Cabecera({ titulo, detalle, children }: { titulo: string; detalle: string; children?: ReactNode }) {
  return (
    <header className="cabecera">
      <div>
        <h1>{titulo}</h1>
        <p>{detalle}</p>
      </div>
      {children && <div className="cabecera__acciones">{children}</div>}
    </header>
  )
}

export function Error({ mensaje, reintentar }: { mensaje: string; reintentar?: () => void }) {
  return (
    <div className="aviso aviso--error" role="alert">
      <span>{mensaje}</span>
      {reintentar && (
        <button type="button" className="boton boton--linea" onClick={reintentar}>
          Reintentar
        </button>
      )}
    </div>
  )
}

/** Reloj de un segundo para tiempos y montos en vivo. */
export function useAhora() {
  const [ahora, setAhora] = useState(Date.now)
  useEffect(() => {
    const id = window.setInterval(() => setAhora(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [])
  return ahora
}
