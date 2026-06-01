import sqlite3
import os
from datetime import datetime
from typing import Optional, List

from app.core.config import SCHEMA_PATH, TARIFA_ID_DEFAULT, PRECIO_HORA_DEFAULT
from app.database.models import Ticket, Tarifa


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")   # lecturas concurrentes sin bloquear escrituras
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self):
        schema_path = SCHEMA_PATH
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = f.read()
        with self._connect() as conn:
            conn.executescript(schema)

    def registrar_entrada(self, placa: str) -> Ticket:
        sql = """
            INSERT INTO tickets (placa, hora_entrada, tarifa_id, estado)
            VALUES (?, datetime('now','localtime'), ?, 'ACTIVO')
        """
        with self._connect() as conn:
            cur = conn.execute(sql, (placa.upper(), TARIFA_ID_DEFAULT))
            ticket_id = cur.lastrowid
        return self.get_ticket_activo(placa)

    def registrar_salida(self, placa: str) -> Optional[Ticket]:
        ticket = self.get_ticket_activo(placa)
        if ticket is None:
            return None

        hora_entrada = datetime.strptime(ticket.hora_entrada, "%Y-%m-%d %H:%M:%S")
        hora_salida = datetime.now()
        minutos = max(1, int((hora_salida - hora_entrada).total_seconds() / 60))

        tarifa = self._get_tarifa(ticket.tarifa_id)
        precio_hora = tarifa.precio_hora if tarifa else PRECIO_HORA_DEFAULT
        monto = round((minutos / 60) * precio_hora, 2)

        sql = """
            UPDATE tickets
            SET hora_salida = datetime('now','localtime'),
                minutos = ?,
                monto = ?,
                estado = 'CERRADO'
            WHERE id = ?
        """
        with self._connect() as conn:
            conn.execute(sql, (minutos, monto, ticket.id))

        return self._get_ticket_by_id(ticket.id)

    def get_ticket_activo(self, placa: str) -> Optional[Ticket]:
        sql = """
            SELECT * FROM tickets
            WHERE placa = ? AND estado = 'ACTIVO'
            ORDER BY hora_entrada DESC LIMIT 1
        """
        with self._connect() as conn:
            row = conn.execute(sql, (placa.upper(),)).fetchone()
        return self._row_to_ticket(row) if row else None

    def get_historial(self, limit: int = 50) -> List[Ticket]:
        sql = """
            SELECT * FROM tickets
            WHERE estado = 'CERRADO'
            ORDER BY hora_salida DESC LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
        return [self._row_to_ticket(r) for r in rows]

    def get_vehiculos_dentro(self) -> List[Ticket]:
        sql = """
            SELECT * FROM tickets
            WHERE estado = 'ACTIVO'
            ORDER BY hora_entrada DESC
        """
        with self._connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [self._row_to_ticket(r) for r in rows]

    def _get_tarifa(self, tarifa_id: int) -> Optional[Tarifa]:
        sql = "SELECT * FROM tarifas WHERE id = ?"
        with self._connect() as conn:
            row = conn.execute(sql, (tarifa_id,)).fetchone()
        if row is None:
            return None
        return Tarifa(id=row["id"], nombre=row["nombre"],
                      precio_hora=row["precio_hora"], activa=row["activa"])

    def _get_ticket_by_id(self, ticket_id: int) -> Optional[Ticket]:
        sql = "SELECT * FROM tickets WHERE id = ?"
        with self._connect() as conn:
            row = conn.execute(sql, (ticket_id,)).fetchone()
        return self._row_to_ticket(row) if row else None

    def clear_all_tickets(self):
        with self._connect() as conn:
            conn.execute("DELETE FROM tickets")

    def close(self):
        pass  # connections are opened/closed per-operation; nothing to release

    @staticmethod
    def _row_to_ticket(row) -> Ticket:
        return Ticket(
            id=row["id"],
            placa=row["placa"],
            hora_entrada=row["hora_entrada"],
            hora_salida=row["hora_salida"],
            minutos=row["minutos"],
            monto=row["monto"],
            tarifa_id=row["tarifa_id"],
            estado=row["estado"],
        )
