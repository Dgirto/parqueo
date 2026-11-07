"""Crea historial de DEMOSTRACIÓN para ver Reportes con datos. Solo actúa si la base está vacía."""
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.core.config import DB_PATH
from app.database.db_manager import DatabaseManager

LETRAS = "ABCDEFGHJKLMNPRSTUVWXYZ"
HORAS = [7, 8, 8, 9, 9, 10, 11, 12, 13, 13, 14, 15, 16, 17, 18, 18, 19, 20]


def placa(rng: random.Random) -> str:
    return f"{''.join(rng.choices(LETRAS, k=3))}-{rng.randint(100, 999)}"


def main() -> None:
    db = DatabaseManager(DB_PATH)
    db.initialize()
    with db._connect() as conn:
        if conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]:
            print("La base ya tiene tickets: no se agregó nada.")
            return
        precio = conn.execute("SELECT precio_hora FROM tarifas WHERE id = 1").fetchone()[0]
        rng = random.Random(2026)
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        filas = []
        for dias_atras in range(30, 0, -1):
            dia = hoy - timedelta(days=dias_atras)
            for _ in range(rng.randint(18, 42) if dia.weekday() < 5 else rng.randint(30, 58)):
                entrada = dia + timedelta(hours=rng.choice(HORAS), minutes=rng.randint(0, 59), seconds=rng.randint(0, 59))
                minutos = rng.randint(12, 190)
                filas.append((placa(rng), entrada.strftime("%Y-%m-%d %H:%M:%S"),
                              (entrada + timedelta(minutes=minutos)).strftime("%Y-%m-%d %H:%M:%S"),
                              minutos, round(minutos / 60 * precio, 2)))
        conn.executemany(
            "INSERT INTO tickets (placa, hora_entrada, hora_salida, minutos, monto, tarifa_id, estado) "
            "VALUES (?, ?, ?, ?, ?, 1, 'CERRADO')", filas)
    print(f"Se crearon {len(filas)} tickets de demostración.")


if __name__ == "__main__":
    main()
