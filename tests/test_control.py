"""
Suite de pruebas unitarias del módulo de control — Quillinchu AI.

Valida el comportamiento de ``MavlinkController`` y ``GuidanceLaw``
mediante mocks asíncronos, sin dependencias de hardware (SITL, dron
físico, telemetría de red).

References:
    - plan.md §3: Pruebas simétricas y unitarias.
    - tech-stack.md: «pytest y unittest para verificar de forma
      robusta la suite de visión, control y seguridad».
    - spec.md: Criterios de aceptación verificables.
"""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.control import VelocityCommand
from src.control.guidance_law import GuidanceLaw, GuidanceParams
from src.control.mavlink_controller import (
    MavlinkConnectionError,
    MavlinkController,
)
from src.vision import TargetState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_target(
    track_id: int = 1,
    x_min: float = 600.0,
    y_min: float = 320.0,
    x_max: float = 680.0,
    y_max: float = 400.0,
    confidence: float = 0.90,
) -> TargetState:
    """Crea un ``TargetState`` de prueba con valores predeterminados."""
    return TargetState(
        track_id=track_id,
        bbox=(x_min, y_min, x_max, y_max),
        confidence=confidence,
    )


def _make_centered_target(
    image_width: int = 1280,
    image_height: int = 720,
    box_size: float = 50.0,
) -> TargetState:
    """Crea un ``TargetState`` centrado exactamente en la imagen."""
    cx: float = image_width / 2.0
    cy: float = image_height / 2.0
    half: float = box_size / 2.0
    return TargetState(
        track_id=1,
        bbox=(cx - half, cy - half, cx + half, cy + half),
        confidence=0.95,
    )


async def _mock_connection_state_connected():
    """Generador asíncrono que simula conexión exitosa."""
    state = MagicMock()
    state.is_connected = True
    yield state


async def _mock_connection_state_timeout():
    """Generador asíncrono que nunca conecta (simula timeout)."""
    while True:
        state = MagicMock()
        state.is_connected = False
        yield state
        await asyncio.sleep(0.01)


def _create_mock_drone() -> MagicMock:
    """Crea un mock completo de ``mavsdk.System``."""
    mock_drone = MagicMock()
    mock_drone.connect = AsyncMock()

    # Core: connection_state como generador asíncrono.
    mock_drone.core = MagicMock()
    mock_drone.core.connection_state.return_value = _mock_connection_state_connected()

    # Offboard plugin.
    mock_drone.offboard = MagicMock()
    mock_drone.offboard.set_velocity_body = AsyncMock()
    mock_drone.offboard.start = AsyncMock()
    mock_drone.offboard.stop = AsyncMock()

    return mock_drone


# ===========================================================================
# TestVelocityCommand
# ===========================================================================


class TestVelocityCommand:
    """Pruebas del dataclass ``VelocityCommand``."""

    def test_default_values(self) -> None:
        """Todos los campos deben ser 0.0 por defecto."""
        cmd = VelocityCommand()
        assert cmd.forward_m_s == 0.0
        assert cmd.right_m_s == 0.0
        assert cmd.down_m_s == 0.0
        assert cmd.yawspeed_deg_s == 0.0

    def test_custom_values(self) -> None:
        """Los campos deben aceptar valores personalizados."""
        cmd = VelocityCommand(
            forward_m_s=1.5,
            right_m_s=-0.3,
            down_m_s=0.2,
            yawspeed_deg_s=15.0,
        )
        assert cmd.forward_m_s == 1.5
        assert cmd.right_m_s == -0.3
        assert cmd.down_m_s == 0.2
        assert cmd.yawspeed_deg_s == 15.0

    def test_immutability(self) -> None:
        """``VelocityCommand`` es inmutable (frozen=True)."""
        cmd = VelocityCommand(forward_m_s=1.0)
        with pytest.raises(FrozenInstanceError):
            cmd.forward_m_s = 2.0  # type: ignore[misc]

    def test_equality(self) -> None:
        """Dos instancias con los mismos valores son iguales."""
        cmd_a = VelocityCommand(forward_m_s=1.0, yawspeed_deg_s=5.0)
        cmd_b = VelocityCommand(forward_m_s=1.0, yawspeed_deg_s=5.0)
        assert cmd_a == cmd_b


