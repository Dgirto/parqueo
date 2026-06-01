"""
Genera assets/videos/test.mp4 — simulación de cámara CCTV en entrada de parqueo.
60 segundos, 30 fps, 1280x720.
"""

import cv2
import numpy as np
import os
import random

# ── Configuración ──────────────────────────────────────────────────────────────
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "assets", "videos", "test.mp4")
W, H = 1280, 720
FPS = 30
TOTAL_FRAMES = 60 * FPS   # 1800

# Colores BGR
C_ASPHALT   = (42,  42,  42)
C_YELLOW    = (0,  200, 220)
C_WHITE     = (255, 255, 255)
C_BLACK     = (0,   0,   0)
C_RED       = (0,   0, 200)
C_GREY_CAR  = (140, 140, 140)
C_BLUE_CAR  = (160,  60,  20)
C_RED_CAR   = (30,   30, 160)
C_BARRIER   = (50,  200, 220)
C_GREEN     = (0,  200,  60)

# Posiciones clave
BARRIER_X   = 780          # x de la barrera vertical pivot
BARRIER_Y   = 360          # y del pivot de la barrera
STOP_X_L    = 220          # auto de SALIDA se detiene en zona izquierda (ROI_SALIDA)
STOP_X_R    = 980          # auto de ENTRADA se detiene en zona derecha (ROI_ENTRADA)
CAR_Y       = 400          # y centro del auto
CAR_W       = 190          # ancho del cuerpo
CAR_H       = 90           # alto del cuerpo


# ── Helpers de dibujo ──────────────────────────────────────────────────────────

def draw_background(frame):
    """Fondo de asfalto, líneas amarillas y texto estático."""
    frame[:] = C_ASPHALT
    # Líneas horizontales amarillas en el suelo
    cv2.line(frame, (0, 500), (W, 500), C_YELLOW, 4)
    cv2.line(frame, (0, 540), (W, 540), C_YELLOW, 4)
    # Texto ENTRADA
    cv2.putText(frame, "ENTRADA", (20, 44),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, C_WHITE, 2, cv2.LINE_AA)
    # Borde superior derecho estilo CCTV
    cv2.putText(frame, "CAM-01", (W - 160, 44),
                cv2.FONT_HERSHEY_DUPLEX, 0.9, C_WHITE, 1, cv2.LINE_AA)


def draw_timestamp(frame, frame_idx):
    total_sec = frame_idx // FPS
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    ts = f"{h:02d}:{m:02d}:{s:02d}"
    cv2.putText(frame, ts, (W - 200, 80),
                cv2.FONT_HERSHEY_DUPLEX, 0.85, C_WHITE, 1, cv2.LINE_AA)


def add_noise(frame, intensity=6):
    noise = np.random.randint(-intensity, intensity,
                              frame.shape, dtype=np.int16)
    noisy = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return noisy


def draw_barrier(frame, angle_deg: float):
    """
    Barrera horizontal anclada en BARRIER_X, BARRIER_Y.
    angle_deg=0   → horizontal (cerrada)
    angle_deg=-90 → vertical   (abierta)
    """
    length = 300
    rad = np.radians(angle_deg)
    ex = int(BARRIER_X + length * np.cos(rad))
    ey = int(BARRIER_Y + length * np.sin(rad))
    cv2.line(frame, (BARRIER_X, BARRIER_Y), (ex, ey), C_BARRIER, 8, cv2.LINE_AA)
    cv2.circle(frame, (BARRIER_X, BARRIER_Y), 10, C_YELLOW, -1)


