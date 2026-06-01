import re
from datetime import datetime
from typing import Dict, Any

from app.database.db_manager import DatabaseManager


PLATE_PATTERN = re.compile(r'^[A-Z]{3}-?\d{3}$')


class ParkingLogic:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def procesar_placa(self, placa: str,
                       accion_sugerida: str | None = None) -> Dict[str, Any]:
        """
        accion_sugerida: "ENTRADA" o "SALIDA" inferida por el ROI de detección.
        Si se provee, se usa como decisión principal y la BD solo valida
        que la operación tenga sentido (no registrar doble entrada, etc.).
        Si no se provee, cae al comportamiento original basado en BD.
        """
        placa = placa.upper().strip()
        hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not self.validar_formato_placa(placa):
            return {"accion": "INVALIDA", "placa": placa, "hora": hora, "monto": None}

        try:
            ticket_activo = self.db.get_ticket_activo(placa)

            # Determinar acción real combinando sugerencia del ROI con estado BD
            if accion_sugerida == "ENTRADA":
                if ticket_activo is not None:
                    # Ya está dentro: ignorar doble entrada
                    return {"accion": "YA_DENTRO", "placa": placa, "hora": hora, "monto": None}
                self.db.registrar_entrada(placa)
                return {"accion": "ENTRADA", "placa": placa, "hora": hora, "monto": None}

            elif accion_sugerida == "SALIDA":
                if ticket_activo is None:
                    # No está dentro: ignorar salida sin entrada
                    return {"accion": "NO_DENTRO", "placa": placa, "hora": hora, "monto": None}
                ticket_cerrado = self.db.registrar_salida(placa)
                return {
                    "accion":   "SALIDA",
                    "placa":    placa,
                    "hora":     hora,
                    "monto":    ticket_cerrado.monto if ticket_cerrado else 0.0,
                    "minutos":  ticket_cerrado.minutos if ticket_cerrado else 0,
                }

            else:
                # Sin sugerencia: comportamiento original (toggle por BD)
                if ticket_activo is None:
                    self.db.registrar_entrada(placa)
                    return {"accion": "ENTRADA", "placa": placa, "hora": hora, "monto": None}
                else:
                    ticket_cerrado = self.db.registrar_salida(placa)
                    return {
                        "accion":  "SALIDA",
                        "placa":   placa,
                        "hora":    hora,
                        "monto":   ticket_cerrado.monto if ticket_cerrado else 0.0,
                        "minutos": ticket_cerrado.minutos if ticket_cerrado else 0,
                    }

        except Exception as exc:
            return {"accion": "ERROR", "placa": placa, "hora": hora, "monto": None,
                    "error": str(exc)}

    def calcular_monto(self, minutos: int, precio_hora: float) -> float:
        return round((minutos / 60) * precio_hora, 2)

    def validar_formato_placa(self, placa: str) -> bool:
        return bool(PLATE_PATTERN.match(placa))
