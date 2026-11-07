import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Dict, Iterator, List, Optional, Tuple

from app.core.config import CAPACIDAD_DEFAULT, SCHEMA_PATH, TARIFA_ID_DEFAULT, PRECIO_HORA_DEFAULT
from app.database.models import Ticket, Tarifa


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Abre una conexión por operación: confirma al terminar y siempre la cierra."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")   # lecturas concurrentes sin bloquear escrituras
            conn.execute("PRAGMA foreign_keys = ON")
            with conn:
                yield conn
        finally:
            conn.close()

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

    def clear_all_tickets(self) -> int:
        with self._connect() as conn:
            return conn.execute("DELETE FROM tickets").rowcount

    # ── Consultas para la web ──────────────────────────────────────

    def registrar_salida_por_id(self, ticket_id: int) -> Optional[Ticket]:
        ticket = self._get_ticket_by_id(ticket_id)
        if ticket is None or ticket.estado != "ACTIVO":
            return None
        return self.registrar_salida(ticket.placa)

    def get_ticket_de_resultado(self, resultado: Dict) -> Optional[Ticket]:
        """Ticket afectado por una lectura: el activo o, si acaba de salir, el último cerrado."""
        placa = resultado["placa"]
        activo = self.get_ticket_activo(placa)
        if activo is not None or resultado["accion"] != "SALIDA":
            return activo
        sql = "SELECT * FROM tickets WHERE placa = ? ORDER BY id DESC LIMIT 1"
        with self._connect() as conn:
            row = conn.execute(sql, (placa,)).fetchone()
        return self._row_to_ticket(row) if row else None

    def listar_tickets(self, estado: Optional[str], q: str, desde: Optional[str],
                       hasta: Optional[str], limite: int, inicio: int) -> Tuple[List[Ticket], int]:
        condiciones, valores = [], []
        if estado:
            condiciones.append("estado = ?")
            valores.append(estado)
        if q.strip():
            condiciones.append("placa LIKE ? ESCAPE '\\'")
            limpio = q.strip().upper().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            valores.append(f"%{limpio}%")
        if desde:
            condiciones.append("date(hora_entrada) >= ?")
            valores.append(desde)
        if hasta:
            condiciones.append("date(hora_entrada) <= ?")
            valores.append(hasta)
        donde = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
        with self._connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM tickets {donde}", valores).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM tickets {donde} ORDER BY hora_entrada DESC, id DESC LIMIT ? OFFSET ?",
                [*valores, limite, inicio],
            ).fetchall()
        return [self._row_to_ticket(r) for r in rows], total

    def resumen_hoy(self) -> Dict:
        hoy = date.today().isoformat()
        capacidad = self.get_capacidad()
        with self._connect() as conn:
            dentro = conn.execute("SELECT COUNT(*) FROM tickets WHERE estado = 'ACTIVO'").fetchone()[0]
            cobros, ingresos = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(monto), 0) FROM tickets "
                "WHERE estado = 'CERRADO' AND date(hora_salida) = ?", (hoy,),
            ).fetchone()
            entradas = conn.execute(
                "SELECT COUNT(*) FROM tickets WHERE date(hora_entrada) = ?", (hoy,),
            ).fetchone()[0]
            tarifa = conn.execute("SELECT precio_hora FROM tarifas WHERE id = ?",
                                  (TARIFA_ID_DEFAULT,)).fetchone()
        return {
            "dentro": dentro, "capacidad": capacidad, "libres": max(0, capacidad - dentro),
            "cobros": cobros, "ingresos": round(ingresos, 2), "entradas": entradas,
            "precio_hora": tarifa["precio_hora"] if tarifa else PRECIO_HORA_DEFAULT,
        }

    def reporte(self, dias: int) -> Dict:
        hoy = date.today()
        inicio = (hoy - timedelta(days=dias - 1)).isoformat()
        with self._connect() as conn:
            filas_dia = conn.execute(
                "SELECT date(hora_salida) AS dia, COUNT(*) AS salidas, COALESCE(SUM(monto), 0) AS ingresos "
                "FROM tickets WHERE estado = 'CERRADO' AND date(hora_salida) >= ? GROUP BY dia", (inicio,),
            ).fetchall()
            filas_hora = conn.execute(
                "SELECT CAST(strftime('%H', hora_entrada) AS INTEGER) AS hora, COUNT(*) AS entradas "
                "FROM tickets WHERE date(hora_entrada) >= ? GROUP BY hora", (inicio,),
            ).fetchall()
            promedio = conn.execute(
                "SELECT AVG(minutos) FROM tickets WHERE estado = 'CERRADO' AND date(hora_salida) >= ?",
                (inicio,),
            ).fetchone()[0]
        por_dia = {f["dia"]: f for f in filas_dia}
        por_hora = {f["hora"]: f["entradas"] for f in filas_hora}
        dias_lista = []
        for i in range(dias):
            dia = (hoy - timedelta(days=dias - 1 - i)).isoformat()
            fila = por_dia.get(dia)
            dias_lista.append({"dia": dia, "salidas": fila["salidas"] if fila else 0,
                               "ingresos": round(fila["ingresos"], 2) if fila else 0})
        return {
            "por_dia": dias_lista,
            "por_hora": [{"hora": h, "entradas": por_hora.get(h, 0)} for h in range(24)],
            "total_ingresos": round(sum(d["ingresos"] for d in dias_lista), 2),
            "total_salidas": sum(d["salidas"] for d in dias_lista),
            "permanencia_promedio": round(promedio) if promedio is not None else None,
        }

    def listar_tarifas(self) -> List[Tarifa]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM tarifas ORDER BY id").fetchall()
        return [Tarifa(id=r["id"], nombre=r["nombre"], precio_hora=r["precio_hora"],
                       activa=r["activa"]) for r in rows]

    def actualizar_tarifa(self, tarifa_id: int, precio_hora: float) -> Optional[Tarifa]:
        with self._connect() as conn:
            conn.execute("UPDATE tarifas SET precio_hora = ? WHERE id = ?", (precio_hora, tarifa_id))
        return self._get_tarifa(tarifa_id)

    def get_capacidad(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT valor FROM ajustes WHERE clave = 'capacidad'").fetchone()
        return int(row["valor"]) if row else CAPACIDAD_DEFAULT

    def set_capacidad(self, capacidad: int) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO ajustes (clave, valor) VALUES ('capacidad', ?) "
                         "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor", (str(capacidad),))

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
