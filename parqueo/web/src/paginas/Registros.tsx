import { ChevronLeft, ChevronRight, Download, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, consultaTickets, type Ticket } from '../api'
import { Cabecera, Error, EstadoTicket, Placa } from '../componentes'
import { useVivo } from '../eventos'
import { fechaCorta, hora, minutosTexto, soles } from '../util'

const POR_PAGINA = 12

export default function Registros() {
  const { version } = useVivo()
  const [q, setQ] = useState('')
  const [estado, setEstado] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [pagina, setPagina] = useState(0)
  const [datos, setDatos] = useState<{ items: Ticket[]; total: number } | null>(null)
  const [error, setError] = useState('')

  const filtros = { q, estado, desde, hasta }

  useEffect(() => setPagina(0), [q, estado, desde, hasta])

  useEffect(() => {
    let vigente = true
    const id = window.setTimeout(() => {
      api
        .tickets({ ...filtros, limite: POR_PAGINA, inicio: pagina * POR_PAGINA })
        .then((d) => {
          if (vigente) {
            setDatos(d)
            setError('')
          }
        })
        .catch((e) => vigente && setError(e.message))
    }, 150)
    return () => {
      vigente = false
      window.clearTimeout(id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, estado, desde, hasta, pagina, version])

  const total = datos?.total ?? 0
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA))
  const hayFiltros = q || estado || desde || hasta

  return (
    <div className="pagina">
      <Cabecera titulo="Registros" detalle="Historial completo de entradas y salidas.">
        <a className="boton boton--linea" href={`/api/tickets.csv?${consultaTickets(filtros)}`} download>
          <Download size={16} aria-hidden="true" /> Exportar CSV
        </a>
      </Cabecera>

      <form className="filtros" role="search" onSubmit={(e) => e.preventDefault()}>
        <label className="campo campo--buscar">
          <span>Placa</span>
          <span className="campo__icono">
            <Search size={16} aria-hidden="true" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="ABC-123" maxLength={10} autoComplete="off" />
          </span>
        </label>
        <label className="campo">
          <span>Estado</span>
          <select value={estado} onChange={(e) => setEstado(e.target.value)}>
            <option value="">Todos</option>
            <option value="ACTIVO">Dentro</option>
            <option value="CERRADO">Cerrado</option>
          </select>
        </label>
        <label className="campo">
          <span>Desde</span>
          <input type="date" value={desde} max={hasta || undefined} onChange={(e) => setDesde(e.target.value)} />
        </label>
        <label className="campo">
          <span>Hasta</span>
          <input type="date" value={hasta} min={desde || undefined} onChange={(e) => setHasta(e.target.value)} />
        </label>
      </form>

      {error && <Error mensaje={error} />}

      <section className="panel" aria-live="polite">
        <div className="panel__titulo">
          <h2>{datos ? `${total} ${total === 1 ? 'ticket' : 'tickets'}` : 'Cargando…'}</h2>
        </div>
        {datos && datos.items.length === 0 ? (
          <p className="vacio">{hayFiltros ? 'Ningún ticket coincide con estos filtros.' : 'Todavía no hay tickets.'}</p>
        ) : (
          <div className="tabla-marco">
            <table className="tabla">
              <thead>
                <tr>
                  <th scope="col">Ticket</th>
                  <th scope="col">Placa</th>
                  <th scope="col">Fecha</th>
                  <th scope="col">Entrada</th>
                  <th scope="col">Salida</th>
                  <th scope="col">Tiempo</th>
                  <th scope="col" className="der">Monto</th>
                  <th scope="col">Estado</th>
                </tr>
              </thead>
              <tbody>
                {datos?.items.map((t) => (
                  <tr key={t.id}>
                    <td className="mono tenue">#{String(t.id).padStart(5, '0')}</td>
                    <td><Placa valor={t.placa} /></td>
                    <td className="mono">{fechaCorta(t.hora_entrada)}</td>
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
        {total > POR_PAGINA && (
          <nav className="paginacion" aria-label="Paginación">
            <button type="button" className="boton boton--linea" disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}>
              <ChevronLeft size={16} aria-hidden="true" /> Anterior
            </button>
            <span className="mono">
              {pagina + 1} / {paginas}
            </span>
            <button type="button" className="boton boton--linea" disabled={pagina + 1 >= paginas} onClick={() => setPagina((p) => p + 1)}>
              Siguiente <ChevronRight size={16} aria-hidden="true" />
            </button>
          </nav>
        )}
      </section>
    </div>
  )
}
