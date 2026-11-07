import os
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.main import crear_app
from app.api.monitor import Monitor
from app.core.parking_logic import ParkingLogic
from app.database.db_manager import DatabaseManager


class MonitorDePrueba(Monitor):
    """Monitor real sin hilos de video ni OCR: las lecturas se inyectan a mano."""

    def iniciar(self, loop):
        self._loop = loop

    def detener(self):
        pass


@pytest.fixture
def entorno():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        ruta = os.path.join(tmp, "api.db")
        db = DatabaseManager(ruta)
        db.initialize()
        monitor = MonitorDePrueba(ParkingLogic(db), "sin-video")
        with TestClient(crear_app(ruta, monitor)) as cliente:
            yield cliente, monitor, db


def leer(monitor, placa, accion):
    return monitor.procesar_lectura({"placa": placa, "accion": accion, "confianza": 0.9})


def test_entrada_y_salida_generan_un_solo_ticket(entorno):
    cliente, monitor, _ = entorno
    assert leer(monitor, "ABC-123", "ENTRADA")["accion"] == "ENTRADA"
    evento = leer(monitor, "ABC-123", "SALIDA")
    assert evento["accion"] == "SALIDA"
    assert evento["ticket"]["estado"] == "CERRADO"
    datos = cliente.get("/api/tickets").json()
    assert datos["total"] == 1
    assert datos["items"][0]["estado"] == "CERRADO"
    assert datos["items"][0]["monto"] > 0


def test_doble_entrada_no_duplica(entorno):
    cliente, monitor, _ = entorno
    leer(monitor, "ABC-123", "ENTRADA")
    assert leer(monitor, "ABC-123", "ENTRADA")["accion"] == "YA_DENTRO"
    assert cliente.get("/api/tickets").json()["total"] == 1


def test_salida_sin_entrada_se_ignora(entorno):
    cliente, monitor, _ = entorno
    assert leer(monitor, "ABC-123", "SALIDA")["accion"] == "NO_DENTRO"
    assert cliente.get("/api/tickets").json()["total"] == 0


def test_salida_manual(entorno):
    cliente, monitor, _ = entorno
    ticket = leer(monitor, "DEF-789", "ENTRADA")["ticket"]
    r = cliente.post(f"/api/tickets/{ticket['id']}/salida")
    assert r.status_code == 200
    assert r.json()["estado"] == "CERRADO"
    assert cliente.post(f"/api/tickets/{ticket['id']}/salida").status_code == 404


def test_filtros_y_busqueda(entorno):
    cliente, monitor, _ = entorno
    leer(monitor, "ABC-123", "ENTRADA")
    leer(monitor, "XYZ-456", "ENTRADA")
    leer(monitor, "XYZ-456", "SALIDA")
    assert cliente.get("/api/tickets?estado=ACTIVO").json()["total"] == 1
    assert cliente.get("/api/tickets?q=xyz").json()["items"][0]["placa"] == "XYZ-456"
    assert cliente.get("/api/tickets?estado=OTRO").status_code == 422
    assert cliente.get("/api/tickets?desde=ayer").status_code == 422


def test_resumen_cuenta_dentro_y_cobros(entorno):
    cliente, monitor, _ = entorno
    leer(monitor, "ABC-123", "ENTRADA")
    leer(monitor, "XYZ-456", "ENTRADA")
    leer(monitor, "XYZ-456", "SALIDA")
    r = cliente.get("/api/resumen").json()
    assert r["dentro"] == 1
    assert r["libres"] == 19
    assert r["cobros"] == 1
    assert r["ingresos"] > 0


def test_tarifa_se_aplica_al_cobrar(entorno):
    cliente, monitor, _ = entorno
    assert cliente.put("/api/tarifas/1", json={"precio_hora": 60}).status_code == 200
    leer(monitor, "ABC-123", "ENTRADA")
    assert leer(monitor, "ABC-123", "SALIDA")["ticket"]["monto"] == 1.0


def test_tarifa_invalida(entorno):
    cliente, _, _ = entorno
    assert cliente.put("/api/tarifas/1", json={"precio_hora": 0}).status_code == 422
    assert cliente.put("/api/tarifas/99", json={"precio_hora": 5}).status_code == 404


def test_capacidad(entorno):
    cliente, _, _ = entorno
    assert cliente.put("/api/ajustes", json={"capacidad": 40}).json()["capacidad"] == 40
    assert cliente.get("/api/resumen").json()["libres"] == 40
    assert cliente.put("/api/ajustes", json={"capacidad": 0}).status_code == 422


def test_limpiar_exige_confirmacion(entorno):
    cliente, monitor, _ = entorno
    leer(monitor, "ABC-123", "ENTRADA")
    r = cliente.request("DELETE", "/api/tickets", json={"confirmacion": "si"})
    assert r.status_code == 400
    assert cliente.get("/api/tickets").json()["total"] == 1
    r = cliente.request("DELETE", "/api/tickets", json={"confirmacion": "BORRAR"})
    assert r.json()["borrados"] == 1


def test_csv(entorno):
    cliente, monitor, _ = entorno
    leer(monitor, "ABC-123", "ENTRADA")
    r = cliente.get("/api/tickets.csv")
    assert r.headers["content-type"].startswith("text/csv")
    assert "ABC-123" in r.text


def test_reporte(entorno):
    cliente, monitor, _ = entorno
    leer(monitor, "ABC-123", "ENTRADA")
    leer(monitor, "ABC-123", "SALIDA")
    r = cliente.get("/api/reportes?dias=7").json()
    assert len(r["por_dia"]) == 7
    assert len(r["por_hora"]) == 24
    assert r["por_dia"][-1]["salidas"] == 1
    assert sum(h["entradas"] for h in r["por_hora"]) == 1


def test_websocket_rechaza_otro_origen(entorno):
    cliente, _, _ = entorno
    with pytest.raises(Exception):
        with cliente.websocket_connect("/api/eventos", headers={"origin": "https://ajeno.example"}) as ws:
            ws.receive_json()


def test_host_no_permitido(entorno):
    cliente, _, _ = entorno
    assert cliente.get("/api/estado", headers={"host": "ajeno.example"}).status_code == 400
