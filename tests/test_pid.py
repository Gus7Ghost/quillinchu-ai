"""
Suite de pruebas unitarias del controlador PID — Quillinchu AI.

Valida el comportamiento matemático puro de ``PIDController``:
término proporcional, acumulación integral con Anti-Windup,
filtro derivativo paso-bajo (Tustin), y reinicio de estado.

Todas las pruebas son puramente numéricas y agnósticas al dron.

References:
    - tasks.md: «Desarrollar la suite de pruebas unitarias
      matemáticas en tests/test_pid.py».
    - tech-stack.md: «pytest y unittest para verificar de forma
      robusta la suite de visión, control y seguridad».
"""

from __future__ import annotations

import pytest

from src.control.pid import PIDController, PIDParams


# ===========================================================================
# TestPIDParams
# ===========================================================================


class TestPIDParams:
    """Pruebas del dataclass ``PIDParams``."""

    def test_default_values(self) -> None:
        """Los valores por defecto son conservadores y seguros."""
        p = PIDParams()
        assert p.kp == 1.0
        assert p.ki == 0.0
        assert p.kd == 0.0
        assert p.integral_limit == 100.0
        assert p.tau == 0.01

    def test_custom_values(self) -> None:
        """Acepta valores personalizados correctamente."""
        p = PIDParams(kp=2.0, ki=0.5, kd=0.1, integral_limit=50.0, tau=0.05)
        assert p.kp == 2.0
        assert p.ki == 0.5
        assert p.kd == 0.1
        assert p.integral_limit == 50.0
        assert p.tau == 0.05

    def test_immutability(self) -> None:
        """``PIDParams`` es inmutable (frozen=True)."""
        p = PIDParams()
        with pytest.raises(AttributeError):
            p.kp = 999.0  # type: ignore[misc]


# ===========================================================================
# TestPIDController
# ===========================================================================


