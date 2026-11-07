"""Compone assets/videos/test.mp4: una cámara de seguridad simulada con autos fotorrealistas.

Las imágenes de `assets/escena/` son generadas por IA y las placas son ficticias. El script recorta
cada auto, le pone su placa y lo anima con perspectiva, sombra, barrera y acabado de cámara.
"""
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ESCENA = os.path.join(BASE, "assets", "escena")
SALIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "assets", "videos", "test.mp4")

W, H, FPS = 1280, 720, 30
DURACION = 60
Y_LEJOS, Y_STOP_IN, Y_STOP_OUT = 205, 520, 545
Y_BARRERA_IN, Y_BARRERA_OUT = 600, 430
FUENTE = "C:/Windows/Fonts/arialbd.ttf"

# Placas en coordenadas de la imagen original de 1264 × 1264.
PLACAS = {
    "plateado-frente": (476, 746, 788, 835),
    "plateado-atras": (478, 552, 788, 651),
    "azul-frente": (451, 733, 813, 815),
    "azul-atras": (489, 518, 775, 598),
}


# ── Geometría de la calzada ────────────────────────────────────────

def borde_izq(y):
    return 430 - (y - 190) * 0.915


def borde_der(y):
    return 855 + (y - 190) * 1.01


def centro_y_ancho(y, carril):
    izq, der = borde_izq(y), borde_der(y)
    mitad = (izq + der) / 2
    centro = (izq + mitad) / 2 if carril == "entrada" else (mitad + der) / 2
    return centro, (der - izq) / 2


# ── Recursos ───────────────────────────────────────────────────────

