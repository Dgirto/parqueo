export interface Ticket {
  id: number
  placa: string
  hora_entrada: string
  hora_salida: string | null
  minutos: number | null
  monto: number | null
  tarifa_id: number
  estado: 'ACTIVO' | 'CERRADO'
}

export interface Resumen {
  dentro: number
  capacidad: number
  libres: number
  cobros: number
  ingresos: number
  entradas: number
  precio_hora: number
}

export interface Estado {
  ocr: 'cargando' | 'listo' | 'error'
  video: boolean
  fps: number
  confianza_minima: number
  frame: { ancho: number; alto: number }
  zonas: { entrada: number[]; salida: number[] }
}

export interface Reporte {
  por_dia: { dia: string; salidas: number; ingresos: number }[]
  por_hora: { hora: number; entradas: number }[]
  total_ingresos: number
  total_salidas: number
  permanencia_promedio: number | null
}

export interface Tarifa {
  id: number
  nombre: string
  precio_hora: number
  activa: number
}

export interface Lectura {
  tipo: 'deteccion'
  accion: 'ENTRADA' | 'SALIDA' | 'YA_DENTRO' | 'NO_DENTRO' | 'INVALIDA' | 'ERROR'
  placa: string
  hora: string
  confianza: number | null
  manual?: boolean
  ticket: Ticket | null
}

export type Evento = Lectura | { tipo: 'cambio' } | { tipo: 'latido' } | { tipo: 'estado'; estado: Partial<Estado> }

export interface FiltrosTickets {
  estado?: string
  q?: string
  desde?: string
  hasta?: string
  limite?: number
  inicio?: number
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  const r = await fetch(ruta, init)
  if (!r.ok) {
    const cuerpo = await r.json().catch(() => null)
    throw new Error(typeof cuerpo?.detail === 'string' ? cuerpo.detail : 'No se pudo completar la operación')
  }
  return r.json()
}

const json = (method: string, cuerpo: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(cuerpo),
})

export function consultaTickets(f: FiltrosTickets): string {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== '') p.set(k, String(v))
  return p.toString()
}

export const api = {
  estado: () => pedir<Estado>('/api/estado'),
  resumen: () => pedir<Resumen>('/api/resumen'),
  reportes: (dias: number) => pedir<Reporte>(`/api/reportes?dias=${dias}`),
  tickets: (f: FiltrosTickets) => pedir<{ items: Ticket[]; total: number }>(`/api/tickets?${consultaTickets(f)}`),
  salida: (id: number) => pedir<Ticket>(`/api/tickets/${id}/salida`, { method: 'POST' }),
  limpiar: (confirmacion: string) => pedir<{ borrados: number }>('/api/tickets', json('DELETE', { confirmacion })),
  tarifas: () => pedir<Tarifa[]>('/api/tarifas'),
  guardarTarifa: (id: number, precio_hora: number) => pedir<Tarifa>(`/api/tarifas/${id}`, json('PUT', { precio_hora })),
  ajustes: () => pedir<{ capacidad: number }>('/api/ajustes'),
  guardarAjustes: (capacidad: number) => pedir<{ capacidad: number }>('/api/ajustes', json('PUT', { capacidad })),
}