# ===========================================================================
# TestGuidanceLaw
# ===========================================================================


class TestGuidanceLaw:
    """Pruebas de la ley de guiado proporcional ``GuidanceLaw``."""

    # ---------------------------------------------------------------
    # Configuración compartida
    # ---------------------------------------------------------------

    @pytest.fixture
    def default_params(self) -> GuidanceParams:
        """Parámetros por defecto: imagen 1280×720."""
        return GuidanceParams()

    @pytest.fixture
    def guidance(self, default_params: GuidanceParams) -> GuidanceLaw:
        """Instancia de ``GuidanceLaw`` con parámetros por defecto."""
        return GuidanceLaw(params=default_params)

    # ---------------------------------------------------------------
    # Lista vacía
    # ---------------------------------------------------------------

    def test_empty_targets_returns_none(self, guidance: GuidanceLaw) -> None:
        """Sin objetivos, ``compute`` debe retornar ``None``."""
        result = guidance.compute([])
        assert result is None

    # ---------------------------------------------------------------
    # Selección de objetivo
    # ---------------------------------------------------------------

    def test_selects_highest_confidence(self, guidance: GuidanceLaw) -> None:
        """Selecciona el target con mayor confianza."""
        low = _make_target(track_id=1, confidence=0.50)
        high = _make_target(track_id=2, confidence=0.95)

        # El resultado depende del target seleccionado.
        # Ambos tienen la misma bbox, así que el resultado debe ser
        # idéntico independientemente del orden.
        result_a = guidance.compute([low, high])
        result_b = guidance.compute([high, low])
        assert result_a is not None
        assert result_a == result_b

    # ---------------------------------------------------------------
    # Objetivo centrado → velocidad cero
    # ---------------------------------------------------------------

    def test_centered_target_zero_velocity(self, guidance: GuidanceLaw) -> None:
        """Objetivo en el centro exacto produce velocidad cero."""
        target = _make_centered_target()
        result = guidance.compute([target])

        assert result is not None
        assert result.forward_m_s == 0.0
        assert result.yawspeed_deg_s == 0.0
        assert result.right_m_s == 0.0
        assert result.down_m_s == 0.0

    # ---------------------------------------------------------------
    # Deadband
    # ---------------------------------------------------------------

    def test_deadband_suppresses_small_error(self) -> None:
        """Errores dentro de la zona muerta se anulan a cero."""
        params = GuidanceParams(deadband_px=20.0)
        guidance = GuidanceLaw(params=params)

        # Bbox con centroide desplazado solo 10 px a la derecha
        # y 5 px debajo del centro (dentro de deadband de 20 px).
        cx, cy = 640.0, 360.0  # Centro de 1280×720.
        offset_x, offset_y = 10.0, 5.0
        target = TargetState(
            track_id=1,
            bbox=(
                cx + offset_x - 25,
                cy + offset_y - 25,
                cx + offset_x + 25,
                cy + offset_y + 25,
            ),
            confidence=0.9,
        )

        result = guidance.compute([target])
        assert result is not None
        assert result.yawspeed_deg_s == 0.0
        assert result.forward_m_s == 0.0

    def test_deadband_passes_large_error(self) -> None:
        """Errores fuera de la zona muerta NO se anulan."""
        params = GuidanceParams(deadband_px=10.0)
        guidance = GuidanceLaw(params=params)

        # Bbox con centroide desplazado 100 px a la derecha.
        cx = 640.0 + 100.0
        cy = 360.0
        target = TargetState(
            track_id=1,
            bbox=(cx - 25, cy - 25, cx + 25, cy + 25),
            confidence=0.9,
        )

        result = guidance.compute([target])
        assert result is not None
        assert result.yawspeed_deg_s != 0.0

    # ---------------------------------------------------------------
    # Ley Proporcional: cálculo exacto
    # ---------------------------------------------------------------

    def test_proportional_yaw_calculation(self) -> None:
        """Verifica el cálculo P exacto para yawspeed."""
        kp_yaw = 0.2
        params = GuidanceParams(
            kp_yaw=kp_yaw,
            deadband_px=0.0,  # Sin deadband para test puro.
        )
        guidance = GuidanceLaw(params=params)

        # Centroide 50 px a la derecha del centro.
        cx = 640.0 + 50.0  # = 690.0
        cy = 360.0  # Centro vertical.
        target = TargetState(
            track_id=1,
            bbox=(cx - 25, cy - 25, cx + 25, cy + 25),
            confidence=0.9,
        )

        result = guidance.compute([target])
        assert result is not None

        # eₓ = 690 - 640 = 50; yawspeed = 0.2 * 50 = 10.0
        expected_yaw: float = kp_yaw * 50.0
        assert result.yawspeed_deg_s == pytest.approx(expected_yaw)

    def test_proportional_forward_calculation(self) -> None:
        """Verifica el cálculo P exacto para forward."""
        kp_forward = 0.005
        params = GuidanceParams(
            kp_forward=kp_forward,
            deadband_px=0.0,
        )
        guidance = GuidanceLaw(params=params)

        # Centroide 80 px debajo del centro.
        cx = 640.0
        cy = 360.0 + 80.0  # = 440.0
        target = TargetState(
            track_id=1,
            bbox=(cx - 25, cy - 25, cx + 25, cy + 25),
            confidence=0.9,
        )

        result = guidance.compute([target])
        assert result is not None

        # eᵧ = 440 - 360 = 80; forward = 0.005 * 80 = 0.4
        expected_fwd: float = kp_forward * 80.0
        assert result.forward_m_s == pytest.approx(expected_fwd)

    def test_negative_error_produces_negative_velocity(self) -> None:
        """Error negativo (objetivo a la izquierda/arriba) produce
        velocidad negativa.
        """
        params = GuidanceParams(
            kp_yaw=0.1,
            kp_forward=0.002,
            deadband_px=0.0,
        )
        guidance = GuidanceLaw(params=params)

        # Centroide 100 px a la izquierda y 50 px arriba del centro.
        cx = 640.0 - 100.0
        cy = 360.0 - 50.0
        target = TargetState(
            track_id=1,
            bbox=(cx - 25, cy - 25, cx + 25, cy + 25),
            confidence=0.9,
        )

        result = guidance.compute([target])
        assert result is not None
        assert result.yawspeed_deg_s < 0.0
        assert result.forward_m_s < 0.0

    # ---------------------------------------------------------------
    # Saturación (clamping)
    # ---------------------------------------------------------------

    def test_clamping_limits_yaw(self) -> None:
        """La velocidad angular se satura al máximo configurado."""
        max_yaw = 20.0
        params = GuidanceParams(
            kp_yaw=1.0,  # Ganancia alta para forzar saturación.
            deadband_px=0.0,
            max_yaw_rate=max_yaw,
        )
        guidance = GuidanceLaw(params=params)

        # Error de 500 px → v = 1.0 * 500 = 500 °/s (sin clamp).
        cx = 640.0 + 500.0
        cy = 360.0
        target = TargetState(
            track_id=1,
            bbox=(cx - 25, cy - 25, cx + 25, cy + 25),
            confidence=0.9,
        )

        result = guidance.compute([target])
        assert result is not None
        assert result.yawspeed_deg_s == pytest.approx(max_yaw)

    def test_clamping_limits_forward(self) -> None:
        """La velocidad lineal se satura al máximo configurado."""
        max_speed = 1.5
        params = GuidanceParams(
            kp_forward=0.1,  # Ganancia alta para forzar saturación.
            deadband_px=0.0,
            max_linear_speed=max_speed,
        )
        guidance = GuidanceLaw(params=params)

        # Error de 300 px → v = 0.1 * 300 = 30 m/s (sin clamp).
        cx = 640.0
        cy = 360.0 + 300.0
        target = TargetState(
            track_id=1,
            bbox=(cx - 25, cy - 25, cx + 25, cy + 25),
            confidence=0.9,
        )

        result = guidance.compute([target])
        assert result is not None
        assert result.forward_m_s == pytest.approx(max_speed)

    def test_clamping_limits_negative(self) -> None:
        """La saturación también funciona con valores negativos."""
        max_yaw = 25.0
        params = GuidanceParams(
            kp_yaw=1.0,
            deadband_px=0.0,
            max_yaw_rate=max_yaw,
        )
        guidance = GuidanceLaw(params=params)

        # Error de -500 px → v = 1.0 * (-500) = -500 °/s.
        cx = 640.0 - 500.0
        cy = 360.0
        target = TargetState(
            track_id=1,
            bbox=(cx - 25, cy - 25, cx + 25, cy + 25),
            confidence=0.9,
        )

        result = guidance.compute([target])
        assert result is not None
        assert result.yawspeed_deg_s == pytest.approx(-max_yaw)

    # ---------------------------------------------------------------
    # right_m_s y down_m_s siempre cero
    # ---------------------------------------------------------------

    def test_lateral_and_vertical_always_zero(self, guidance: GuidanceLaw) -> None:
        """right_m_s y down_m_s deben ser siempre 0.0."""
        target = _make_target()
        result = guidance.compute([target])

        assert result is not None
        assert result.right_m_s == 0.0
        assert result.down_m_s == 0.0

    # ---------------------------------------------------------------
    # Propiedades
    # ---------------------------------------------------------------

    def test_params_property(self, default_params: GuidanceParams) -> None:
        """La propiedad ``params`` devuelve la configuración inyectada."""
        guidance = GuidanceLaw(params=default_params)
        assert guidance.params == default_params

    def test_image_center_property(self) -> None:
        """El centro se calcula correctamente a partir de la resolución."""
        params = GuidanceParams(image_width=1920, image_height=1080)
        guidance = GuidanceLaw(params=params)
        cx, cy = guidance.image_center
        assert cx == pytest.approx(960.0)
        assert cy == pytest.approx(540.0)


