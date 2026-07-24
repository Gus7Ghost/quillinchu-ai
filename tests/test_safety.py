"""
Suite de pruebas unitarias del módulo de seguridad — Quillinchu AI.

Valida el comportamiento del ``SafetyFilter`` y ``SafetyParams``
mediante pruebas deterministas, sin dependencias de hardware
(SITL, dron físico, telemetría de red, MAVSDK ni OpenCV).

Cobertura:
    - Valores por defecto e inmutabilidad de ``SafetyParams``.
    - Saturación simétrica (clamping) de velocidades positivas y
      negativas en los 4 ejes.
    - Activación exacta del Hovering Autónomo (Failsafe) tras
      superar el timeout configurado.
    - Recuperación fluida del control tras reanudar el tracking.

References:
    - spec.md §005: Criterios de aceptación verificables.
    - plan.md §005: Suite de Pruebas de Seguridad.
    - tech-stack.md: «pytest y unittest para verificar de forma
      robusta la suite de visión, control y seguridad».
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.control import VelocityCommand
from src.safety import SafetyFilter, SafetyParams


# ===========================================================================
# TestSafetyParams
# ===========================================================================


class TestSafetyParams:
    """Pruebas del dataclass ``SafetyParams``."""

    def test_default_values(self) -> None:
        """Los defaults deben ser conservadores para seguridad."""
        params = SafetyParams()
        assert params.max_linear_speed == 2.0
        assert params.max_yaw_rate == 30.0
        assert params.failsafe_timeout_s == 1.5

    def test_custom_values(self) -> None:
        """Los campos deben aceptar valores personalizados."""
        params = SafetyParams(
            max_linear_speed=3.0,
            max_yaw_rate=45.0,
            failsafe_timeout_s=2.0,
        )
        assert params.max_linear_speed == 3.0
        assert params.max_yaw_rate == 45.0
        assert params.failsafe_timeout_s == 2.0

    def test_immutability(self) -> None:
        """``SafetyParams`` es inmutable (frozen=True)."""
        params = SafetyParams()
        with pytest.raises(FrozenInstanceError):
            params.max_linear_speed = 5.0  # type: ignore[misc]

    def test_equality(self) -> None:
        """Dos instancias con los mismos valores son iguales."""
        params_a = SafetyParams(max_linear_speed=1.0)
        params_b = SafetyParams(max_linear_speed=1.0)
        assert params_a == params_b


# ===========================================================================
# TestSafetyFilter
# ===========================================================================


class TestSafetyFilter:
    """Pruebas del filtro de seguridad ``SafetyFilter``.

    Valida la saturación simétrica (clamping) de los 4 ejes de
    velocidad y la activación del Hovering Autónomo (Failsafe)
    por pérdida de tracking.
    """

    # ---------------------------------------------------------------
    # Configuración compartida
    # ---------------------------------------------------------------

    @pytest.fixture
    def default_filter(self) -> SafetyFilter:
        """Filtro con parámetros por defecto."""
        return SafetyFilter()

    @pytest.fixture
    def strict_filter(self) -> SafetyFilter:
        """Filtro con límites estrictos para forzar saturación."""
        return SafetyFilter(
            params=SafetyParams(
                max_linear_speed=1.0,
                max_yaw_rate=10.0,
                failsafe_timeout_s=1.0,
            )
        )

    # ---------------------------------------------------------------
    # Clamping positivo
    # ---------------------------------------------------------------

    def test_clamp_forward_positive(self, strict_filter: SafetyFilter) -> None:
        """forward_m_s positivo se satura al máximo."""
        cmd = VelocityCommand(forward_m_s=5.0)
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result.forward_m_s == pytest.approx(1.0)

    def test_clamp_right_positive(self, strict_filter: SafetyFilter) -> None:
        """right_m_s positivo se satura al máximo."""
        cmd = VelocityCommand(right_m_s=5.0)
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result.right_m_s == pytest.approx(1.0)

    def test_clamp_down_positive(self, strict_filter: SafetyFilter) -> None:
        """down_m_s positivo se satura al máximo."""
        cmd = VelocityCommand(down_m_s=5.0)
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result.down_m_s == pytest.approx(1.0)

    def test_clamp_yaw_positive(self, strict_filter: SafetyFilter) -> None:
        """yawspeed_deg_s positivo se satura al máximo."""
        cmd = VelocityCommand(yawspeed_deg_s=50.0)
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result.yawspeed_deg_s == pytest.approx(10.0)

    # ---------------------------------------------------------------
    # Clamping negativo (simétrico)
    # ---------------------------------------------------------------

    def test_clamp_forward_negative(self, strict_filter: SafetyFilter) -> None:
        """forward_m_s negativo se satura al mínimo simétrico."""
        cmd = VelocityCommand(forward_m_s=-5.0)
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result.forward_m_s == pytest.approx(-1.0)

    def test_clamp_right_negative(self, strict_filter: SafetyFilter) -> None:
        """right_m_s negativo se satura al mínimo simétrico."""
        cmd = VelocityCommand(right_m_s=-5.0)
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result.right_m_s == pytest.approx(-1.0)

    def test_clamp_down_negative(self, strict_filter: SafetyFilter) -> None:
        """down_m_s negativo se satura al mínimo simétrico."""
        cmd = VelocityCommand(down_m_s=-5.0)
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result.down_m_s == pytest.approx(-1.0)

    def test_clamp_yaw_negative(self, strict_filter: SafetyFilter) -> None:
        """yawspeed_deg_s negativo se satura al mínimo simétrico."""
        cmd = VelocityCommand(yawspeed_deg_s=-50.0)
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result.yawspeed_deg_s == pytest.approx(-10.0)

    # ---------------------------------------------------------------
    # Valores dentro del rango (pass-through)
    # ---------------------------------------------------------------

    def test_values_within_range_pass_through(
        self, strict_filter: SafetyFilter
    ) -> None:
        """Valores dentro de los límites pasan intactos."""
        cmd = VelocityCommand(
            forward_m_s=0.5,
            right_m_s=-0.3,
            down_m_s=0.8,
            yawspeed_deg_s=-7.0,
        )
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result.forward_m_s == pytest.approx(0.5)
        assert result.right_m_s == pytest.approx(-0.3)
        assert result.down_m_s == pytest.approx(0.8)
        assert result.yawspeed_deg_s == pytest.approx(-7.0)

    def test_zero_command_passes_through(
        self, strict_filter: SafetyFilter
    ) -> None:
        """Comando de ceros pasa intacto (no hay nada que saturar)."""
        cmd = VelocityCommand()
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result == VelocityCommand()

    def test_exact_limit_passes_through(
        self, strict_filter: SafetyFilter
    ) -> None:
        """Valores exactamente en el límite pasan intactos."""
        cmd = VelocityCommand(
            forward_m_s=1.0,
            right_m_s=-1.0,
            down_m_s=1.0,
            yawspeed_deg_s=10.0,
        )
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result == cmd

    # ---------------------------------------------------------------
    # Clamping simultáneo de múltiples ejes
    # ---------------------------------------------------------------

    def test_clamp_all_axes_simultaneously(
        self, strict_filter: SafetyFilter
    ) -> None:
        """Todos los ejes se saturan correctamente en una sola llamada."""
        cmd = VelocityCommand(
            forward_m_s=10.0,
            right_m_s=-10.0,
            down_m_s=10.0,
            yawspeed_deg_s=-100.0,
        )
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        assert result.forward_m_s == pytest.approx(1.0)
        assert result.right_m_s == pytest.approx(-1.0)
        assert result.down_m_s == pytest.approx(1.0)
        assert result.yawspeed_deg_s == pytest.approx(-10.0)

    # ---------------------------------------------------------------
    # Failsafe: Hovering Autónomo
    # ---------------------------------------------------------------

    def test_failsafe_activates_after_timeout(
        self, strict_filter: SafetyFilter
    ) -> None:
        """Tras superar el timeout, retorna ceros absolutos."""
        cmd = VelocityCommand(
            forward_m_s=0.5,
            right_m_s=0.3,
            down_m_s=-0.2,
            yawspeed_deg_s=5.0,
        )
        # failsafe_timeout_s = 1.0, elapsed = 1.5 > 1.0 → Hovering.
        result = strict_filter.apply(
            cmd, last_target_time=10.0, current_time=11.5
        )
        assert result == VelocityCommand()

    def test_failsafe_all_fields_are_zero(
        self, strict_filter: SafetyFilter
    ) -> None:
        """En failsafe, todos los campos deben ser exactamente 0.0."""
        cmd = VelocityCommand(
            forward_m_s=2.0,
            right_m_s=1.0,
            down_m_s=-1.0,
            yawspeed_deg_s=30.0,
        )
        result = strict_filter.apply(
            cmd, last_target_time=0.0, current_time=100.0
        )
        assert result.forward_m_s == 0.0
        assert result.right_m_s == 0.0
        assert result.down_m_s == 0.0
        assert result.yawspeed_deg_s == 0.0

    def test_failsafe_exact_boundary_does_not_activate(
        self, strict_filter: SafetyFilter
    ) -> None:
        """En el límite exacto (elapsed == timeout), NO se activa
        el failsafe (condición es estrictamente ``>``).
        """
        cmd = VelocityCommand(forward_m_s=0.5, yawspeed_deg_s=5.0)
        # failsafe_timeout_s = 1.0, elapsed = 1.0 exacto → NO Hovering.
        result = strict_filter.apply(
            cmd, last_target_time=10.0, current_time=11.0
        )
        assert result.forward_m_s == pytest.approx(0.5)
        assert result.yawspeed_deg_s == pytest.approx(5.0)

    def test_failsafe_just_over_boundary_activates(
        self, strict_filter: SafetyFilter
    ) -> None:
        """Un epsilon por encima del timeout activa el failsafe."""
        cmd = VelocityCommand(forward_m_s=0.5, yawspeed_deg_s=5.0)
        # failsafe_timeout_s = 1.0, elapsed = 1.001 > 1.0 → Hovering.
        result = strict_filter.apply(
            cmd, last_target_time=10.0, current_time=11.001
        )
        assert result == VelocityCommand()

    # ---------------------------------------------------------------
    # Recuperación fluida del tracking
    # ---------------------------------------------------------------

    def test_recovery_after_failsafe(
        self, strict_filter: SafetyFilter
    ) -> None:
        """Tras recuperar el tracking, el filtro deja pasar velocidades
        normalmente (sin estado residual del failsafe).
        """
        cmd = VelocityCommand(forward_m_s=0.5, yawspeed_deg_s=5.0)

        # 1. Failsafe activo (elapsed = 2.0 > 1.0).
        result_fail = strict_filter.apply(
            cmd, last_target_time=10.0, current_time=12.0
        )
        assert result_fail == VelocityCommand()

        # 2. Tracking recuperado (elapsed = 0.1 < 1.0).
        result_ok = strict_filter.apply(
            cmd, last_target_time=12.0, current_time=12.1
        )
        assert result_ok.forward_m_s == pytest.approx(0.5)
        assert result_ok.yawspeed_deg_s == pytest.approx(5.0)

    # ---------------------------------------------------------------
    # Propiedad params
    # ---------------------------------------------------------------

    def test_params_property(self) -> None:
        """La propiedad ``params`` devuelve la configuración inyectada."""
        params = SafetyParams(max_linear_speed=3.0)
        safety = SafetyFilter(params=params)
        assert safety.params == params

    def test_default_params_property(self) -> None:
        """Sin inyección, ``params`` devuelve los defaults."""
        safety = SafetyFilter()
        assert safety.params == SafetyParams()

    # ---------------------------------------------------------------
    # Resultado es un VelocityCommand inmutable
    # ---------------------------------------------------------------

    def test_result_is_immutable(self, strict_filter: SafetyFilter) -> None:
        """El VelocityCommand retornado es inmutable (frozen)."""
        cmd = VelocityCommand(forward_m_s=0.5)
        result = strict_filter.apply(cmd, last_target_time=10.0, current_time=10.0)
        with pytest.raises(FrozenInstanceError):
            result.forward_m_s = 99.0  # type: ignore[misc]
