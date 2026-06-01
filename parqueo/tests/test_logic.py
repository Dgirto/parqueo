import os
import tempfile
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database.db_manager import DatabaseManager
from app.core.parking_logic import ParkingLogic


@pytest.fixture
def logic():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        db.initialize()
        yield ParkingLogic(db)


def test_validar_placa_valida(logic):
    assert logic.validar_formato_placa("ABC-123") is True
    assert logic.validar_formato_placa("ABC123") is True


def test_validar_placa_invalida(logic):
    assert logic.validar_formato_placa("AB-123") is False
    assert logic.validar_formato_placa("ABCD-123") is False
    assert logic.validar_formato_placa("ABC-12") is False
    assert logic.validar_formato_placa("") is False


def test_calcular_monto(logic):
    # 60 minutos a 5.00/hora = 5.00
    assert logic.calcular_monto(60, 5.00) == 5.00
    # 30 minutos = 2.50
    assert logic.calcular_monto(30, 5.00) == 2.50


def test_procesar_placa_entrada(logic):
    result = logic.procesar_placa("XYZ-321")
    assert result["accion"] == "ENTRADA"
    assert result["placa"] == "XYZ-321"


def test_procesar_placa_salida(logic):
    logic.procesar_placa("XYZ-321")
    result = logic.procesar_placa("XYZ-321")
    assert result["accion"] == "SALIDA"
    assert result["monto"] is not None


def test_procesar_placa_invalida(logic):
    result = logic.procesar_placa("INVALID")
    assert result["accion"] == "INVALIDA"
