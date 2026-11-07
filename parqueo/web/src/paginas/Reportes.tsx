import { useEffect, useState } from 'react'
import { api, type Reporte } from '../api'
import { Cabecera, Error } from '../componentes'
import { useVivo } from '../eventos'
import { diaCorto, minutosTexto, soles } from '../util'

interface Dato {
  etiqueta: string
  corta: string
  valor: number
  texto: string
}

function Barras({ titulo, datos, resumen }: { titulo: string; datos: Dato[]; resumen: string }) {
  const [activo, setActivo] = useState<number | null>(null)
  const [tabla, setTabla] = useState(false)
  const maximo = Math.max(...datos.map((d) => d.valor), 1)
  const pico = datos.reduce((a, b) => (b.valor > a.valor ? b : a), datos[0])
  const mostrar = activo !== null ? datos[activo] : null

  return (
    <section className="panel grafico">
      <div className="panel__titulo">
        <div>
          <h2>{titulo}</h2>
          <p className="grafico__dato" aria-hidden="true">
            {mostrar ? `${mostrar.etiqueta}: ${mostrar.texto}` : resumen}
          </p>
        </div>
        <button type="button" className="enlace" aria-pressed={tabla} onClick={() => setTabla((t) => !t)}>
          {tabla ? 'Ver gráfico' : 'Ver tabla'}
        </button>
      </div>
      {tabla ? (
        <div className="tabla-marco">
          <table className="tabla">
            <tbody>
              {datos.map((d) => (
                <tr key={d.etiqueta}>
                  <th scope="row">{d.etiqueta}</th>
                  <td className="mono der">{d.texto}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="barras" role="img" aria-label={`${titulo}. ${resumen}. Máximo: ${pico.etiqueta}, ${pico.texto}.`} onMouseLeave={() => setActivo(null)}>
          {datos.map((d, i) => (
            <div key={d.etiqueta} className={`barra${activo === i ? ' barra--activa' : ''}`} onMouseEnter={() => setActivo(i)}>
              <span className="barra__marca" style={{ height: `${Math.max(d.valor > 0 ? 2 : 0, (d.valor / maximo) * 100)}%` }} />
              <small>{d.corta}</small>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default function Reportes() {
  const { version } = useVivo()
  const [dias, setDias] = useState(7)
  const [datos, setDatos] = useState<Reporte | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let vigente = true
    api
      .reportes(dias)
      .then((r) => {
        if (vigente) {
          setDatos(r)
          setError('')
        }
      })
      .catch((e) => vigente && setError(e.message))
    return () => {
      vigente = false
    }
  }, [dias, version])

  const entradas = datos?.por_hora.reduce((a, h) => a + h.entradas, 0) ?? 0
  const salto = dias > 14 ? 5 : 1

  return (
    <div className="pagina">
      <Cabecera titulo="Reportes" detalle="Ingresos y movimiento del estacionamiento.">
        <div className="segmento" role="group" aria-label="Periodo">
          {[7, 30].map((d) => (
            <button key={d} type="button" aria-pressed={dias === d} onClick={() => setDias(d)}>
              {d} días
            </button>
          ))}
        </div>
      </Cabecera>

      {error && <Error mensaje={error} />}

      {datos && (
        <>
          <section className="indicadores indicadores--tres" aria-label="Totales del periodo">
            <div className="indicador">
              <p className="rotulo">Ingresos</p>
              <p className="indicador__valor">{soles(datos.total_ingresos)}</p>
            </div>
            <div className="indicador">
              <p className="rotulo">Salidas cobradas</p>
              <p className="indicador__valor">{datos.total_salidas}</p>
            </div>
            <div className="indicador">
              <p className="rotulo">Permanencia promedio</p>
              <p className="indicador__valor">{minutosTexto(datos.permanencia_promedio)}</p>
            </div>
          </section>

          <div className="graficos">
            <Barras
              titulo="Ingresos por día"
              resumen={`${soles(datos.total_ingresos)} en ${dias} días`}
              datos={datos.por_dia.map((d, i) => ({
                etiqueta: diaCorto(d.dia),
                corta: dias > 14 ? ((dias - 1 - i) % salto === 0 ? diaCorto(d.dia).split(' ').at(-1)! : '') : diaCorto(d.dia).split(' ')[0],
                valor: d.ingresos,
                texto: soles(d.ingresos),
              }))}
            />
            <Barras
              titulo="Entradas por hora"
              resumen={`${entradas} entradas en el periodo`}
              datos={datos.por_hora.map((h) => ({
                etiqueta: `${String(h.hora).padStart(2, '0')}:00`,
                corta: h.hora % 6 === 0 ? String(h.hora).padStart(2, '0') : '',
                valor: h.entradas,
                texto: `${h.entradas} ${h.entradas === 1 ? 'entrada' : 'entradas'}`,
              }))}
            />
          </div>
        </>
      )}
    </div>
  )
}
