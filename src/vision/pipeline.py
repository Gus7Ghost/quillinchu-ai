"""
Pipeline de Visión (Productor-Consumidor) — Quillinchu AI.

Orquesta la lectura de video, inferencia YOLOv8 y tracking Deep SORT
en un hilo dedicado, publicando asíncronamente los resultados en una
cola compartida de forma no bloqueante. Garantiza el desacoplamiento
computacional estricto exigido por la constitución del proyecto.

References:
    - plan.md §4: Orquestación del pipeline de visión (Productor-Consumidor).
    - tech-stack.md: «El procesamiento gráfico del pipeline de visión
      jamás debe ser síncrono o ejecutarse en el mismo hilo que el bucle
      de envío de telemetría principal».
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import List, Optional

import numpy as np

from src.vision import TargetState
from src.vision.camera_reader import CameraReader
from src.vision.detector import HeadDetector
from src.vision.tracker import DeepSortTracker

logger = logging.getLogger(__name__)


class VisionPipeline:
    """Orquestador del pipeline de visión con patrón Productor-Consumidor.

    Ejecuta el ciclo completo captura→detección→tracking en un hilo
    dedicado y publica los ``TargetState`` resultantes en una cola
    compartida. Si la cola está llena, descarta el resultado más antiguo
    para evitar acumulación de latencia.

    Args:
        camera: Instancia de ``CameraReader`` configurada.
        detector: Instancia de ``HeadDetector`` con pesos cargados.
        tracker: Instancia de ``DeepSortTracker`` inicializado.
        output_queue: Cola thread-safe donde se publican los
            ``TargetState``. El consumidor (módulo de control)
            lee de esta cola.
        max_queue_size: Tamaño máximo de la cola de salida (default: 1).
            Un valor de 1 garantiza que el consumidor siempre obtiene
            el estado más reciente.
    """

    def __init__(
        self,
        camera: CameraReader,
        detector: HeadDetector,
        tracker: DeepSortTracker,
        output_queue: queue.Queue[List[TargetState]],
        max_queue_size: int = 1,
    ) -> None:
        self._camera: CameraReader = camera
        self._detector: HeadDetector = detector
        self._tracker: DeepSortTracker = tracker
        self._output_queue: queue.Queue[List[TargetState]] = output_queue
        self._max_queue_size: int = max_queue_size

        self._running: bool = False
        self._thread: Optional[threading.Thread] = None

        # Métricas de rendimiento.
        self._frame_count: int = 0
        self._fps: float = 0.0
        self._last_fps_time: float = 0.0
        self._fps_update_interval: float = 1.0  # Actualizar FPS cada 1s.

    def start(self) -> None:
        """Lanza el hilo del pipeline de visión (Productor).

        El hilo se ejecuta como daemon para garantizar la terminación
        automática al finalizar el proceso principal.
        """
        if self._running:
            logger.warning("VisionPipeline ya se encuentra en ejecución.")
            return

        self._running = True
        self._frame_count = 0
        self._fps = 0.0
        self._last_fps_time = time.perf_counter()

        self._thread = threading.Thread(
            target=self._run,
            name="VisionPipeline-ProducerThread",
            daemon=True,
        )
        self._thread.start()
        logger.info("VisionPipeline iniciado — hilo Productor en ejecución.")

    def _run(self) -> None:
        """Bucle principal del Productor: captura → detección → tracking.

        Publica cada ``TargetState`` en la cola de salida de forma no
        bloqueante. Si la cola alcanza su capacidad máxima, descarta el
        elemento más antiguo antes de insertar el nuevo, evitando que
        el consumidor procese información desactualizada.
        """
        while self._running:
            ret, frame = self._camera.read()

            if not ret or frame is None:
                continue

            # Detección de cabezas con YOLOv8.
            detections = self._detector.detect(frame)

            # Tracking con Deep SORT.
            targets = self._tracker.update(detections, frame)

            # Publicar la lista completa del frame (no bloqueante).
            self._publish(targets)

            # Actualizar métricas de FPS.
            self._update_fps()

        logger.info("Hilo Productor del VisionPipeline detenido.")

    def _publish(self, targets: List[TargetState]) -> None:
        """Publica la lista completa de ``TargetState`` del frame actual.

        Si la cola está llena, descarta la lista más antigua para
        garantizar que el consumidor siempre acceda al estado más reciente
        de la escena completa.

        Args:
            targets: Lista de estados de todos los objetivos detectados
                en el frame actual.
        """
        try:
            self._output_queue.put_nowait(targets)
        except queue.Full:
            try:
                # Descartar la lista más antigua.
                self._output_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._output_queue.put_nowait(targets)
            except queue.Full:
                logger.warning(
                    "Cola de salida llena — descartando lista de"
                    " TargetState del frame."
                )

    def _update_fps(self) -> None:
        """Actualiza la tasa de procesamiento (FPS) del pipeline.

        Calcula el FPS promedio sobre intervalos de 1 segundo para
        obtener una métrica estable y representativa.
        """
        self._frame_count += 1
        current_time: float = time.perf_counter()
        elapsed: float = current_time - self._last_fps_time

        if elapsed >= self._fps_update_interval:
            self._fps = self._frame_count / elapsed
            self._frame_count = 0
            self._last_fps_time = current_time

    def get_fps(self) -> float:
        """Devuelve la tasa de procesamiento instantánea en Hz.

        Returns:
            FPS promedio del último intervalo de medición.
        """
        return self._fps

    def stop(self) -> None:
        """Detiene el pipeline de visión y espera la finalización del hilo."""
        self._running = False

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3.0)
            self._thread = None

        logger.info("VisionPipeline detenido.")

    @property
    def is_running(self) -> bool:
        """Indica si el pipeline está en ejecución."""
        return self._running
