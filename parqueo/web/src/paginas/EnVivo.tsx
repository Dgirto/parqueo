import { ArrowRight, ScanLine, VideoOff } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Resumen, type Ticket } from '../api'
import { Accion, Error, EstadoTicket, Placa, useAhora } from '../componentes'
import { useVivo } from '../eventos'
import { cobroEstimado, hora, minutosTexto, soles, transcurrido } from '../util'

function Camara() {
  const { estado, ultima } = useVivo()
  const [fallo, setFallo] = useState(false)
  const [activa, setActiva] = useState<string | null>(null)

  useEffect(() => {
    if (!ultima) return
    setActiva(ultima.accion)
    const id = window.setTimeout(() => setActiva(null), 2400)
    return () => window.clearTimeout(id)
  }, [ultima])

  const caja = (roi: number[]) => {
    if (!estado) return undefined
    const { ancho, alto } = estado.frame
    return {
      left: `${(roi[0] / ancho) * 100}%`,
      top: `${(roi[1] / alto) * 100}%`,
      width: `${((roi[2] - roi[0]) / ancho) * 100}%`,
      height: `${((roi[3] - roi[1]) / alto) * 100}%`,
    }
  }

  return (
    <section className="camara" aria-label="Cámara de la entrada principal">
      <div className="camara__barra">
        <span>
          <b className="pulso" aria-hidden="true" /> CAM-01 · Entrada principal
        </span>
        <span>{estado ? `${estado.fps} FPS` : '— FPS'}</span>
      </div>
      <div className="camara__marco">
        {fallo ? (
          <div className="camara__vacia">
            <VideoOff size={28} aria-hidden="true" />
            <p>No llega señal de la cámara</p>
            <button type="button" className="boton boton--linea" onClick={() => setFallo(false)}>
              Reconectar
            </button>
          </div>
        ) : (
          <img src="/api/camara.mjpeg" alt="Video en vivo de la entrada" onError={() => setFallo(true)} />
        )}
        {estado && !fallo && (
          <>
            <div className={`zona zona--salida${activa === 'SALIDA' ? ' zona--activa' : ''}`} style={caja(estado.zonas.salida)}>
              <span>Zona de salida</span>
            </div>
            <div className={`zona zona--entrada${activa === 'ENTRADA' ? ' zona--activa' : ''}`} style={caja(estado.zonas.entrada)}>
              <span>Zona de entrada</span>
            </div>
          </>
        )}
      </div>
    </section>
  )
}

function UltimaLectura({ precioHora }: { precioHora: number }) {
  const { ultima, estado } = useVivo()
  const ahora = useAhora()
  const ticket = ultima?.ticket

  return (
    <section className="talon" aria-live="polite" aria-label="Última lectura">
      <div className="talon__cuerpo">
        <p className="rotulo">Última lectura</p>
        {ultima ? (
          <div key={`${ultima.placa}-${ultima.hora}`} className="talon__lectura">
            <Placa valor={ultima.placa} grande />
            <div className="talon__fila">
              <Accion tipo={ultima.accion as 'ENTRADA' | 'SALIDA'} />
              <span className="mono">{hora(ultima.hora)}</span>
            </div>
          </div>
        ) : (
          <div className="talon__vacio">
            <ScanLine size={26} aria-hidden="true" />
            <p>{estado?.ocr === 'cargando' ? 'Cargando el motor de lectura…' : 'Esperando la próxima placa'}</p>
          </div>
        )}
      </div>
      <div className="talon__corte" aria-hidden="true" />
      <dl className="talon__datos">
        <div>
          <dt>Ticket</dt>
          <dd>{ticket ? `#${String(ticket.id).padStart(5, '0')}` : '—'}</dd>
        </div>
        <div>
          <dt>{ultima?.manual ? 'Registro' : 'Confianza'}</dt>
          <dd>{ultima?.manual ? 'Manual' : ultima?.confianza != null ? `${Math.round(ultima.confianza * 100)} %` : '—'}</dd>
        </div>
        <div>
          <dt>{ticket?.estado === 'CERRADO' ? 'Tiempo' : 'Permanencia'}</dt>
          <dd>{ticket ? (ticket.estado === 'CERRADO' ? minutosTexto(ticket.minutos) : transcurrido(ticket.hora_entrada, ahora)) : '—'}</dd>
        </div>
        <div>
          <dt>{ticket?.estado === 'CERRADO' ? 'Cobrado' : 'Acumulado'}</dt>
          <dd className="talon__monto">
            {ticket ? soles(ticket.estado === 'CERRADO' ? ticket.monto : cobroEstimado(ticket.hora_entrada, ahora, precioHora)) : '—'}
          </dd>
        </div>
      </dl>
    </section>
  )
}

