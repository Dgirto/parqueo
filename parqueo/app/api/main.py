"""API de SmartPark. Está pensada para una red local: por defecto solo escucha en 127.0.0.1."""
import asyncio
import csv
import io
import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.api.monitor import Monitor
from app.core.config import (DB_PATH, FRAME_ALTO, FRAME_ANCHO, ROI_ENTRADA, ROI_SALIDA,
                             VIDEO_PATH, WEB_DIST)
from app.core.parking_logic import ParkingLogic
from app.database.db_manager import DatabaseManager

FECHA = r"^\d{4}-\d{2}-\d{2}$"
HOSTS_LOCALES = {"localhost", "127.0.0.1"}


class TarifaEntrada(BaseModel):
    precio_hora: float = Field(gt=0, le=1000)


class AjustesEntrada(BaseModel):
    capacidad: int = Field(ge=1, le=10000)


class LimpiezaEntrada(BaseModel):
    confirmacion: str


def crear_app(db_path: str = DB_PATH, monitor: Optional[Monitor] = None) -> FastAPI:
    db = DatabaseManager(db_path)
    db.initialize()
    logic = ParkingLogic(db)
    mon = monitor or Monitor(logic, VIDEO_PATH)

    @asynccontextmanager
    async def ciclo(_: FastAPI):
        mon.iniciar(asyncio.get_running_loop())
        yield
        mon.detener()

    app = FastAPI(title="SmartPark API", lifespan=ciclo)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[*HOSTS_LOCALES, "testserver"])

    def notificar_cambio() -> None:
        mon.publicar({"tipo": "cambio"})

    # ── Estado y resumen ───────────────────────────────────────────

    @app.get("/api/estado")
    def estado():
        return {
            **mon.estado(),
            "frame": {"ancho": FRAME_ANCHO, "alto": FRAME_ALTO},
            "zonas": {"entrada": ROI_ENTRADA, "salida": ROI_SALIDA},
        }

    @app.get("/api/resumen")
    def resumen():
        return db.resumen_hoy()

    @app.get("/api/reportes")
    def reportes(dias: int = Query(7, ge=1, le=90)):
        return db.reporte(dias)

    # ── Tickets ────────────────────────────────────────────────────

    @app.get("/api/tickets")
    def tickets(
        estado: Optional[str] = Query(None, pattern="^(ACTIVO|CERRADO)$"),
        q: str = Query("", max_length=10),
        desde: Optional[str] = Query(None, pattern=FECHA),
        hasta: Optional[str] = Query(None, pattern=FECHA),
        limite: int = Query(25, ge=1, le=200),
        inicio: int = Query(0, ge=0),
    ):
        items, total = db.listar_tickets(estado, q, desde, hasta, limite, inicio)
        return {"items": [asdict(t) for t in items], "total": total}

    @app.get("/api/tickets.csv")
    def tickets_csv(
        estado: Optional[str] = Query(None, pattern="^(ACTIVO|CERRADO)$"),
        q: str = Query("", max_length=10),
        desde: Optional[str] = Query(None, pattern=FECHA),
        hasta: Optional[str] = Query(None, pattern=FECHA),
    ):
        items, _ = db.listar_tickets(estado, q, desde, hasta, 10000, 0)
        salida = io.StringIO()
        escritor = csv.writer(salida)
        escritor.writerow(["ticket", "placa", "entrada", "salida", "minutos", "monto", "estado"])
        for t in items:
            escritor.writerow([t.id, t.placa, t.hora_entrada, t.hora_salida or "",
                               t.minutos or "", t.monto if t.monto is not None else "", t.estado])
        return Response(salida.getvalue(), media_type="text/csv; charset=utf-8", headers={
            "Content-Disposition": 'attachment; filename="tickets-smartpark.csv"',
        })

    @app.post("/api/tickets/{ticket_id}/salida")
    def registrar_salida(ticket_id: int):
        ticket = db.registrar_salida_por_id(ticket_id)
        if ticket is None:
            raise HTTPException(404, "No hay un ticket activo con ese número")
        evento = {"tipo": "deteccion", "accion": "SALIDA", "placa": ticket.placa,
                  "hora": ticket.hora_salida, "confianza": None, "manual": True,
                  "ticket": asdict(ticket)}
        mon.publicar(evento)
        return asdict(ticket)

    @app.delete("/api/tickets")
    def limpiar_tickets(entrada: LimpiezaEntrada):
        if entrada.confirmacion != "BORRAR":
            raise HTTPException(400, "Escribe BORRAR para confirmar")
        borrados = db.clear_all_tickets()
        notificar_cambio()
        return {"borrados": borrados}

    # ── Tarifas y ajustes ──────────────────────────────────────────

    @app.get("/api/tarifas")
    def tarifas():
        return [asdict(t) for t in db.listar_tarifas()]

    @app.put("/api/tarifas/{tarifa_id}")
    def actualizar_tarifa(tarifa_id: int, entrada: TarifaEntrada):
        tarifa = db.actualizar_tarifa(tarifa_id, entrada.precio_hora)
        if tarifa is None:
            raise HTTPException(404, "Tarifa no encontrada")
        notificar_cambio()
        return asdict(tarifa)

    @app.get("/api/ajustes")
    def ajustes():
        return {"capacidad": db.get_capacidad()}

    @app.put("/api/ajustes")
    def actualizar_ajustes(entrada: AjustesEntrada):
        db.set_capacidad(entrada.capacidad)
        notificar_cambio()
        return {"capacidad": entrada.capacidad}

    # ── Tiempo real ────────────────────────────────────────────────

    @app.get("/api/camara.mjpeg")
    async def camara(request: Request):
        async def emitir():
            ultimo = -1
            while not await request.is_disconnected():
                secuencia, jpeg = mon.ultimo_frame()
                if jpeg and secuencia != ultimo:
                    ultimo = secuencia
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                           + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
                await asyncio.sleep(1 / 30)

        return StreamingResponse(emitir(), media_type="multipart/x-mixed-replace; boundary=frame",
                                 headers={"Cache-Control": "no-store"})

    @app.websocket("/api/eventos")
    async def eventos(ws: WebSocket):
        origen = ws.headers.get("origin")
        if origen and urlparse(origen).hostname not in HOSTS_LOCALES:
            await ws.close(code=1008)
            return
        await ws.accept()
        cola = mon.suscribir()
        try:
            while True:
                try:
                    await ws.send_json(await asyncio.wait_for(cola.get(), timeout=20))
                except asyncio.TimeoutError:
                    await ws.send_json({"tipo": "latido"})
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            mon.desuscribir(cola)

    # ── Sitio compilado ────────────────────────────────────────────

    if os.path.isdir(WEB_DIST):
        app.mount("/assets", StaticFiles(directory=os.path.join(WEB_DIST, "assets")), name="assets")

        @app.get("/{ruta:path}", include_in_schema=False)
        def sitio(ruta: str):
            if ruta.startswith("api/"):
                raise HTTPException(404)
            return FileResponse(os.path.join(WEB_DIST, "index.html"))

    return app