def draw_car(frame, cx: int, cy: int, color, plate_text: str,
             facing_right: bool = True):
    """Dibuja un auto simplificado con carrocería, ruedas y placa."""
    half_w = CAR_W // 2
    half_h = CAR_H // 2

    # Sombra
    shadow_pts = np.array([
        [cx - half_w + 10, cy + half_h],
        [cx + half_w + 10, cy + half_h],
        [cx + half_w + 16, cy + half_h + 14],
        [cx - half_w + 4,  cy + half_h + 14],
    ], np.int32)
    cv2.fillPoly(frame, [shadow_pts], (20, 20, 20))

    # Carrocería principal
    cv2.rectangle(frame,
                  (cx - half_w, cy - half_h),
                  (cx + half_w, cy + half_h),
                  color, -1)

    # Techo (más pequeño y elevado)
    roof_w = int(CAR_W * 0.55)
    roof_h = int(CAR_H * 0.45)
    cv2.rectangle(frame,
                  (cx - roof_w // 2, cy - half_h - roof_h),
                  (cx + roof_w // 2, cy - half_h),
                  tuple(max(0, c - 25) for c in color), -1)

    # Borde carrocería
    cv2.rectangle(frame,
                  (cx - half_w, cy - half_h),
                  (cx + half_w, cy + half_h),
                  tuple(max(0, c - 40) for c in color), 2)

    # Ruedas (4 círculos negros)
    wheel_r = 18
    for wx, wy in [(cx - 55, cy + half_h - 4),
                   (cx + 55, cy + half_h - 4),
                   (cx - 55, cy - half_h + 4),
                   (cx + 55, cy - half_h + 4)]:
        cv2.circle(frame, (wx, wy), wheel_r, C_BLACK, -1)
        cv2.circle(frame, (wx, wy), wheel_r - 6, (60, 60, 60), -1)

    # Placa
    plate_w, plate_h = 130, 38
    px = cx - plate_w // 2
    if facing_right:
        py = cy + half_h - plate_h - 2   # placa delantera (mirando der)
    else:
        py = cy + half_h - plate_h - 2

    cv2.rectangle(frame, (px, py), (px + plate_w, py + plate_h),
                  C_WHITE, -1)
    cv2.rectangle(frame, (px, py), (px + plate_w, py + plate_h),
                  (0, 0, 180), 3)

    # Texto de la placa — centrado
    font = cv2.FONT_HERSHEY_DUPLEX
    scale = 0.85
    thickness = 2
    (tw, th), _ = cv2.getTextSize(plate_text, font, scale, thickness)
    tx = px + (plate_w - tw) // 2
    ty = py + (plate_h + th) // 2 - 2
    cv2.putText(frame, plate_text, (tx, ty), font, scale,
                C_BLACK, thickness, cv2.LINE_AA)


def lerp(a, b, t):
    return a + (b - a) * t


def ease_in_out(t):
    return t * t * (3 - 2 * t)


# ── Definición de eventos ──────────────────────────────────────────────────────
# Cada evento: (start_sec, end_sec, plate, color, direction)
# direction: "enter" (der→izq) | "exit" (izq→der)

EVENTS = [
    (0,  12, "ABC-123", C_GREY_CAR, "enter"),
    (12, 24, "XYZ-456", C_BLUE_CAR, "enter"),
    (24, 36, "ABC-123", C_GREY_CAR, "exit"),
    (36, 48, "DEF-789", C_RED_CAR,  "enter"),
    (48, 60, "XYZ-456", C_BLUE_CAR, "exit"),
]


def get_event_state(frame_idx):
    """
    Para el frame_idx dado, retorna los parámetros del evento activo.
    Devuelve None si no hay auto visible.
    """
    t_sec = frame_idx / FPS
    for (s, e, plate, color, direction) in EVENTS:
        if not (s <= t_sec < e):
            continue
        duration = e - s          # 12 s
        local_t  = t_sec - s      # 0..12

        # Sub-fases (en segundos dentro del evento):
        #  0.0 – 2.5  → acercamiento
        #  2.5 – 5.5  → detenido frente barrera
        #  5.5 – 7.0  → barrera sube
        #  7.0 – 10.0 → cruza y desaparece
        # 10.0 – 12.0 → barrera baja

        if direction == "enter":
            start_x = W + 50
            end_x   = -CAR_W - 50
            stop_x  = STOP_X_R
        else:  # exit
            start_x = -50
            end_x   = W + CAR_W + 50
            stop_x  = STOP_X_L

        barrier_angle = 0.0   # horizontal por defecto

        if local_t < 2.5:
            # Acercamiento
            progress = ease_in_out(local_t / 2.5)
            cx = int(lerp(start_x, stop_x, progress))
            visible = True
            barrier_angle = 0.0
        elif local_t < 5.5:
            # Detenido
            cx = stop_x
            visible = True
            barrier_angle = 0.0
        elif local_t < 7.0:
            # Barrera sube
            cx = stop_x
            visible = True
            sub_t = (local_t - 5.5) / 1.5
            barrier_angle = lerp(0, -90, ease_in_out(sub_t))
        elif local_t < 10.0:
            # Cruza
            sub_t = (local_t - 7.0) / 3.0
            cx = int(lerp(stop_x, end_x, ease_in_out(sub_t)))
            visible = True
            barrier_angle = -90.0
        else:
            # Barrera baja
            visible = False
            cx = end_x
            sub_t = (local_t - 10.0) / 2.0
            barrier_angle = lerp(-90, 0, ease_in_out(sub_t))

        facing_right = (direction == "enter")
        return {
            "visible": visible,
            "cx": cx,
            "color": color,
            "plate": plate,
            "facing_right": facing_right,
            "barrier_angle": barrier_angle,
            "direction": direction,
            "local_t": local_t,
        }
    return None


def draw_salida_flash(frame, frame_idx):
    """Parpadea texto SALIDA en rojo durante eventos de salida (2s tras detención)."""
    t_sec = frame_idx / FPS
    for (s, e, plate, color, direction) in EVENTS:
        if direction != "exit":
            continue
        local_t = t_sec - s
        # Aparece entre seg 2.5 y 4.5 (mientras está detenido)
        if 2.5 <= local_t <= 4.5:
            flash = int(local_t * FPS) % 20 < 10   # parpadea a ~3Hz
            if flash:
                cv2.putText(frame, "SALIDA", (W // 2 - 90, 80),
                            cv2.FONT_HERSHEY_DUPLEX, 1.8,
                            (0, 0, 255), 3, cv2.LINE_AA)


# ── Generación del video ───────────────────────────────────────────────────────

def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(OUTPUT_PATH, fourcc, FPS, (W, H))

    if not writer.isOpened():
        raise RuntimeError(f"No se pudo abrir el VideoWriter para {OUTPUT_PATH}")

    print(f"Generando {TOTAL_FRAMES} frames ({TOTAL_FRAMES // FPS}s a {FPS}fps)…")

    for fi in range(TOTAL_FRAMES):
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        draw_background(frame)

        state = get_event_state(fi)
        barrier_angle = state["barrier_angle"] if state else 0.0
        draw_barrier(frame, barrier_angle)

        if state and state["visible"]:
            draw_car(frame, state["cx"], CAR_Y,
                     state["color"], state["plate"],
                     state["facing_right"])

        draw_salida_flash(frame, fi)
        draw_timestamp(frame, fi)

        # Grano sutil
        frame = add_noise(frame, intensity=5)

        writer.write(frame)

        if fi % (FPS * 5) == 0:
            print(f"  {fi // FPS:3d}s / 60s …")

    writer.release()

    size_kb = os.path.getsize(OUTPUT_PATH) // 1024
    print(f"\nVideo generado exitosamente en {OUTPUT_PATH}")
    print(f"Tamaño: {size_kb} KB  |  Duración: 60s  |  Resolución: {W}x{H}")


if __name__ == "__main__":
    main()
