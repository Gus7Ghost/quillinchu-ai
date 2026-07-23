"""
Controlador PID discreto — Quillinchu AI.

Implementación matemática pura de un controlador Proporcional-
Integral-Derivativo (PID) discreto con:

- **Anti-Windup**: Clamping del acumulador integral dentro de
  límites simétricos configurables para evitar saturación.
- **Filtro paso-bajo derivativo**: Aproximación bilineal (Tustin)
  de un filtro de primer orden aplicado al término derivativo
  para suprimir la amplificación de ruido de alta frecuencia.

El controlador es completamente agnóstico al sistema físico
controlado: recibe un escalar de error y un diferencial de
tiempo, y produce una señal de control escalar.

Ecuación de control::

    u(k) = P(k) + I(k) + D_filtered(k)

Donde::

    P(k) = Kp · e(k)
    I(k) = Ki · Σ(e · dt),  acumulador saturado en ±integral_limit
    D_filtered(k) = [2·Kd·(eₖ - eₖ₋₁) + (2τ - dt)·Dₖ₋₁]
                     / (2τ + dt)

References:
    - Åström, K.J. & Murray, R.M. (2008). *Feedback Systems*,
      Princeton University Press, §10.3 PID Control.
    - Tustin's method (bilinear transform) para discretización
      del filtro derivativo de primer orden.
    - tasks.md: Anti-Windup y Low-Pass Filter obligatorios.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PIDParams:
    """Parámetros inmutables del controlador PID.

    Attributes:
        kp: Ganancia proporcional. Respuesta inmediata al error
            actual.
        ki: Ganancia integral. Elimina el error en estado
            estacionario acumulando el historial de errores.
        kd: Ganancia derivativa. Anticipa cambios futuros del
            error reaccionando a su tasa de cambio.
        integral_limit: Límite simétrico del acumulador integral
            para protección Anti-Windup. El acumulador se satura
            en ``[-integral_limit, +integral_limit]``.
        tau: Constante de tiempo del filtro paso-bajo derivativo
            [s]. Valores mayores producen mayor suavizado del
            término D. ``tau = 0`` desactiva el filtro (derivada
            pura, no recomendado en práctica por amplificación
            de ruido).
    """

    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0
    integral_limit: float = 100.0
    tau: float = 0.01


class PIDController:
    """Controlador PID discreto con Anti-Windup y filtro derivativo.

    Args:
        params: Parámetros del controlador. Si no se proveen, se
            utilizan los defaults de ``PIDParams``.
    """

    def __init__(self, params: PIDParams | None = None) -> None:
        self._params: PIDParams = (
            params if params is not None else PIDParams()
        )

        # Estado interno mutable.
        self._integral: float = 0.0
        self._prev_error: float = 0.0
        self._prev_derivative_filtered: float = 0.0
        self._initialized: bool = False

    def compute(self, error: float, dt: float) -> float:
        """Calcula la señal de control para el instante actual.

        Args:
            error: Error actual (setpoint - medición). Positivo
                indica que la medición está por debajo del setpoint.
            dt: Diferencial de tiempo desde la última invocación
                [s]. Debe ser >= 0. Si ``dt <= 0``, solo se aplica
                el término proporcional (I y D se suprimen para
                evitar spikes en el primer frame o ante anomalías
                temporales).

        Returns:
            Señal de control escalar (sin saturar externamente).
        """
        # --- Término Proporcional ---
        p_term: float = self._params.kp * error

        # Protección: dt <= 0 suprime I y D (primer frame o error).
        if dt <= 0.0:
            self._prev_error = error
            self._initialized = True
            return p_term

        # --- Término Integral con Anti-Windup (clamping) ---
        self._integral += self._params.ki * error * dt
        self._integral = max(
            -self._params.integral_limit,
            min(self._integral, self._params.integral_limit),
        )
        i_term: float = self._integral

        # --- Término Derivativo con filtro paso-bajo (Tustin) ---
        if not self._initialized:
            # Primera iteración con dt > 0: no hay error previo
            # significativo para calcular la derivada.
            self._prev_error = error
            self._initialized = True
            d_term: float = 0.0
        else:
            tau: float = self._params.tau
            denominator: float = 2.0 * tau + dt

            if denominator <= 0.0:
                d_term = 0.0
            else:
                d_term = (
                    2.0 * self._params.kd * (error - self._prev_error)
                    + (2.0 * tau - dt)
                    * self._prev_derivative_filtered
                ) / denominator

        self._prev_derivative_filtered = d_term
        self._prev_error = error

        return p_term + i_term + d_term

    def reset(self) -> None:
        """Reinicia completamente el estado interno del controlador.

        Borra el acumulador integral, el error previo y el estado
        del filtro derivativo. Útil al cambiar de objetivo o
        re-iniciar el seguimiento tras una pérdida de tracking.
        """
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_derivative_filtered = 0.0
        self._initialized = False

    @property
    def params(self) -> PIDParams:
        """Devuelve los parámetros configurados (solo lectura)."""
        return self._params

    @property
    def integral(self) -> float:
        """Devuelve el valor actual del acumulador integral.

        Útil para monitoreo y pruebas de Anti-Windup.
        """
        return self._integral
