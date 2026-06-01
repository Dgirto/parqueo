import os
import tempfile
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database.db_manager import DatabaseManager
from app.core.config import SCHEMA_PATH


@pytest.fixture
def db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = DatabaseManager(db_path)
        manager.initialize()
        yield manager


def test_initialize_creates_tables(db):
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert {"tarifas", "vehiculos", "tickets"}.issubset(tables)


def test_registrar_entrada(db):
    ticket = db.registrar_entrada("ABC-123")
    assert ticket is not None
    assert ticket.placa == "ABC-123"
    assert ticket.estado == "ACTIVO"


def test_get_ticket_activo(db):
    db.registrar_entrada("ABC-123")
    ticket = db.get_ticket_activo("ABC-123")
    assert ticket is not None
    assert ticket.placa == "ABC-123"


def test_registrar_salida(db):
    db.registrar_entrada("DEF-456")
    ticket = db.registrar_salida("DEF-456")
    assert ticket is not None
    assert ticket.estado == "CERRADO"
    assert ticket.minutos is not None
    assert ticket.monto is not None


def test_no_ticket_activo_after_salida(db):
    db.registrar_entrada("GHI-789")
    db.registrar_salida("GHI-789")
    assert db.get_ticket_activo("GHI-789") is None


def test_get_vehiculos_dentro(db):
    db.registrar_entrada("AAA-001")
    db.registrar_entrada("BBB-002")
    dentro = db.get_vehiculos_dentro()
    placas = {t.placa for t in dentro}
    assert "AAA-001" in placas
    assert "BBB-002" in placas


def test_get_historial(db):
    db.registrar_entrada("ZZZ-999")
    db.registrar_salida("ZZZ-999")
    historial = db.get_historial()
    assert any(t.placa == "ZZZ-999" for t in historial)
