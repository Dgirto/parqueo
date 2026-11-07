import '@fontsource-variable/geist'
import '@fontsource-variable/geist-mono'
import '@fontsource/saira-stencil-one'
import { BarChart3, CircleDollarSign, Radio, Rows3, Settings } from 'lucide-react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import { ProveedorVivo, useVivo } from './eventos'
import './estilos.css'
import Ajustes from './paginas/Ajustes'
import EnVivo from './paginas/EnVivo'
import Registros from './paginas/Registros'
import Reportes from './paginas/Reportes'
import Tarifas from './paginas/Tarifas'

const SECCIONES = [
  { ruta: '/', texto: 'En vivo', Icono: Radio },
  { ruta: '/registros', texto: 'Registros', Icono: Rows3 },
  { ruta: '/reportes', texto: 'Reportes', Icono: BarChart3 },
  { ruta: '/tarifas', texto: 'Tarifas', Icono: CircleDollarSign },
  { ruta: '/configuracion', texto: 'Configuración', Icono: Settings },
]

function EstadoSistema() {
  const { conectado, estado } = useVivo()
  const ocr = estado?.ocr === 'listo' ? 'OCR operativo' : estado?.ocr === 'error' ? 'OCR con errores' : 'Cargando OCR'
  return (
    <div className="sistema" role="status">
      <span className={conectado ? 'sistema__punto sistema__punto--ok' : 'sistema__punto'} aria-hidden="true" />
      <span>{conectado ? ocr : 'Reconectando…'}</span>
    </div>
  )
}

function App() {
  return (
    <div className="marco">
      <a className="saltar" href="#contenido">Saltar al contenido</a>
      <aside className="lateral">
        <div className="marca">
          <span className="marca__logo" aria-hidden="true">P</span>
          <span>SmartPark</span>
        </div>
        <nav aria-label="Principal">
          {SECCIONES.map(({ ruta, texto, Icono }) => (
            <NavLink key={ruta} to={ruta} end={ruta === '/'}>
              <Icono size={18} aria-hidden="true" />
              <span>{texto}</span>
            </NavLink>
          ))}
        </nav>
        <EstadoSistema />
      </aside>
      <main id="contenido" className="principal">
        <Routes>
          <Route path="/" element={<EnVivo />} />
          <Route path="/registros" element={<Registros />} />
          <Route path="/reportes" element={<Reportes />} />
          <Route path="/tarifas" element={<Tarifas />} />
          <Route path="/configuracion" element={<Ajustes />} />
        </Routes>
      </main>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ProveedorVivo>
        <App />
      </ProveedorVivo>
    </BrowserRouter>
  </StrictMode>,
)
