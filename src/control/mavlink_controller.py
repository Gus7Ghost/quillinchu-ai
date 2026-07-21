"""
Controlador MAVLink asíncrono — Quillinchu AI.

Gestiona la conexión con el piloto automático a través de
MAVSDK-Python y el envío de comandos de velocidad en el marco
de referencia BODY_NED mediante el plugin Offboard.

MAVSDK-Python administra internamente la emisión del Heartbeat
MAVLink a 1 Hz, eliminando la necesidad de hilos dedicados.
Se lanza una tarea ``asyncio`` para monitorizar el estado de
conexión y registrar desconexiones sin bloquear el lazo principal.

References:
    - spec.md §Criterios: Conexión MAVLink, Heartbeat, BODY_NED.
    - plan.md §1: Gestión de telemetría y conexión.
    - tech-stack.md: «Toda la API de comunicación se gestiona
      mediante MAVSDK-Python y protocolos nativos asíncronos».
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from mavsdk import System
from mavsdk.offboard import OffboardError, VelocityBodyYawspeed

from src.control import VelocityCommand

logger = logging.getLogger(__name__)


class MavlinkConnectionError(Exception):
    """Error personalizado para fallos de conexión MAVLink.

    Se lanza cuando el controlador no logra establecer conexión
    con el piloto automático dentro del tiempo límite configurado.
    """


class MavlinkController:
    """Controlador asíncrono de la conexión MAVLink vía MAVSDK.

    Administra el ciclo de vida completo de la comunicación con
    el piloto automático: conexión, activación del modo Offboard,
    envío de consignas de velocidad BODY_NED y cierre limpio.

    MAVSDK-Python maneja internamente la emisión del Heartbeat
    MAVLink a 1 Hz hacia ArduPilot, eliminando la necesidad de
    hilos daemon dedicados. Se utiliza una tarea ``asyncio`` para
    monitorizar el estado de conexión de forma no bloqueante.

    Args:
        system_address: Cadena de conexión MAVSDK
            (ej. ``"udp://:14540"`` para SITL o
            ``"serial:///dev/ttyUSB0:57600"`` para hardware).
        connection_timeout_s: Tiempo máximo de espera para la
            conexión inicial con el piloto automático, en segundos.
        drone: Instancia opcional de ``mavsdk.System`` para
            inyección de dependencias en pruebas unitarias.
            Si no se provee, se crea una instancia nueva.
    """

    def __init__(
        self,
        system_address: str = "udp://:14540",
        connection_timeout_s: float = 15.0,
        drone: Optional[System] = None,
    ) -> None:
        self._system_address: str = system_address
        self._connection_timeout_s: float = connection_timeout_s
        self._drone: System = drone if drone is not None else System()
        self._connected: bool = False
        self._offboard_active: bool = False
        self._health_task: Optional[asyncio.Task[None]] = None

    # ------------------------------------------------------------------
    # Conexión
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Establece conexión asíncrona con el piloto automático.

        Espera hasta que MAVSDK confirme la conexión o se agote
        el tiempo límite configurado. Una vez conectado, lanza una
        tarea de monitoreo de salud de conexión en segundo plano.

        Raises:
            MavlinkConnectionError: Si no se logra conectar dentro
                del tiempo límite.
        """
        logger.info(
            "Iniciando conexión MAVSDK en '%s'...",
            self._system_address,
        )
        await self._drone.connect(system_address=self._system_address)

        try:
            await asyncio.wait_for(
                self._wait_for_connection(),
                timeout=self._connection_timeout_s,
            )
        except asyncio.TimeoutError:
            raise MavlinkConnectionError(
                f"Timeout de conexión ({self._connection_timeout_s}s) "
                f"agotado para '{self._system_address}'."
            )

        self._connected = True
        logger.info("Conexión MAVSDK establecida con éxito.")

        # Lanzar tarea de monitoreo de salud de conexión.
        self._health_task = asyncio.create_task(
            self._monitor_connection_health(),
            name="MavlinkController-HealthMonitor",
        )

    async def _wait_for_connection(self) -> None:
        """Espera a que MAVSDK confirme la conexión.

        Itera el generador asíncrono ``connection_state()`` hasta
        recibir un estado ``is_connected=True``.
        """
        async for state in self._drone.core.connection_state():
            if state.is_connected:
                return

    async def _monitor_connection_health(self) -> None:
        """Tarea asyncio que monitoriza cambios en la conexión.

        Registra advertencias cuando se pierde la conexión y
        actualizaciones cuando se restablece. No detiene el lazo
        de control; solo provee información diagnóstica.
        """
        try:
            async for state in self._drone.core.connection_state():
                was_connected: bool = self._connected
                self._connected = state.is_connected

                if was_connected and not state.is_connected:
                    logger.warning(
                        "Conexión MAVLink perdida — esperando "
                        "reconexión automática de MAVSDK."
                    )
                elif not was_connected and state.is_connected:
                    logger.info("Conexión MAVLink restablecida.")
        except asyncio.CancelledError:
            logger.debug(
                "Tarea de monitoreo de conexión cancelada."
            )
        except Exception as exc:
            logger.error(
                "Error en el monitor de conexión: %s", exc
            )

    # ------------------------------------------------------------------
    # Modo Offboard
    # ------------------------------------------------------------------

    async def start_offboard(self) -> None:
        """Activa el modo Offboard en el piloto automático.

        Antes de iniciar, envía una consigna de velocidad cero como
        setpoint inicial obligatorio exigido por el protocolo Offboard
        de PX4/ArduPilot.

        Raises:
            OffboardError: Si MAVSDK no puede activar el modo.
        """
        try:
            # Setpoint inicial obligatorio antes de start().
            await self._drone.offboard.set_velocity_body(
                VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0)
            )
            await self._drone.offboard.start()
            self._offboard_active = True
            logger.info("Modo Offboard activado con éxito.")
        except OffboardError as exc:
            self._offboard_active = False
            logger.error(
                "Fallo al activar modo Offboard: %s", exc
            )
            raise

    async def stop_offboard(self) -> None:
        """Desactiva el modo Offboard.

        Retorna el control al modo manual o al modo de vuelo
        previo configurado en el piloto automático.
        """
        if not self._offboard_active:
            return

        try:
            await self._drone.offboard.stop()
            self._offboard_active = False
            logger.info("Modo Offboard desactivado.")
        except OffboardError as exc:
            logger.error(
                "Error al desactivar modo Offboard: %s", exc
            )

    # ------------------------------------------------------------------
    # Envío de comandos de velocidad
    # ------------------------------------------------------------------

    async def send_velocity_cmd(self, cmd: VelocityCommand) -> bool:
        """Envía una consigna de velocidad BODY_NED al dron.

        Traduce el ``VelocityCommand`` interno a la estructura
        ``VelocityBodyYawspeed`` de MAVSDK y lo despacha al plugin
        Offboard. Si ocurre un error de comunicación, se registra
        sin propagar la excepción para no bloquear el lazo de control.

        Args:
            cmd: Consigna de velocidad a enviar.

        Returns:
            ``True`` si el envío fue exitoso, ``False`` si falló
            o si el modo Offboard no está activo.
        """
        if not self._offboard_active:
            logger.warning(
                "Intento de enviar velocidad sin modo Offboard "
                "activo — comando descartado."
            )
            return False

        try:
            await self._drone.offboard.set_velocity_body(
                VelocityBodyYawspeed(
                    cmd.forward_m_s,
                    cmd.right_m_s,
                    cmd.down_m_s,
                    cmd.yawspeed_deg_s,
                )
            )
            return True
        except OffboardError as exc:
            logger.error(
                "Error Offboard al enviar velocidad: %s", exc
            )
            return False
        except Exception as exc:
            logger.error(
                "Error inesperado al enviar comando de "
                "velocidad: %s",
                exc,
            )
            return False

    # ------------------------------------------------------------------
    # Cierre
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Cierra la conexión y cancela las tareas de monitoreo.

        Desactiva el modo Offboard si estaba activo y cancela
        la tarea de monitoreo de salud de conexión.
        """
        await self.stop_offboard()

        if self._health_task is not None:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

        self._connected = False
        logger.info("MavlinkController cerrado.")

    # ------------------------------------------------------------------
    # Propiedades de estado
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """Indica si la conexión con el piloto automático está activa."""
        return self._connected

    @property
    def is_offboard_active(self) -> bool:
        """Indica si el modo Offboard está activo."""
        return self._offboard_active
