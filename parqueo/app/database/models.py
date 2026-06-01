from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Tarifa:
    id: int
    nombre: str
    precio_hora: float
    activa: int = 1


@dataclass
class Vehiculo:
    id: int
    placa: str
    propietario: Optional[str]
    tipo: str
    created_at: str


@dataclass
class Ticket:
    id: int
    placa: str
    hora_entrada: str
    hora_salida: Optional[str] = None
    minutos: Optional[int] = None
    monto: Optional[float] = None
    tarifa_id: int = 1
    estado: str = "ACTIVO"
