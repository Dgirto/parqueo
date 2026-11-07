import { Check, TriangleAlert } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import { Cabecera, Error } from '../componentes'
import { useVivo } from '../eventos'

const OCR = { cargando: 'Cargando', listo: 'Operativo', error: 'Con errores' }

export default function Ajustes() {
  const { estado, conectado } = useVivo()
  const [actual, setActual] = useState<number | null>(null)
  const [capacidad, setCapacidad] = useState('')
  const [confirmacion, setConfirmacion] = useState('')
  const [error, setError] = useState('')
  const [mensaje, setMensaje] = useState('')

  useEffect(() => {
    api
      .ajustes()
      .then((a) => {
        setActual(a.capacidad)
        setCapacidad(String(a.capacidad))
      })
      .catch((e) => setError(e.message))
  }, [])

  const valor = Number(capacidad)
  const valido = Number.isInteger(valor) && valor >= 1 && valor <= 10000

  const guardar = async (e: FormEvent) => {
    e.preventDefault()
    if (!valido) return
    try {
      const r = await api.guardarAjustes(valor)
      setActual(r.capacidad)
      setMensaje('Capacidad actualizada')
      setError('')
    } catch (err) {
      setError((err as globalThis.Error).message)
    }
  }

  const limpiar = async (e: FormEvent) => {
    e.preventDefault()
    try {
      const r = await api.limpiar(confirmacion)
      setConfirmacion('')
      setMensaje(`Se borraron ${r.borrados} tickets`)
      setError('')
    } catch (err) {
      setError((err as globalThis.Error).message)
    }
  }

  return (
    <div className="pagina pagina--estrecha">
      <Cabecera titulo="Configuración" detalle="Capacidad del local y estado del sistema." />
      {error && <Error mensaje={error} />}
      {mensaje && (
        <p className="aviso aviso--ok" role="status">
          <Check size={16} aria-hidden="true" /> {mensaje}
        </p>
      )}

      <div className="dos-columnas">
        <form className="panel formulario" onSubmit={guardar}>
          <h2>Capacidad</h2>
          <label className="campo">
            <span>Espacios del estacionamiento</span>
            <input type="number" min="1" max="10000" step="1" value={capacidad} onChange={(e) => setCapacidad(e.target.value)} required />
          </label>
          <button type="submit" className="boton" disabled={!valido || valor === actual}>
            Guardar capacidad
          </button>
        </form>

        <section className="panel">
          <h2>Sistema</h2>
          <dl className="ficha">
            <div><dt>Conexión en vivo</dt><dd>{conectado ? 'Conectada' : 'Reconectando…'}</dd></div>
            <div><dt>Motor de lectura</dt><dd>{estado ? OCR[estado.ocr] : '—'}</dd></div>
            <div><dt>Cámara</dt><dd>{estado?.video ? `${estado.fps} FPS` : 'Sin señal'}</dd></div>
            <div><dt>Confianza mínima</dt><dd>{estado ? `${Math.round(estado.confianza_minima * 100)} %` : '—'}</dd></div>
          </dl>
        </section>
      </div>

      <form className="panel peligro" onSubmit={limpiar}>
        <div>
          <h2>
            <TriangleAlert size={18} aria-hidden="true" /> Borrar todos los tickets
          </h2>
          <p>Elimina el historial completo. No se puede deshacer.</p>
        </div>
        <label className="campo">
          <span>Escribe BORRAR para confirmar</span>
          <input value={confirmacion} onChange={(e) => setConfirmacion(e.target.value)} autoComplete="off" />
        </label>
        <button type="submit" className="boton boton--peligro" disabled={confirmacion !== 'BORRAR'}>
          Borrar historial
        </button>
      </form>
    </div>
  )
}
