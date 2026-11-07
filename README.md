# SmartPark

Sistema web para controlar un estacionamiento: lee las placas en el video de la cámara, abre y cierra tickets, y calcula el cobro según los minutos y la tarifa.

## Qué hace

- **En vivo:** video de la cámara, zonas de entrada y salida, última lectura, vehículos dentro y salida manual.
- **Registros:** historial con búsqueda, filtros por estado y fecha, paginación y exportación a CSV.
- **Reportes:** ingresos por día, entradas por hora y permanencia promedio.
- **Tarifas y configuración:** precio por hora, capacidad del local y estado del sistema.

## Tecnologías

| Parte | Herramientas |
| --- | --- |
| Visión | OpenCV, EasyOCR |
| API | Python, FastAPI, WebSocket, video MJPEG |
| Datos | SQLite |
| Web | React 19, TypeScript, Vite |
| Pruebas | pytest |

La captura, el OCR y el registro corren en hilos separados, de modo que el reconocimiento no frena el video. El OCR siempre analiza la imagen más reciente y solo gasta tiempo en las zonas con un vehículo; en una CPU sin GPU, la lectura llega con unos 2 s de retraso (`python scripts/probar_sincronia.py` lo comprueba). Los cambios llegan a la web por WebSocket.

## Puesta en marcha

Requiere Python 3.11 o superior y Node.js 20 o superior.

```bash
cd parqueo
python -m venv .venv
.venv/Scripts/activate            # en Linux o macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
python scripts/componer_video.py  # video de cámara compuesto con assets/escena
cd web && npm install && npm run build && cd ..
python main.py                    # http://127.0.0.1:8100
```

La primera ejecución descarga los modelos de EasyOCR. Para desarrollar la web con recarga en caliente, deja `python main.py` corriendo y ejecuta `npm run dev` dentro de `web/` (http://localhost:5180).

El video de prueba es una composición: las imágenes de `assets/escena/` están generadas por IA y las placas son ficticias. Para comprobar que el OCR lee cada placa, ejecuta `python scripts/probar_ocr.py`.

Para ver Reportes con historial de ejemplo, ejecuta `python scripts/sembrar_demo.py` con la base vacía. Esos tickets son de demostración.

| Variable | Valor por defecto | Uso |
| --- | --- | --- |
| `PARQUEO_VIDEO` | `assets/videos/test.mp4` | Video de entrada |
| `PARQUEO_DB` | `data/parqueo.db` | Base de datos SQLite |
| `PARQUEO_HOST` / `PARQUEO_PORT` | `127.0.0.1` / `8100` | Dirección del servidor |

## Pruebas

```bash
cd parqueo
python -m pytest
```

## Límites conocidos

El OCR puede confundir caracteres parecidos en placas que mezclan letras y números: en las pruebas leyó `D4F-789` como `DAF-789`, un formato válido que abriría un ticket con la placa equivocada. Por eso existe la salida manual, y en un despliegue real conviene revisar las lecturas de baja confianza.

## Seguridad

La aplicación no tiene inicio de sesión: está pensada para un equipo local y solo acepta peticiones dirigidas a `localhost` o `127.0.0.1`. Antes de exponerla en una red hay que agregar autenticación.
