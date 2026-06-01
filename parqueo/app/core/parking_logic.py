import re
from datetime import datetime
from typing import Dict, Any

from app.database.db_manager import DatabaseManager


PLATE_PATTERN = re.compile(r'^[A-Z]{3}-?\d{3}$')


class ParkingLogic:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def procesar_placa(self, placa: str) -> Dict[str, Any]:
        placa = placa.upper().strip()
        hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not self.validar_formato_placa(placa):
            return {"accion": "INVALIDA", "placa": placa, "hora": hora, "monto": None}

        try:
            ticket_activo = self.db.get_ticket_activo(placa)
            if ticket_activo is None:
                self.db.registrar_entrada(placa)
                return {"accion": "ENTRADA", "placa": placa, "hora": hora, "monto": None}
            else:
                ticket_cerrado = self.db.registrar_salida(placa)
                monto = ticket_cerrado.monto if ticket_cerrado else 0.0
                minutos = ticket_cerrado.minutos if ticket_cerrado else 0
                return {
                    "accion": "SALIDA",
                    "placa": placa,
                    "hora": hora,
                    "monto": monto,
                    "minutos": minutos,
                }
        except Exception as exc:
            return {"accion": "ERROR", "placa": placa, "hora": hora, "monto": None,
                    "error": str(exc)}

    def calcular_monto(self, minutos: int, precio_hora: float) -> float:
        return round((minutos / 60) * precio_hora, 2)

    def validar_formato_placa(self, placa: str) -> bool:
        return bool(PLATE_PATTERN.match(placa))
