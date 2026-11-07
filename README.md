# Parqueo

App de escritorio que lee placas de vehículos desde video y gestiona las entradas, salidas y cobros de un estacionamiento.

## Qué hace

- Procesa video y detecta placas con OpenCV y EasyOCR.
- Distingue entradas y salidas según la zona del video donde aparece el vehículo.
- Valida placas con formato `ABC-123` o `ABC123`.
- Evita registrar una entrada doble o una salida sin entrada previa.
- Calcula el monto según el tiempo de permanencia y la tarifa por hora.
- Guarda vehículos, tarifas y tickets en una base de datos SQLite local.
- Muestra el video, las detecciones, los vehículos activos y la actividad en una interfaz de escritorio.

## Tecnologías

Python · CustomTkinter · OpenCV · EasyOCR · NumPy · SQLite

## Requisitos

- Python 3.10 o superior
- GPU opcional para acelerar EasyOCR

## Instalación

```bash
git clone https://github.com/Dgirto/parqueo.git
cd parqueo/parqueo
python -m venv .venv
```

Activa el entorno virtual e instala las dependencias:

```bash
# Windows
.venv\Scripts\activate

# macOS o Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuración

La app usa por defecto el video de prueba `assets/videos/test.mp4`. Puedes ajustar estos valores en `app/core/config.py`:

| Variable | Qué controla |
|---|---|
| `VIDEO_PATH` | Video que procesa la app |
| `OCR_INTERVAL_SECONDS` | Tiempo entre lecturas de OCR |
| `OCR_CONFIDENCE_MIN` | Confianza mínima para aceptar una lectura |
| `ROI_ENTRADA` y `ROI_SALIDA` | Zonas del video para entradas y salidas |

La tarifa inicial se define en `app/database/schema.sql`.

## Uso

Desde la carpeta `parqueo/parqueo`:

```bash
python main.py
```

La base de datos se crea en `data/parqueo.db` al iniciar la app.

Para generar otra vez el video de prueba de 60 segundos:

```bash
python generate_test_video.py
```

## Pruebas

`pytest` no está incluido en `requirements.txt`, así que instálalo primero:

```bash
pip install pytest
python -m pytest tests
```

## Estructura

```text
parqueo/
├── app/
│   ├── core/       # Configuración, tema y reglas del estacionamiento
│   ├── database/   # Esquema, modelos y acceso a SQLite
│   ├── ui/         # Interfaz de escritorio
│   └── vision/     # Captura de video y lectura de placas
├── assets/videos/  # Video de prueba
├── data/           # Base de datos local
├── tests/          # Pruebas
├── generate_test_video.py
└── main.py
```