def recortar_auto(bgr):
    """Quita el fondo blanco de estudio por inundación desde los bordes."""
    alto, ancho = bgr.shape[:2]
    gris = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    claro = (gris > 205).astype(np.uint8)
    _, etiquetas = cv2.connectedComponents(claro)
    bordes = np.unique(np.concatenate([etiquetas[0], etiquetas[-1], etiquetas[:, 0], etiquetas[:, -1]]))
    fondo = np.isin(etiquetas, bordes[bordes != 0])
    auto = (~fondo).astype(np.uint8) * 255

    # Se queda con la pieza mayor y rellena sus huecos (parabrisas, brillos).
    n, comp, stats, _ = cv2.connectedComponentsWithStats(auto)
    mayor = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    auto = (comp == mayor).astype(np.uint8) * 255
    contornos, _ = cv2.findContours(auto, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    relleno = np.zeros_like(auto)
    cv2.drawContours(relleno, contornos, -1, 255, -1)
    relleno = cv2.morphologyEx(relleno, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    relleno = cv2.erode(relleno, np.ones((3, 3), np.uint8))
    x, y, w, h = cv2.boundingRect(relleno)

    # Bajo el auto queda la sombra clara del estudio: se conservan solo llantas y zonas oscuras.
    corte = y + int(h * 0.84)
    claro_bajo = gris[corte:y + h, :] > 95
    relleno[corte:y + h, :][claro_bajo] = 0
    relleno[corte:y + h, :] = cv2.morphologyEx(relleno[corte:y + h, :], cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))

    alfa = cv2.GaussianBlur(relleno, (5, 5), 0)
    return np.dstack([bgr, alfa])[y:y + h, x:x + w], (x, y)


def dibujar_placa(texto, ancho, alto):
    """Placa ficticia con el aspecto de las peruanas: banda azul y caracteres negros."""
    esc = 4
    W_p, H_p = ancho * esc, alto * esc
    img = Image.new("RGB", (W_p, H_p), (238, 238, 232))
    d = ImageDraw.Draw(img)
    banda = int(H_p * 0.21)
    d.rectangle([0, 0, W_p, banda], fill=(24, 58, 130))
    tam_b = int(banda * 0.8)
    f_b = ImageFont.truetype(FUENTE, tam_b)
    d.text((W_p / 2, banda / 2), "PERU", font=f_b, fill=(240, 240, 240), anchor="mm")
    tam = int((H_p - banda) * 0.86)
    f = ImageFont.truetype(FUENTE, tam)
    while d.textlength(texto, font=f) > W_p * 0.93:
        tam -= 4
        f = ImageFont.truetype(FUENTE, tam)
    d.text((W_p / 2, banda + (H_p - banda) * 0.52), texto, font=f, fill=(14, 14, 14), anchor="mm")
    d.rectangle([0, 0, W_p - 1, H_p - 1], outline=(30, 30, 30), width=esc * 2)
    return cv2.cvtColor(np.array(img.resize((ancho, alto), Image.LANCZOS)), cv2.COLOR_RGB2BGR)


def a_rojo(bgr):
    """Convierte la carrocería azul en roja para sumar un tercer auto."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    azul = (hsv[..., 0] > 95) & (hsv[..., 0] < 135) & (hsv[..., 1] > 55)
    mascara = cv2.GaussianBlur(azul.astype(np.float32), (7, 7), 0)
    rojo = hsv.copy()
    rojo[..., 0] = 176
    rojo[..., 1] = np.clip(hsv[..., 1] * 1.05, 0, 255)
    rojo[..., 2] = np.clip(hsv[..., 2] * 1.55 + 18, 0, 255)
    salida = cv2.cvtColor(rojo.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    m = mascara[..., None]
    return (salida * m + bgr.astype(np.float32) * (1 - m)).astype(np.uint8)


def preparar_auto(archivo, placa, rojo=False):
    bgr = cv2.imread(os.path.join(ESCENA, f"{archivo}.png"))
    x1, y1, x2, y2 = PLACAS[archivo]
    hoja = dibujar_placa(placa, x2 - x1, y2 - y1)
    if rojo:
        bgr = a_rojo(bgr)
    bgr[y1:y2, x1:x2] = hoja
    # Integra el auto de estudio con la luz nublada de la escena.
    bgr = np.clip(bgr.astype(np.float32) * 0.86 + 6, 0, 255).astype(np.uint8)
    sprite, _ = recortar_auto(bgr)
    return sprite


# ── Composición ────────────────────────────────────────────────────

def pegar(destino, sprite, cx, base_y, ancho, opacidad=1.0, estela=0):
    alto = int(sprite.shape[0] * ancho / sprite.shape[1])
    if ancho < 8 or alto < 8:
        return
    pieza = cv2.resize(sprite, (int(ancho), alto), interpolation=cv2.INTER_AREA)
    if estela >= 3:
        k = np.zeros((estela | 1, estela | 1), np.float32)
        k[:, (estela | 1) // 2] = 1 / (estela | 1)
        pieza = cv2.filter2D(pieza, -1, k)
    x, y = int(cx - pieza.shape[1] / 2), int(base_y - alto)
    x1, y1, x2, y2 = max(0, x), max(0, y), min(W, x + pieza.shape[1]), min(H, y + alto)
    if x1 >= x2 or y1 >= y2:
        return
    p = pieza[y1 - y:y2 - y, x1 - x:x2 - x].astype(np.float32)
    a = p[..., 3:] / 255 * opacidad
    destino[y1:y2, x1:x2] = p[..., :3] * a + destino[y1:y2, x1:x2] * (1 - a)


def sombra(destino, cx, base_y, ancho):
    if ancho < 20:
        return
    capa = np.zeros((H, W), np.float32)
    ejes = (int(ancho * 0.56), int(ancho * 0.1))
    cv2.ellipse(capa, (int(cx), int(base_y - ancho * 0.015)), ejes, 0, 0, 360, 1.0, -1)
    r = int(ancho * 0.05) | 1
    capa = cv2.GaussianBlur(capa, (r, r), 0)[..., None]
    destino *= 1 - capa * 0.62


def barrera(destino, pivote, largo, angulo):
    """Poste y brazo con franjas. angulo: 0 cerrada, 88 abierta."""
    x, y = pivote
    a = math.radians(angulo)
    sentido = 1 if largo > 0 else -1
    cv2.rectangle(destino, (x - 17, y - 8), (x + 17, y + 138), (66, 72, 78), -1, cv2.LINE_AA)
    cv2.rectangle(destino, (x - 17, y - 8), (x - 8, y + 138), (92, 98, 104), -1, cv2.LINE_AA)
    cv2.rectangle(destino, (x - 26, y + 130), (x + 26, y + 144), (46, 48, 52), -1, cv2.LINE_AA)
    n = 8
    for i in range(n):
        t1, t2 = i / n, (i + 1) / n
        p1 = (x + sentido * abs(largo) * t1 * math.cos(a), y - abs(largo) * t1 * math.sin(a))
        p2 = (x + sentido * abs(largo) * t2 * math.cos(a), y - abs(largo) * t2 * math.sin(a))
        color = (42, 42, 190) if i % 2 == 0 else (225, 228, 228)
        cv2.line(destino, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), color, 13, cv2.LINE_AA)
    cv2.circle(destino, (x, y), 15, (46, 48, 52), -1, cv2.LINE_AA)


def suave(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def entrada(t):
    """(y del suelo, opacidad, apertura de barrera, velocidad) para un auto que entra."""
    if t < 3.2:
        k = 1 - (1 - t / 3.2) ** 2.4
        y = Y_LEJOS + (Y_STOP_IN - Y_LEJOS) * k
        v = (Y_STOP_IN - Y_LEJOS) * 2.4 * (1 - t / 3.2) ** 1.4 / 3.2 / FPS
    elif t < 6.6:
        y, v = Y_STOP_IN, 0
    else:
        k = (t - 6.6) / 2.4
        y = Y_STOP_IN + 560 * k ** 2.1
        v = 560 * 2.1 * k ** 1.1 / 2.4 / FPS
    apertura = suave((t - 5.2) / 1.3) - suave((t - 9.4) / 1.5)
    return y, min(1.0, t / 0.5), apertura, v


def salida(t):
    """Igual que `entrada`, para un auto que se aleja de espaldas."""
    if t < 3.0:
        k = 1 - (1 - t / 3.0) ** 2.4
        y = 1000 + (Y_STOP_OUT - 1000) * k
        v = (1000 - Y_STOP_OUT) * 2.4 * (1 - t / 3.0) ** 1.4 / 3.0 / FPS
    elif t < 6.6:
        y, v = Y_STOP_OUT, 0
    else:
        k = min(1.0, (t - 6.6) / 3.2)
        y = Y_STOP_OUT + (Y_LEJOS - Y_STOP_OUT) * (1 - (1 - k) ** 1.7) if k < 1 else Y_LEJOS
        v = 0
    apertura = suave((t - 5.2) / 1.3) - suave((t - 9.6) / 1.5)
    return y, 1.0 - suave((t - 9.3) / 0.6), apertura, v


def main():
    fondo = cv2.resize(cv2.imread(os.path.join(ESCENA, "fondo.png")), (W, H), interpolation=cv2.INTER_AREA)
    fondo = cv2.addWeighted(fondo, 0.94, np.full_like(fondo, 92), 0.06, 0).astype(np.float32)

    plateado = (preparar_auto("plateado-frente", "ABC-123"), preparar_auto("plateado-atras", "ABC-123"))
    azul = (preparar_auto("azul-frente", "XYZ-456"), preparar_auto("azul-atras", "XYZ-456"))
    rojo = preparar_auto("azul-frente", "K7R-352", rojo=True)

    eventos = [
        (0, plateado[0], 0.76, "entrada"),
        (12, azul[0], 0.80, "entrada"),
        (24, plateado[1], 0.76, "salida"),
        (36, rojo, 0.80, "entrada"),
        (48, azul[1], 0.80, "salida"),
    ]

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    video = cv2.VideoWriter(SALIDA, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    rng = np.random.default_rng(7)
    borde_v = np.fromfunction(lambda y, x: 1 - 0.28 * (((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2) / 2, (H, W), dtype=np.float32)[..., None]

    izq_in, largo_in = (int(borde_izq(Y_BARRERA_IN)) + 34, Y_BARRERA_IN - 235), 490
    der_out, largo_out = (int(borde_der(Y_BARRERA_OUT)) - 22, Y_BARRERA_OUT - 150), -340

    for f in range(DURACION * FPS):
        t = f / FPS
        lienzo = fondo.copy()
        lienzo *= 1 + 0.012 * math.sin(t * 0.7)   # la luz nublada cambia apenas

        giro_in, giro_out = 0.0, 0.0
        auto = None
        for inicio, sprite, proporcion, carril in eventos:
            if inicio <= t < inicio + 12:
                local = t - inicio
                y, opacidad, apertura, v = (entrada if carril == "entrada" else salida)(local)
                if carril == "entrada":
                    giro_in = apertura
                else:
                    giro_out = apertura
                auto = (sprite, proporcion, carril, y, opacidad, v, local)

        def dibujar_auto():
            sprite, proporcion, carril, y, opacidad, v, local = auto
            cx, carril_w = centro_y_ancho(min(y, 900), carril)
            ancho = carril_w * proporcion
            rebote = math.sin(local * 9) * 0.7 if v > 0.4 else 0
            if opacidad > 0.02:
                sombra(lienzo, cx, y, ancho)
                pegar(lienzo, sprite, cx, y + rebote, ancho, opacidad, int(v * 1.1))

        # Orden por profundidad: lo más cercano a la cámara se dibuja al final.
        auto_detras_out = auto is not None and auto[3] > Y_BARRERA_OUT
        if not auto_detras_out and auto is not None:
            dibujar_auto()
        barrera(lienzo, der_out, largo_out, giro_out * 86)
        if auto_detras_out:
            dibujar_auto()
        barrera(lienzo, izq_in, largo_in, giro_in * 86)

        imagen = cv2.GaussianBlur(lienzo, (3, 3), 0.55) * borde_v
        imagen += rng.normal(0, 3.2, imagen.shape).astype(np.float32)
        salida_f = np.clip(imagen, 0, 255).astype(np.uint8)

        segundos = int(t)
        cv2.putText(salida_f, f"CAM-01  ENTRADA PRINCIPAL  00:{segundos // 60:02d}:{segundos % 60:02d}", (22, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.56, (235, 235, 235), 1, cv2.LINE_AA)
        video.write(salida_f)

    video.release()
    print("Listo:", SALIDA)


if __name__ == "__main__":
    main()
