"""
Módulo de Control — Quillinchu AI.

Define las estructuras de datos compartidas del dominio de control
de vuelo y exporta los componentes públicos del módulo.

El ``VelocityCommand`` actúa como estructura de transferencia
inmutable entre la capa de guiado (``GuidanceLaw``) y la capa
de comunicación con el piloto automático (``MavlinkController``).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.control.pid import PIDController, PIDParams


@dataclass(frozen=True, slots=True)
class VelocityCommand:
    """Consigna de velocidad en el marco de referencia BODY_NED.

    Estructura inmutable que encapsula los 4 grados de libertad
    de velocidad enviados al piloto automático mediante MAVSDK.

    El marco ``BODY_NED`` define las velocidades relativas al
    cuerpo de la aeronave:
    - Eje X (forward): positivo hacia adelante.
    - Eje Y (right): positivo hacia la derecha.
    - Eje Z (down): positivo hacia abajo.
    - Yaw: positivo en sentido horario visto desde arriba.

    Attributes:
        forward_m_s: Velocidad longitudinal (+ adelante) [m/s].
        right_m_s: Velocidad lateral (+ derecha) [m/s].
        down_m_s: Velocidad vertical (+ descender) [m/s].
        yawspeed_deg_s: Velocidad angular de guiñada [°/s].
    """

    forward_m_s: float = 0.0
    right_m_s: float = 0.0
    down_m_s: float = 0.0
    yawspeed_deg_s: float = 0.0


__all__: list[str] = [
    "PIDController",
    "PIDParams",
    "VelocityCommand",
]
