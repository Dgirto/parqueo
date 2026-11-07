import { Check } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { api, type Tarifa } from '../api'
import { Cabecera, Error } from '../componentes'
import { soles } from '../util'

const EJEMPLOS = [15, 30, 60, 150]

export default function Tarifas() {
  const [tarifa, setTarifa] = useState<Tarifa | null>(null)
  const [precio, setPrecio] = useState('')
  const [error, setError] = useState('')
  const [guardado, setGuardado] = useState(false)

  const cargar = () =>
    api
      .tarifas()
      .then(([t]) => {
        setTarifa(t)
        setPrecio(t.precio_hora.toFixed(2))
        setError('')
      })
      .catch((e) => setError(e.message))

  useEffect(() => {
    cargar()
  }, [])

  const valor = Number(precio)
  const valido = precio !== '' && valor > 0 && valor <= 1000
  const sinCambios = tarifa !== null && valor === tarifa.precio_hora

  const guardar = async (e: FormEvent) => {
    e.preventDefault()
    if (!tarifa || !valido) return
    try {
      setTarifa(await api.guardarTarifa(tarifa.id, valor))
      setGuardado(true)
      setError('')
      window.setTimeout(() => setGuardado(false), 2500)
    } catch (err) {
      setError((err as globalThis.Error).message)
    }
  }

  return (
    <div className="pagina pagina--estrecha">
      <Cabecera titulo="Tarifas" detalle="El nuevo precio se aplica a los tickets que se cierren desde ahora." />
      {error && <Error mensaje={error} reintentar={cargar} />}
      <div className="dos-columnas">
        <form className="panel formulario" onSubmit={guardar}>
          <h2>{tarifa?.nombre ?? 'Tarifa'}</h2>
          <label className="campo">
            <span>Precio por hora (S/)</span>
            <input type="number" min="0.01" max="1000" step="0.01" inputMode="decimal" value={precio} onChange={(e) => setPrecio(e.target.value)} aria-invalid={!valido} required />
          </label>
          {!valido && <p className="ayuda ayuda--error">Escribe un precio entre S/ 0.01 y S/ 1000.</p>}
          <button type="submit" className="boton" disabled={!valido || sinCambios}>
            {guardado ? <><Check size={16} aria-hidden="true" /> Guardado</> : 'Guardar tarifa'}
          </button>
        </form>
        <section className="panel">
          <h2>Cuánto se cobraría</h2>
          <table className="tabla tabla--simple">
            <tbody>
              {EJEMPLOS.map((m) => (
                <tr key={m}>
                  <th scope="row">{m < 60 ? `${m} minutos` : `${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60} min` : ''}`}</th>
                  <td className="mono der">{valido ? soles(Math.round((m / 60) * valor * 100) / 100) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ayuda">Se cobra por minuto, con un mínimo de un minuto.</p>
        </section>
      </div>
    </div>
  )
}