class TestPIDController:
    """Pruebas matemáticas puras del ``PIDController``."""

    # ---------------------------------------------------------------
    # Término Proporcional
    # ---------------------------------------------------------------

    def test_proportional_only_with_zero_dt(self) -> None:
        """Con ki=kd=0 y dt=0, output = kp * error."""
        pid = PIDController(PIDParams(kp=2.0, ki=0.0, kd=0.0))
        result: float = pid.compute(10.0, 0.0)
        assert result == pytest.approx(20.0)

    def test_proportional_only_with_positive_dt(self) -> None:
        """Con ki=kd=0 y dt>0, output sigue siendo kp * error."""
        pid = PIDController(PIDParams(kp=2.0, ki=0.0, kd=0.0))
        # Inicializar con un error para establecer prev_error.
        pid.compute(0.0, 0.0)
        result: float = pid.compute(10.0, 0.1)
        assert result == pytest.approx(20.0)

    def test_proportional_negative_error(self) -> None:
        """Error negativo produce salida negativa."""
        pid = PIDController(PIDParams(kp=3.0, ki=0.0, kd=0.0))
        result: float = pid.compute(-5.0, 0.0)
        assert result == pytest.approx(-15.0)

    def test_proportional_zero_error(self) -> None:
        """Error cero produce salida cero."""
        pid = PIDController(PIDParams(kp=3.0, ki=0.0, kd=0.0))
        result: float = pid.compute(0.0, 0.0)
        assert result == pytest.approx(0.0)

    # ---------------------------------------------------------------
    # Término Integral
    # ---------------------------------------------------------------

    def test_integral_accumulation(self) -> None:
        """Error constante acumula integral linealmente."""
        pid = PIDController(
            PIDParams(kp=0.0, ki=1.0, kd=0.0, integral_limit=1000.0)
        )
        # Cada llamada: integral += ki * error * dt = 1.0 * 10 * 0.1 = 1.0
        r1: float = pid.compute(10.0, 0.1)
        assert r1 == pytest.approx(1.0)
        assert pid.integral == pytest.approx(1.0)

        r2: float = pid.compute(10.0, 0.1)
        assert r2 == pytest.approx(2.0)
        assert pid.integral == pytest.approx(2.0)

        r3: float = pid.compute(10.0, 0.1)
        assert r3 == pytest.approx(3.0)
        assert pid.integral == pytest.approx(3.0)

    def test_integral_anti_windup_positive(self) -> None:
        """El acumulador integral se satura en +integral_limit."""
        pid = PIDController(
            PIDParams(kp=0.0, ki=10.0, kd=0.0, integral_limit=5.0)
        )
        # Cada llamada: integral += 10.0 * 100.0 * 0.1 = 100.0
        # Pero se satura en 5.0.
        for _ in range(10):
            result: float = pid.compute(100.0, 0.1)
        assert result == pytest.approx(5.0)
        assert pid.integral == pytest.approx(5.0)

    def test_integral_anti_windup_negative(self) -> None:
        """El acumulador integral se satura en -integral_limit."""
        pid = PIDController(
            PIDParams(kp=0.0, ki=10.0, kd=0.0, integral_limit=5.0)
        )
        for _ in range(10):
            result: float = pid.compute(-100.0, 0.1)
        assert result == pytest.approx(-5.0)
        assert pid.integral == pytest.approx(-5.0)

    def test_steady_state_integral_grows_linearly(self) -> None:
        """Con error y dt constantes, integral crece linealmente."""
        ki: float = 2.0
        error: float = 5.0
        dt: float = 0.05
        pid = PIDController(
            PIDParams(kp=0.0, ki=ki, kd=0.0, integral_limit=1000.0)
        )

        n_steps: int = 20
        for i in range(1, n_steps + 1):
            pid.compute(error, dt)
            expected_integral: float = ki * error * dt * i
            assert pid.integral == pytest.approx(expected_integral)

    def test_integral_no_accumulation_with_zero_dt(self) -> None:
        """dt=0 no acumula integral."""
        pid = PIDController(
            PIDParams(kp=0.0, ki=5.0, kd=0.0, integral_limit=1000.0)
        )
        pid.compute(100.0, 0.0)
        assert pid.integral == pytest.approx(0.0)

    # ---------------------------------------------------------------
    # Término Derivativo
    # ---------------------------------------------------------------

    def test_derivative_response_to_step(self) -> None:
        """El término D responde ante un cambio escalón del error."""
        pid = PIDController(
            PIDParams(kp=0.0, ki=0.0, kd=1.0, tau=0.1)
        )
        # Inicializar con error=0.
        r_init: float = pid.compute(0.0, 0.1)
        assert r_init == pytest.approx(0.0)

        # Escalón a error=10.
        result: float = pid.compute(10.0, 0.1)
        # D = (2*Kd*(e-e_prev) + (2*tau-dt)*D_prev) / (2*tau+dt)
        #   = (2*1.0*(10-0) + (0.2-0.1)*0) / (0.2+0.1)
        #   = 20 / 0.3 ≈ 66.667
        expected: float = (2.0 * 1.0 * 10.0) / (2.0 * 0.1 + 0.1)
        assert result == pytest.approx(expected)

    def test_derivative_filter_smoothing(self) -> None:
        """Mayor tau produce mayor suavizado (menor respuesta D)."""
        # tau bajo → menor suavizado → mayor respuesta.
        pid_low_tau = PIDController(
            PIDParams(kp=0.0, ki=0.0, kd=1.0, tau=0.01)
        )
        pid_low_tau.compute(0.0, 0.1)
        result_low: float = pid_low_tau.compute(10.0, 0.1)

        # tau alto → mayor suavizado → menor respuesta.
        pid_high_tau = PIDController(
            PIDParams(kp=0.0, ki=0.0, kd=1.0, tau=1.0)
        )
        pid_high_tau.compute(0.0, 0.1)
        result_high: float = pid_high_tau.compute(10.0, 0.1)

        assert abs(result_high) < abs(result_low)

    def test_derivative_zero_on_constant_error(self) -> None:
        """Error constante produce término D decreciente a cero."""
        pid = PIDController(
            PIDParams(kp=0.0, ki=0.0, kd=1.0, tau=0.1)
        )
        pid.compute(10.0, 0.1)  # Inicializar.

        # Mismo error → (e-e_prev)=0 → D tiende a 0.
        result: float = pid.compute(10.0, 0.1)
        # D = (2*1.0*(10-10) + (0.2-0.1)*0) / (0.2+0.1) = 0/0.3 = 0
        assert result == pytest.approx(0.0)

    # ---------------------------------------------------------------
    # Casos borde y seguridad
    # ---------------------------------------------------------------

    def test_zero_dt_returns_proportional_only(self) -> None:
        """dt=0 suprime I y D, retorna solo P."""
        pid = PIDController(
            PIDParams(kp=2.0, ki=5.0, kd=3.0)
        )
        result: float = pid.compute(10.0, 0.0)
        # Solo P: 2.0 * 10.0 = 20.0 (I y D suprimidos).
        assert result == pytest.approx(20.0)

    def test_negative_dt_treated_as_zero(self) -> None:
        """dt negativo se trata igual que dt=0 (seguridad)."""
        pid = PIDController(
            PIDParams(kp=2.0, ki=5.0, kd=3.0)
        )
        result: float = pid.compute(10.0, -0.5)
        assert result == pytest.approx(20.0)

    # ---------------------------------------------------------------
    # Reset
    # ---------------------------------------------------------------

    def test_reset_clears_state(self) -> None:
        """``reset()`` reinicia integral, error previo y filtro D."""
        pid = PIDController(
            PIDParams(kp=0.0, ki=1.0, kd=0.0, integral_limit=1000.0)
        )
        # Acumular integral.
        pid.compute(10.0, 0.1)  # integral = 1.0
        pid.compute(10.0, 0.1)  # integral = 2.0
        assert pid.integral == pytest.approx(2.0)

        pid.reset()
        assert pid.integral == pytest.approx(0.0)

        # Tras reset, se comporta como controlador nuevo.
        result: float = pid.compute(10.0, 0.1)
        assert result == pytest.approx(1.0)

    def test_reset_allows_fresh_derivative(self) -> None:
        """Tras reset, la primera derivada es cero (no hay previo)."""
        pid = PIDController(
            PIDParams(kp=0.0, ki=0.0, kd=1.0, tau=0.1)
        )
        pid.compute(0.0, 0.1)
        pid.compute(10.0, 0.1)  # D ≠ 0

        pid.reset()

        # Tras reset, primera llamada con dt>0 da D=0 (sin previo).
        result: float = pid.compute(10.0, 0.1)
        assert result == pytest.approx(0.0)

    # ---------------------------------------------------------------
    # Propiedades
    # ---------------------------------------------------------------

    def test_params_property(self) -> None:
        """La propiedad ``params`` devuelve la configuración inyectada."""
        p = PIDParams(kp=1.5, ki=0.5, kd=0.1)
        pid = PIDController(params=p)
        assert pid.params == p

    def test_default_params(self) -> None:
        """Sin parámetros, se usan los defaults de ``PIDParams``."""
        pid = PIDController()
        assert pid.params == PIDParams()

    # ---------------------------------------------------------------
    # PID Completo (P + I + D combinados)
    # ---------------------------------------------------------------

    def test_full_pid_output(self) -> None:
        """Verifica la salida combinada P + I + D."""
        pid = PIDController(
            PIDParams(kp=1.0, ki=0.5, kd=0.2, tau=0.1, integral_limit=1000.0)
        )
        # Inicializar con error=0.
        pid.compute(0.0, 0.0)

        # Segundo paso: error=10, dt=0.1.
        result: float = pid.compute(10.0, 0.1)

        # P = 1.0 * 10 = 10.0
        p_expected: float = 10.0
        # I = 0.5 * 10 * 0.1 = 0.5
        i_expected: float = 0.5
        # D = (2*0.2*(10-0) + (0.2-0.1)*0) / (0.2+0.1)
        #   = 4.0 / 0.3 ≈ 13.333
        d_expected: float = (2.0 * 0.2 * 10.0) / (2.0 * 0.1 + 0.1)

        assert result == pytest.approx(p_expected + i_expected + d_expected)