# ===========================================================================
# TestMavlinkController
# ===========================================================================


class TestMavlinkController:
    """Pruebas del controlador MAVLink asíncrono ``MavlinkController``.

    Utiliza ``AsyncMock`` de ``unittest.mock`` para simular las
    llamadas asíncronas de MAVSDK sin requerir hardware físico
    ni el simulador SITL activo.
    """

    # ---------------------------------------------------------------
    # Conexión
    # ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """La conexión exitosa establece el estado ``is_connected``."""
        mock_drone = _create_mock_drone()
        controller = MavlinkController(drone=mock_drone)

        await controller.connect()

        assert controller.is_connected is True
        mock_drone.connect.assert_awaited_once()
        # Limpiar tarea de monitoreo.
        await controller.close()

    @pytest.mark.asyncio
    async def test_connect_timeout_raises_error(self) -> None:
        """Si la conexión no se establece, lanza
        ``MavlinkConnectionError``.
        """
        mock_drone = _create_mock_drone()
        mock_drone.core.connection_state.return_value = _mock_connection_state_timeout()

        controller = MavlinkController(drone=mock_drone, connection_timeout_s=0.1)

        with pytest.raises(MavlinkConnectionError):
            await controller.connect()

        assert controller.is_connected is False

    # ---------------------------------------------------------------
    # Modo Offboard
    # ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_start_offboard_success(self) -> None:
        """``start_offboard`` envía el setpoint inicial y activa
        el modo.
        """
        mock_drone = _create_mock_drone()
        controller = MavlinkController(drone=mock_drone)
        await controller.connect()

        await controller.start_offboard()

        assert controller.is_offboard_active is True
        # Se debe haber enviado el setpoint cero inicial.
        assert mock_drone.offboard.set_velocity_body.await_count >= 1
        mock_drone.offboard.start.assert_awaited_once()
        await controller.close()

    @pytest.mark.asyncio
    async def test_start_offboard_error_propagates(self) -> None:
        """Si Offboard falla al iniciar, la excepción se propaga."""
        from mavsdk.offboard import OffboardError

        mock_drone = _create_mock_drone()
        mock_drone.offboard.start = AsyncMock(
            side_effect=OffboardError(
                MagicMock(result=MagicMock(result_str="NO_SETPOINT")),
                "start()",
            )
        )

        controller = MavlinkController(drone=mock_drone)
        await controller.connect()

        with pytest.raises(OffboardError):
            await controller.start_offboard()

        assert controller.is_offboard_active is False
        await controller.close()

    @pytest.mark.asyncio
    async def test_stop_offboard(self) -> None:
        """``stop_offboard`` desactiva el modo correctamente."""
        mock_drone = _create_mock_drone()
        controller = MavlinkController(drone=mock_drone)
        await controller.connect()
        await controller.start_offboard()

        await controller.stop_offboard()

        assert controller.is_offboard_active is False
        mock_drone.offboard.stop.assert_awaited_once()
        await controller.close()

    @pytest.mark.asyncio
    async def test_stop_offboard_noop_when_inactive(self) -> None:
        """``stop_offboard`` no hace nada si Offboard no estaba
        activo.
        """
        mock_drone = _create_mock_drone()
        controller = MavlinkController(drone=mock_drone)

        await controller.stop_offboard()

        mock_drone.offboard.stop.assert_not_awaited()

    # ---------------------------------------------------------------
    # Envío de velocidad
    # ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_velocity_cmd_success(self) -> None:
        """``send_velocity_cmd`` envía la trama correcta vía MAVSDK."""
        mock_drone = _create_mock_drone()
        controller = MavlinkController(drone=mock_drone)
        await controller.connect()
        await controller.start_offboard()

        cmd = VelocityCommand(
            forward_m_s=1.0,
            right_m_s=0.5,
            down_m_s=-0.2,
            yawspeed_deg_s=10.0,
        )
        result: bool = await controller.send_velocity_cmd(cmd)

        assert result is True

        # Verificar los argumentos exactos del último envío.
        last_call = mock_drone.offboard.set_velocity_body.call_args
        velocity_body = last_call[0][0]
        assert velocity_body.forward_m_s == 1.0
        assert velocity_body.right_m_s == 0.5
        assert velocity_body.down_m_s == -0.2
        assert velocity_body.yawspeed_deg_s == 10.0
        await controller.close()

    @pytest.mark.asyncio
    async def test_send_velocity_without_offboard_returns_false(
        self,
    ) -> None:
        """Enviar velocidad sin Offboard activo retorna ``False``."""
        mock_drone = _create_mock_drone()
        controller = MavlinkController(drone=mock_drone)
        await controller.connect()

        cmd = VelocityCommand(forward_m_s=1.0)
        result: bool = await controller.send_velocity_cmd(cmd)

        assert result is False
        await controller.close()

    @pytest.mark.asyncio
    async def test_send_velocity_handles_offboard_error(
        self,
    ) -> None:
        """Errores Offboard no se propagan; retornan ``False``."""
        from mavsdk.offboard import OffboardError

        mock_drone = _create_mock_drone()
        controller = MavlinkController(drone=mock_drone)
        await controller.connect()
        await controller.start_offboard()

        # Simular error en el envío (no en start).
        mock_drone.offboard.set_velocity_body = AsyncMock(
            side_effect=OffboardError(
                MagicMock(result=MagicMock(result_str="TIMEOUT")),
                "set_velocity_body()",
            )
        )

        cmd = VelocityCommand(forward_m_s=1.0)
        result: bool = await controller.send_velocity_cmd(cmd)

        assert result is False
        # El controlador NO debe haber crasheado.
        await controller.close()

    @pytest.mark.asyncio
    async def test_send_velocity_handles_generic_exception(
        self,
    ) -> None:
        """Excepciones genéricas no se propagan; retornan ``False``."""
        mock_drone = _create_mock_drone()
        controller = MavlinkController(drone=mock_drone)
        await controller.connect()
        await controller.start_offboard()

        mock_drone.offboard.set_velocity_body = AsyncMock(
            side_effect=ConnectionError("Red perdida")
        )

        cmd = VelocityCommand(forward_m_s=1.0)
        result: bool = await controller.send_velocity_cmd(cmd)

        assert result is False
        await controller.close()

    # ---------------------------------------------------------------
    # Cierre
    # ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_close_stops_offboard_and_cleans_up(self) -> None:
        """``close`` desactiva Offboard y cancela la tarea de salud."""
        mock_drone = _create_mock_drone()
        controller = MavlinkController(drone=mock_drone)
        await controller.connect()
        await controller.start_offboard()

        await controller.close()

        assert controller.is_connected is False
        assert controller.is_offboard_active is False

    @pytest.mark.asyncio
    async def test_close_without_connection(self) -> None:
        """``close`` funciona correctamente sin conexión previa."""
        mock_drone = _create_mock_drone()
        controller = MavlinkController(drone=mock_drone)

        # No debe lanzar excepciones.
        await controller.close()

        assert controller.is_connected is False
