const fecha = (s: string) => new Date(s.replace(' ', 'T'))

export const soles = (n: number | null | undefined) => (n == null ? '—' : `S/ ${n.toFixed(2)}`)

export const hora = (s: string | null | undefined) =>
  s ? fecha(s).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }) : '—'

export const fechaCorta = (s: string | null | undefined) =>
  s ? fecha(s).toLocaleDateString('es-PE', { day: '2-digit', month: 'short' }).replace('.', '') : '—'

export const diaCorto = (s: string) => {
  const [a, m, d] = s.split('-').map(Number)
  return new Date(a, m - 1, d).toLocaleDateString('es-PE', { weekday: 'short', day: 'numeric' }).replace('.', '')
}

export const minutosTexto = (min: number | null | undefined) => {
  if (min == null) return '—'
  if (min < 60) return `${min} min`
  return `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, '0')} min`
}

export const transcurrido = (desde: string, ahora: number) => {
  const s = Math.max(0, Math.floor((ahora - fecha(desde).getTime()) / 1000))
  const hh = String(Math.floor(s / 3600)).padStart(2, '0')
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

/** Misma regla que el servidor: mínimo un minuto y prorrateo por minuto completo. */
export const cobroEstimado = (desde: string, ahora: number, precioHora: number) => {
  const minutos = Math.max(1, Math.floor((ahora - fecha(desde).getTime()) / 60000))
  return Math.round((minutos / 60) * precioHora * 100) / 100
}
