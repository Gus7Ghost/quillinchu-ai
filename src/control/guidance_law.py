"""
Ley de Guiado PID — Quillinchu AI.

Implementa el algoritmo de control PID que transforma los
errores de posición en píxeles del objetivo rastreado en consignas
de velocidad BODY_NED para el piloto automático.

Flujo del cálculo:
    1. Selección del objetivo con mayor confianza.
    2. Cálculo del error de píxeles (eₓ, eᵧ) respecto al centro.
    3. Aplicación de zonas muertas (deadband) para suprimir jitter.
    4. Cálculo del dt real a partir de los timestamps de TargetState.
    5. Ley PID: u = PIDController.compute(error, dt).
    6. Saturación física (clamping) de velocidades.

References:
    - spec.md §Criterios: Ley de guiado, saturación, deadband.
    - plan.md §2: Cálculo de Leyes de Guiado (GuidanceLaw).
    - tech-stack.md: «Cada algoritmo implementado debe contar con
      respaldo teórico sólido y formal».
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from src.control import VelocityCommand
from src.control.pid import PIDController, PIDParams
from src.vision import TargetState

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GuidanceParams:
    """Parámetros configurables de la ley de guiado PID.

    Todos los valores poseen defaults conservadores orientados a
    la seguridad. Las ganancias deben ajustarse experimentalmente
    con sustento matemático (prohibido el ajuste empírico arbitrario,
    ver ``mission.md`` §Principios).

    Attributes:
        image_width: Ancho de la imagen del stream en píxeles.
        image_height: Alto de la imagen del stream en píxeles.
        kp_yaw: Ganancia proporcional para la rotación yaw [°/s/px].
            Convierte el error horizontal en velocidad angular.
        ki_yaw: Ganancia integral para yaw [°/s/(px·s)].
            Elimina error estacionario en el eje de guiñada.
        kd_yaw: Ganancia derivativa para yaw [°/s·s/px].
            Amortigua oscilaciones en el eje de guiñada.
        kp_forward: Ganancia proporcional para el avance [m/s/px].
            Convierte el error vertical en velocidad lineal.
        ki_forward: Ganancia integral para forward [m/s/(px·s)].
            Elimina error estacionario en el eje longitudinal.
        kd_forward: Ganancia derivativa para forward [m/s·s/px].
            Amortigua oscilaciones en el eje longitudinal.
        integral_limit: Límite simétrico del acumulador integral
            para protección Anti-Windup (compartido por ambos
            ejes). Unidades en la salida del controlador.
        tau: Constante de tiempo del filtro paso-bajo derivativo
            [s]. Valores mayores producen mayor suavizado del
            término D en ambos ejes.
        deadband_px: Zona muerta simétrica en píxeles. Errores con
            magnitud inferior a este umbral se anulan para suprimir
            el jitter proveniente de variaciones del bounding box.
        max_yaw_rate: Velocidad angular máxima de guiñada [°/s].
            Límite de saturación para giros seguros.
        max_linear_speed: Velocidad lineal máxima [m/s].
            Límite de saturación para avance/retroceso seguros.
    """

    image_width: int = 1280
    image_height: int = 720
    kp_yaw: float = 0.1
    ki_yaw: float = 0.0
    kd_yaw: float = 0.0
    kp_forward: float = 0.002
    ki_forward: float = 0.0
    kd_forward: float = 0.0
    integral_limit: float = 100.0
    tau: float = 0.01
    deadband_px: float = 15.0
    max_yaw_rate: float = 30.0
    max_linear_speed: float = 2.0


class GuidanceLaw:
    """Ley de guiado PID con zonas muertas y saturación.

    Recibe la lista de ``TargetState`` publicada por el pipeline
    de visión (``queue.Queue[List[TargetState]]``), selecciona el
    objetivo con mayor confianza, calcula el error de píxeles
    respecto al centro de la imagen, aplica zonas muertas (deadband)
    para suprimir jitter, calcula el dt real a partir de los
    timestamps de ``TargetState``, delega a controladores PID
    independientes para yaw y forward, y satura (clamp) las
    velocidades resultantes dentro de los límites de seguridad.

    Convenciones de signo del controlador:
        - ``eₓ > 0`` (objetivo a la derecha) → ``yawspeed > 0``
          (giro horario visto desde arriba).
        - ``eᵧ > 0`` (objetivo debajo del centro) → ``forward > 0``
          (avance longitudinal del dron).

    TODO: La saturación física (clamping) aplicada en esta clase es
        una medida temporal de seguridad. Esta responsabilidad deberá
        migrar al módulo ``src/safety/`` cuando se implemente la
        Feature 005 (Contingencias de Seguridad), que proveerá
        validación centralizada, Geofencing 3D y filtros de
        seguridad avanzados. Ver ``tech-stack.md`` §Límites duros:
        «NINGÚN comando de velocidad puede enviarse directamente a
        MAVSDK sin ser previamente validado por src/safety/».

    Args:
        params: Parámetros de configuración de la ley de guiado.
            Si no se proveen, se utilizan los defaults conservadores
            definidos en ``GuidanceParams``.
    """

    def __init__(self, params: Optional[GuidanceParams] = None) -> None:
        self._params: GuidanceParams = (
            params if params is not None else GuidanceParams()
        )
        # Centro óptico de la imagen (punto de referencia del error).
        self._cx: float = self._params.image_width / 2.0
        self._cy: float = self._params.image_height / 2.0

        # Controladores PID independientes para cada eje.
        self._pid_yaw: PIDController = PIDController(
            params=PIDParams(
                kp=self._params.kp_yaw,
                ki=self._params.ki_yaw,
                kd=self._params.kd_yaw,
                integral_limit=self._params.integral_limit,
                tau=self._params.tau,
            )
        )
        self._pid_forward: PIDController = PIDController(
            params=PIDParams(
                kp=self._params.kp_forward,
                ki=self._params.ki_forward,
                kd=self._params.kd_forward,
                integral_limit=self._params.integral_limit,
                tau=self._params.tau,
            )
        )

        # Timestamp del frame anterior para cálculo de dt.
        self._last_timestamp: Optional[float] = None

    def compute(self, targets: List[TargetState]) -> Optional[VelocityCommand]:
        """Calcula la consigna de velocidad para el frame actual.

        Pipeline completo: selección → error → deadband → dt → PID → clamp.

        Args:
            targets: Lista de objetivos detectados y rastreados en
                el frame actual. Puede estar vacía si no hay
                detecciones activas.

        Returns:
            ``VelocityCommand`` con las velocidades calculadas, o
            ``None`` si no hay objetivos que seguir.
        """
        selected: Optional[TargetState] = self._select_target(targets)
        if selected is None:
            return None

        # ----------------------------------------------------------
        # 1. Centroide del bounding box del objetivo seleccionado.
        # ----------------------------------------------------------
        x_min, y_min, x_max, y_max = selected.bbox
        uc: float = (x_min + x_max) / 2.0
        vc: float = (y_min + y_max) / 2.0

        # ----------------------------------------------------------
        # 2. Error de píxeles respecto al centro de la imagen.
        #    eₓ = uₓ - cₓ  (positivo = objetivo a la derecha)
        #    eᵧ = vᵧ - cᵧ  (positivo = objetivo debajo del centro)
        # ----------------------------------------------------------
        ex: float = uc - self._cx
        ey: float = vc - self._cy

        # ----------------------------------------------------------
        # 3. Zona muerta (deadband): suprime jitter de baja amplitud.
        # ----------------------------------------------------------
        ex = self._apply_deadband(ex)
        ey = self._apply_deadband(ey)

        # ----------------------------------------------------------
        # 4. Cálculo del dt real desde los timestamps de TargetState.
        #    Primer frame: dt=0 → solo término P (sin spike I/D).
        # ----------------------------------------------------------
        dt: float = 0.0
        if self._last_timestamp is not None:
            dt = selected.timestamp - self._last_timestamp
            # Protección contra timestamps desordenados o repetidos.
            if dt < 0.0:
                logger.warning(
                    "Timestamp no monótono detectado (dt=%.6f s). "
                    "Reiniciando controladores PID.",
                    dt,
                )
                self.reset()
                dt = 0.0
        self._last_timestamp = selected.timestamp

        # ----------------------------------------------------------
        # 5. Ley PID: u = PIDController.compute(error, dt)
        # ----------------------------------------------------------
        yawspeed: float = self._pid_yaw.compute(ex, dt)
        forward: float = self._pid_forward.compute(ey, dt)

        # ----------------------------------------------------------
        # 6. Saturación física (clamping) — medida temporal.
        # TODO: Migrar a src/safety/ (Feature 005).
        # ----------------------------------------------------------
        yawspeed = self._clamp(yawspeed, self._params.max_yaw_rate)
        forward = self._clamp(forward, self._params.max_linear_speed)

        return VelocityCommand(
            forward_m_s=forward,
            right_m_s=0.0,
            down_m_s=0.0,
            yawspeed_deg_s=yawspeed,
        )

    def reset(self) -> None:
        """Reinicia el estado de ambos controladores PID y el timestamp.

        Útil al cambiar de objetivo, perder tracking o detectar
        anomalías temporales.
        """
        self._pid_yaw.reset()
        self._pid_forward.reset()
        self._last_timestamp = None

    def _select_target(self, targets: List[TargetState]) -> Optional[TargetState]:
        """Selecciona el objetivo con mayor confianza de detección.

        Args:
            targets: Lista de candidatos del frame actual.

        Returns:
            El ``TargetState`` con mayor ``confidence``, o ``None``
            si la lista está vacía.
        """
        if not targets:
            return None

        return max(targets, key=lambda t: t.confidence)

    def _apply_deadband(self, error: float) -> float:
        """Aplica zona muerta simétrica al error.

        Si la magnitud del error es inferior al umbral configurado,
        lo anula a cero para evitar que micro-variaciones del
        bounding box generen movimientos erráticos del dron.

        Args:
            error: Error en píxeles (puede ser negativo).

        Returns:
            El error original si ``|error| >= deadband_px``, o
            ``0.0`` si cae dentro de la zona muerta.
        """
        if abs(error) < self._params.deadband_px:
            return 0.0
        return error

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
    def params(self) -> GuidanceParams:
        """Devuelve los parámetros configurados (solo lectura)."""
        return self._params

    @property
    def image_center(self) -> tuple[float, float]:
        """Devuelve el centro óptico de la imagen (cₓ, cᵧ)."""
        return (self._cx, self._cy)
