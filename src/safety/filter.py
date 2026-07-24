"""
Filtro de Seguridad — Quillinchu AI.

Implementa la capa middleware de contingencias que intercepta los
comandos de velocidad generados por ``GuidanceLaw`` y los valida
antes de ser enviados al piloto automático vía ``MavlinkController``.

Responsabilidades:
    1. **Saturación Física (Hard Clamping):** Restringe cada
       componente de velocidad a límites simétricos configurables.
    2. **Hovering Autónomo (Failsafe):** Si el pipeline de visión
       pierde al objetivo por un tiempo superior al umbral
       ``failsafe_timeout_s``, sobrescribe el comando con ceros
       absolutos para detener la aeronave en el aire.

Principios de diseño:
    - **Desacoplamiento total:** Este módulo NO importa MAVSDK,
      OpenCV ni ninguna dependencia pesada. Es una función
      puramente matemática y lógica.
    - **Responsabilidad única:** Toda la lógica de saturación y
      contingencia temporal reside aquí, liberando al módulo de
      control de cualquier validación de seguridad.

References:
    - spec.md §005: Contingencias de Seguridad.
    - plan.md §005: Patrón Middleware, desacoplamiento total.
    - tech-stack.md §Límites duros: Filtro obligatorio de seguridad.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from src.control import VelocityCommand

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SafetyParams:
    """Parámetros configurables del filtro de seguridad.

    Todos los valores poseen defaults conservadores orientados a la
    protección de la aeronave, los operadores y el entorno del
    LabIAR. Deben ajustarse experimentalmente según las condiciones
    del espacio de pruebas (interior/exterior).

    Attributes:
        max_linear_speed: Velocidad lineal máxima permitida [m/s].
            Límite simétrico aplicado a ``forward_m_s``,
            ``right_m_s`` y ``down_m_s``. Valores superiores
            serán recortados a ``±max_linear_speed``.
        max_yaw_rate: Velocidad angular máxima de guiñada [°/s].
            Límite simétrico aplicado a ``yawspeed_deg_s``.
        failsafe_timeout_s: Tiempo máximo de tolerancia [s] sin
            detección válida del objetivo antes de activar el
            Hovering Autónomo. Valores entre 1.0 y 1.5 s son
            conservadores y dan margen a Deep SORT para recuperar
            oclusiones breves sin generar frenadas espurias.
    """

    max_linear_speed: float = 2.0
    max_yaw_rate: float = 30.0
    failsafe_timeout_s: float = 1.5


class SafetyFilter:
    """Filtro middleware de contingencias de seguridad.

    Intercepta cada ``VelocityCommand`` emitido por ``GuidanceLaw``
    y lo valida contra dos mecanismos de protección antes de que
    sea enviado al piloto automático:

    1. **Failsafe temporal:** Si el tiempo transcurrido desde la
       última detección válida supera ``failsafe_timeout_s``, el
       filtro sobrescribe el comando con ceros absolutos (Hovering).
    2. **Saturación simétrica (clamping):** Cada componente de
       velocidad es recortado dentro del rango ``[-max, +max]``
       definido en ``SafetyParams``.

    El filtro es **stateless** respecto a frames anteriores: toda
    la información temporal necesaria (``last_target_time``,
    ``current_time``) le es inyectada en cada llamada a ``apply()``.

    Args:
        params: Configuración de límites de seguridad. Si no se
            provee, se utilizan los defaults conservadores de
            ``SafetyParams``.
    """

    def __init__(self, params: Optional[SafetyParams] = None) -> None:
        self._params: SafetyParams = (
            params if params is not None else SafetyParams()
        )

    def apply(
        self,
        cmd: VelocityCommand,
        last_target_time: float,
        current_time: float,
    ) -> VelocityCommand:
        """Aplica las contingencias de seguridad al comando de velocidad.

        Pipeline de validación:
            1. Evalúa el tiempo transcurrido desde la última
               detección válida del objetivo.
            2. Si excede ``failsafe_timeout_s`` → Hovering (ceros).
            3. Si el tracking es válido → aplica clamping simétrico
               a cada componente del comando.

        Args:
            cmd: Comando de velocidad crudo emitido por el
                controlador PID (``GuidanceLaw.compute()``).
            last_target_time: Timestamp (epoch, segundos) de la
                última detección válida del objetivo por el
                pipeline de visión.
            current_time: Timestamp (epoch, segundos) del instante
                actual del ciclo del lazo de vuelo.

        Returns:
            ``VelocityCommand`` validado y seguro. Puede ser:
            - Ceros absolutos si el failsafe está activo.
            - El comando original con sus componentes saturados
              dentro de los límites de ``SafetyParams``.
        """
        # ----------------------------------------------------------
        # 1. Failsafe: Hovering Autónomo por pérdida de tracking.
        # ----------------------------------------------------------
        elapsed: float = current_time - last_target_time

        if elapsed > self._params.failsafe_timeout_s:
            logger.warning(
                "Failsafe activado: objetivo perdido hace %.3f s "
                "(umbral: %.3f s). Emitiendo Hovering.",
                elapsed,
                self._params.failsafe_timeout_s,
            )
            return VelocityCommand(
                forward_m_s=0.0,
                right_m_s=0.0,
                down_m_s=0.0,
                yawspeed_deg_s=0.0,
            )

        # ----------------------------------------------------------
        # 2. Saturación física (clamping) simétrica.
        # ----------------------------------------------------------
        return VelocityCommand(
            forward_m_s=self._clamp(
                cmd.forward_m_s, self._params.max_linear_speed
            ),
            right_m_s=self._clamp(
                cmd.right_m_s, self._params.max_linear_speed
            ),
            down_m_s=self._clamp(
                cmd.down_m_s, self._params.max_linear_speed
            ),
            yawspeed_deg_s=self._clamp(
                cmd.yawspeed_deg_s, self._params.max_yaw_rate
            ),
        )

    @staticmethod
    def _clamp(value: float, limit: float) -> float:
        """Satura un valor dentro del rango simétrico [-limit, +limit].

        Args:
            value: Valor a saturar.
            limit: Límite absoluto (debe ser positivo).

        Returns:
            Valor saturado dentro de [-limit, +limit].
        """
        return max(-limit, min(value, limit))

    @property
    def params(self) -> SafetyParams:
        """Devuelve los parámetros de seguridad configurados (solo lectura)."""
        return self._params
