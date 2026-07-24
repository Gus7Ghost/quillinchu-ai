"""
Orquestador Central — Quillinchu AI (Feature 006).

Punto de entrada principal del sistema de seguimiento autónomo.
Instancia e integra todos los subsistemas completados (Features 001-005)
mediante el patrón Productor-Consumidor sobre un lazo ``asyncio``:

    VisionPipeline (hilo daemon) → queue.Queue → Lazo de Control (asyncio)
    → GuidanceLaw → SafetyFilter → MavlinkController → Dron

El pipeline de visión (captura, YOLOv8, Deep SORT) se ejecuta en un
hilo dedicado para cumplir con el desacoplamiento computacional estricto
exigido por la constitución del proyecto (``tech-stack.md``). El lazo de
control permanece en el hilo principal de ``asyncio``, garantizando que
las operaciones matemáticas puras (PID, Safety) no bloqueen la
telemetría asíncrona de MAVSDK.

Ejecución::

    python src/main.py

References:
    - spec/features/006 - orquestador central/spec.md
    - spec/features/006 - orquestador central/plan.md
    - spec/constitution/tech-stack.md §Desacoplamiento computacional.
    - spec/constitution/mission.md §Seguridad Física Absoluta.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import time
from typing import List, Optional

from src.control import VelocityCommand
from src.control.guidance_law import GuidanceLaw, GuidanceParams
from src.control.mavlink_controller import MavlinkController
from src.metrics.logger import MetricsLogger
from src.safety.filter import SafetyFilter, SafetyParams
from src.vision import TargetState
from src.vision.camera_reader import CameraReader
from src.vision.detector import HeadDetector
from src.vision.pipeline import VisionPipeline
from src.vision.tracker import DeepSortTracker

# ──────────────────────────────────────────────────────────────────
# 1. Configuración de logging básico (INFO) en consola
# ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("quillinchu.main")

# Tasa objetivo del lazo de control (~30 Hz).
_LOOP_PERIOD_S: float = 0.033


async def main() -> None:
    """Lazo de control asíncrono del Orquestador Central.

    Ciclo de vida completo:
        1. Instanciación de componentes (inyección de dependencias).
        2. Conexión MAVLink + arranque del VisionPipeline.
        3. Activación del modo Offboard.
        4. Lazo ``while True`` del Consumidor.
        5. Apagado seguro (``finally``).
    """
    # ──────────────────────────────────────────────────────────────
    # 2. Instanciar componentes — Inyección de dependencias
    # ──────────────────────────────────────────────────────────────
    guidance_params: GuidanceParams = GuidanceParams()
    safety_params: SafetyParams = SafetyParams()

    # Subsistema de Visión (Feature 001)
    camera: CameraReader = CameraReader(
        port=5600,
        width=guidance_params.image_width,
        height=guidance_params.image_height,
    )
    detector: HeadDetector = HeadDetector(
        weights_path="HeadDetect.pt",
        confidence=0.5,
        device="cpu",
    )
    tracker: DeepSortTracker = DeepSortTracker(
        max_age=30,
        n_init=3,
        max_cosine_distance=0.3,
    )

    # Cola thread-safe Productor → Consumidor (maxsize=1: siempre
    # el estado más reciente de la escena).
    detection_queue: queue.Queue[List[TargetState]] = queue.Queue(
        maxsize=1,
    )

    vision_pipeline: VisionPipeline = VisionPipeline(
        camera=camera,
        detector=detector,
        tracker=tracker,
        output_queue=detection_queue,
        max_queue_size=1,
    )

    # Subsistema de Control y Navegación (Features 002 y 003)
    mavlink: MavlinkController = MavlinkController(
        system_address="udp://:14540",
        connection_timeout_s=15.0,
    )
    guidance: GuidanceLaw = GuidanceLaw(params=guidance_params)

    # Subsistema de Seguridad (Feature 005)
    safety: SafetyFilter = SafetyFilter(params=safety_params)

    # Subsistema de Métricas (Feature 004)
    metrics: MetricsLogger = MetricsLogger()

    try:
        # ──────────────────────────────────────────────────────────
        # 3. Arranque: Visión + Conexión MAVLink + Offboard
        # ──────────────────────────────────────────────────────────
        logger.info("Iniciando subsistema de visión (hilo Productor)…")
        camera.start()
        vision_pipeline.start()

        logger.info("Conectando al piloto automático vía MAVSDK…")
        await mavlink.connect()

        logger.info("Activando modo Offboard…")
        await mavlink.start_offboard()

        # Estado del lazo de control.
        last_loop_time: float = time.time()
        last_target_time: float = time.time()

        logger.info("═══════════════════════════════════════════")
        logger.info("  QUILLINCHU AI — ORQUESTADOR CENTRAL ACTIVO")
        logger.info("  Presiona Ctrl+C para apagado seguro.")
        logger.info("═══════════════════════════════════════════")

        # ──────────────────────────────────────────────────────────
        # 4. Lazo principal (while True) — Consumidor
        # ──────────────────────────────────────────────────────────
        while True:
            current_time: float = time.time()
            dt: float = current_time - last_loop_time
            last_loop_time = current_time

            # 4a. Obtener detecciones de la cola (no bloqueante).
            targets: List[TargetState] = []
            try:
                targets = detection_queue.get_nowait()
            except queue.Empty:
                pass

            # 4b. Si hay detecciones, actualizar last_target_time.
            error_x: float = 0.0
            error_y: float = 0.0

            if targets:
                selected: TargetState = max(
                    targets, key=lambda t: t.confidence
                )
                last_target_time = current_time

                # Calcular errores de píxeles para métricas.
                cx: float = guidance_params.image_width / 2.0
                cy: float = guidance_params.image_height / 2.0
                x_min, y_min, x_max, y_max = selected.bbox
                error_x = ((x_min + x_max) / 2.0) - cx
                error_y = ((y_min + y_max) / 2.0) - cy

            # 4c. Calcular comando crudo con GuidanceLaw PID.
            raw_cmd: Optional[VelocityCommand] = guidance.compute(targets)
            if raw_cmd is None:
                raw_cmd = VelocityCommand()

            # 4d. Mutar con SafetyFilter (clamping + Hovering failsafe).
            safe_cmd: VelocityCommand = safety.apply(
                cmd=raw_cmd,
                last_target_time=last_target_time,
                current_time=current_time,
            )

            # 4e. Enviar comando seguro a MAVSDK.
            await mavlink.send_velocity_cmd(safe_cmd)

            # 4f. Registrar iteración en MetricsLogger (RAM pura).
            metrics.log_iteration(
                dt=dt,
                error_x=error_x,
                error_y=error_y,
                vel_forward=safe_cmd.forward_m_s,
                vel_yaw=safe_cmd.yawspeed_deg_s,
            )

            # 4g. Controlar tasa de actualización (~30 Hz).
            await asyncio.sleep(_LOOP_PERIOD_S)

    except asyncio.CancelledError:
        logger.info("Lazo principal cancelado por señal externa.")
    except Exception as exc:
        logger.error(
            "Error inesperado en el lazo principal: %s", exc, exc_info=True
        )
    finally:
        # ──────────────────────────────────────────────────────────
        # 5. Apagado seguro (Graceful Shutdown)
        # ──────────────────────────────────────────────────────────
        logger.info("═══════════════════════════════════════════")
        logger.info("  INICIANDO SECUENCIA DE APAGADO SEGURO")
        logger.info("═══════════════════════════════════════════")

        # 5a. Detener modo Offboard y cerrar conexión MAVSDK.
        try:
            await mavlink.close()
            logger.info("Conexión MAVLink cerrada correctamente.")
        except Exception as exc:
            logger.error("Error al cerrar MAVLink: %s", exc)

        # 5b. Detener pipeline de visión y cámara.
        try:
            vision_pipeline.stop()
            camera.stop()
            logger.info("Pipeline de visión detenido.")
        except Exception as exc:
            logger.error("Error al detener visión: %s", exc)

        # 5c. Exportar métricas científicas a CSV.
        try:
            filepath: str = metrics.export_to_csv(params=guidance_params)
            logger.info("Métricas exportadas: %s", filepath)
        except RuntimeError as exc:
            logger.warning("No se exportaron métricas: %s", exc)
        except Exception as exc:
            logger.error("Fallo al exportar CSV de métricas: %s", exc)

        logger.info("Apagado seguro completado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(
            "Interrupción por teclado (Ctrl+C) detectada. Saliendo…"
        )