function Dentro({ tickets, precioHora, alSalir }: { tickets: Ticket[]; precioHora: number; alSalir: (t: Ticket) => Promise<void> }) {
  const ahora = useAhora()
  const [confirmando, setConfirmando] = useState<number | null>(null)

  return (
    <section className="panel dentro">
      <div className="panel__titulo">
        <h2>Dentro ahora</h2>
        <span className="mono">{tickets.length}</span>
      </div>
      {tickets.length === 0 ? (
        <p className="vacio">No hay vehículos dentro.</p>
      ) : (
        <ul>
          {tickets.map((t) => (
            <li key={t.id}>
              <Placa valor={t.placa} />
              <span className="mono dentro__tiempo">{transcurrido(t.hora_entrada, ahora)}</span>
              <span className="mono dentro__monto">{soles(cobroEstimado(t.hora_entrada, ahora, precioHora))}</span>
              {confirmando === t.id ? (
                <span className="dentro__confirmar">
                  <button type="button" className="boton boton--peligro" onClick={() => alSalir(t).finally(() => setConfirmando(null))}>
                    Cobrar
                  </button>
                  <button type="button" className="boton boton--linea" onClick={() => setConfirmando(null)}>
                    No
                  </button>
                </span>
              ) : (
                <button type="button" className="boton boton--linea" onClick={() => setConfirmando(t.id)} aria-label={`Registrar salida de ${t.placa}`}>
                  Salida
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default function EnVivo() {
  const { version } = useVivo()
  const [resumen, setResumen] = useState<Resumen | null>(null)
  const [dentro, setDentro] = useState<Ticket[]>([])
  const [recientes, setRecientes] = useState<Ticket[]>([])
  const [error, setError] = useState('')

  const cargar = useCallback(async () => {
    try {
      const [r, d, u] = await Promise.all([api.resumen(), api.tickets({ estado: 'ACTIVO', limite: 50 }), api.tickets({ limite: 6 })])
      setResumen(r)
      setDentro(d.items)
      setRecientes(u.items)
      setError('')
    } catch (e) {
      setError((e as globalThis.Error).message)
    }
  }, [])

  useEffect(() => {
    cargar()
  }, [cargar, version])

  const salir = async (t: Ticket) => {
    try {
      await api.salida(t.id)
      await cargar()
    } catch (e) {
      setError((e as globalThis.Error).message)
    }
  }

  const ocupacion = resumen ? Math.min(100, (resumen.dentro / resumen.capacidad) * 100) : 0
  const precio = resumen?.precio_hora ?? 0

  return (
    <div className="vivo">
      {error && <Error mensaje={error} reintentar={cargar} />}
      <section className="indicadores" aria-label="Resumen de hoy">
        <div className="indicador indicador--aforo">
          <p className="rotulo">Ocupación</p>
          <p className="indicador__valor">
            {resumen?.dentro ?? '—'}
            <small>/{resumen?.capacidad ?? '—'}</small>
          </p>
          <div className="medidor" role="meter" aria-label="Ocupación" aria-valuemin={0} aria-valuemax={resumen?.capacidad ?? 0} aria-valuenow={resumen?.dentro ?? 0}>
            <span style={{ width: `${ocupacion}%` }} />
          </div>
        </div>
        <div className="indicador">
          <p className="rotulo">Espacios libres</p>
          <p className="indicador__valor">{resumen?.libres ?? '—'}</p>
        </div>
        <div className="indicador">
          <p className="rotulo">Salidas de hoy</p>
          <p className="indicador__valor">{resumen?.cobros ?? '—'}</p>
        </div>
        <div className="indicador">
          <p className="rotulo">Ingresos de hoy</p>
          <p className="indicador__valor">{resumen ? soles(resumen.ingresos) : '—'}</p>
        </div>
      </section>

      <div className="vivo__rejilla">
        <Camara />
        <div className="vivo__lateral">
          <UltimaLectura precioHora={precio} />
          <Dentro tickets={dentro} precioHora={precio} alSalir={salir} />
        </div>
      </div>

      <section className="panel">
        <div className="panel__titulo">
          <h2>Actividad reciente</h2>
          <Link to="/registros" className="enlace">
            Ver registros <ArrowRight size={15} aria-hidden="true" />
          </Link>
        </div>
        {recientes.length === 0 ? (
          <p className="vacio">Aún no hay movimientos.</p>
        ) : (
          <div className="tabla-marco">
            <table className="tabla">
              <thead>
                <tr>
                  <th scope="col">Placa</th>
                  <th scope="col">Entrada</th>
                  <th scope="col">Salida</th>
                  <th scope="col">Tiempo</th>
                  <th scope="col" className="der">Monto</th>
                  <th scope="col">Estado</th>
                </tr>
              </thead>
              <tbody>
                {recientes.map((t) => (
                  <tr key={t.id}>
                    <td><Placa valor={t.placa} /></td>
                    <td className="mono">{hora(t.hora_entrada)}</td>
                    <td className="mono">{hora(t.hora_salida)}</td>
                    <td className="mono">{minutosTexto(t.minutos)}</td>
                    <td className="mono der">{soles(t.monto)}</td>
                    <td><EstadoTicket estado={t.estado} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
