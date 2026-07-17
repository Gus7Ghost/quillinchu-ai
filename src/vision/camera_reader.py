"""
Lector de cámara asíncrono con GStreamer — Quillinchu AI.

Captura el flujo de video RTP/H.264 retransmitido por Rosetta Drone
en el puerto UDP 5600 mediante un pipeline de GStreamer. Un hilo daemon
de captura continua descarta activamente los frames acumulados en el
buffer, garantizando que el consumidor siempre acceda al frame más
reciente en tiempo real.

El módulo expone tanto una API síncrona (``read``) como una API
asíncrona (``read_async``) para integración directa con el event loop
de ``asyncio`` sin bloquear el hilo principal ni el lazo de control
de MAVSDK.

IMPORTANTE — Compatibilidad con Ubuntu:
    Este módulo está diseñado para ejecutarse con el OpenCV del sistema
    (``python3-opencv 4.6.0``, paquete ``apt``) que incluye soporte
    nativo para GStreamer. **NO** utilizar el OpenCV de Conda/pip
    (``opencv-contrib-python``) ya que carece de backend GStreamer y
    provoca ``free(): invalid pointer`` por conflicto de bibliotecas
    compartidas.

References:
    - plan.md §1: Configuración de la captura de video por red (GStreamer).
    - spec.md: Criterio «flujo de video se lee y decodifica correctamente
      desde el puerto UDP 5600».
    - tech-stack.md: «Desacoplamiento computacional estricto».
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Formato estándar del pipeline GStreamer para Rosetta Drone.
_GST_PIPELINE_TEMPLATE: str = (
    "udpsrc port={port} "
    "! application/x-rtp,encoding-name=H264,payload=96 "
    "! rtph264depay "
    "! h264parse "
    "! avdec_h264 "
    "! videoconvert "
    "! video/x-raw,format=BGR,width={width},height={height} "
    "! appsink drop=true sync=false"
)


class CameraReader:
    """Lector de video GStreamer con descarte activo de frames antiguos.

    El hilo interno de captura lee continuamente del ``VideoCapture`` y
    retiene exclusivamente el frame más reciente bajo un ``threading.Lock``,
    eliminando la latencia acumulada por el buffer de OpenCV/GStreamer.

    Ofrece dos interfaces de lectura:
    - ``read()``: Síncrona, thread-safe, para uso directo en hilos.
    - ``read_async()``: Asíncrona, para uso dentro de un ``asyncio``
      event loop sin bloquear el hilo del bucle principal.

    Args:
        port: Puerto UDP de escucha del stream RTP/H.264 (default: 5600).
        width: Ancho esperado del frame decodificado en píxeles.
        height: Alto esperado del frame decodificado en píxeles.
    """

    def __init__(
        self,
        port: int = 5600,
        width: int = 1280,
        height: int = 720,
    ) -> None:
        self._port: int = port
        self._width: int = width
        self._height: int = height

        # Pipeline GStreamer para decodificación RTP/H.264 vía UDP.
        self._gst_pipeline: str = _GST_PIPELINE_TEMPLATE.format(
            port=self._port,
            width=self._width,
            height=self._height,
        )

        self._capture: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._ret: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Propiedades de solo lectura
    # ------------------------------------------------------------------

    @property
    def gst_pipeline(self) -> str:
        """Devuelve el string del pipeline GStreamer configurado."""
        return self._gst_pipeline

    @property
    def port(self) -> int:
        """Puerto UDP configurado para la recepción del stream."""
        return self._port

    @property
    def width(self) -> int:
        """Ancho del frame decodificado en píxeles."""
        return self._width

    @property
    def height(self) -> int:
        """Alto del frame decodificado en píxeles."""
        return self._height

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Abre la captura de video y lanza el hilo de lectura continua.

        Raises:
            RuntimeError: Si el ``VideoCapture`` no se puede abrir (e.g.,
                GStreamer no instalado o Rosetta Drone no transmitiendo).
        """
        if self._running:
            logger.warning("CameraReader ya se encuentra en ejecución.")
            return

        self._capture = cv2.VideoCapture(
            self._gst_pipeline, cv2.CAP_GSTREAMER
        )

        if not self._capture.isOpened():
            raise RuntimeError(
                f"No se pudo abrir el stream GStreamer en UDP:{self._port}. "
                "Verifica que Rosetta Drone esté transmitiendo y que "
                "GStreamer esté instalado correctamente en el sistema. "
                "NOTA: Usa el OpenCV del sistema (apt), NO el de Conda/pip."
            )

        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="CameraReader-CaptureThread",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "CameraReader iniciado — escuchando UDP:%d (%dx%d).",
            self._port,
            self._width,
            self._height,
        )

    def _capture_loop(self) -> None:
        """Bucle de captura continua que retiene solo el frame más reciente.

        Se ejecuta en un hilo daemon dedicado. Cada iteración lee un frame
        nuevo y lo almacena bajo ``_lock``, descartando implícitamente el
        anterior. Si la lectura falla, señaliza la detención del lector.

        Este diseño elimina la latencia acumulada: cuando el consumidor
        llama a ``read()`` o ``read_async()``, siempre obtiene el frame
        más reciente sin importar cuánto tiempo haya pasado desde la
        última lectura.
        """
        while self._running:
            if self._capture is None:
                break

            ret, frame = self._capture.read()

            if not ret:
                logger.warning(
                    "Lectura de frame fallida — posible desconexión del stream."
                )
                continue

            with self._lock:
                self._ret = ret
                self._frame = frame

        logger.info("Hilo de captura detenido.")

    # ------------------------------------------------------------------
    # Lectura síncrona (thread-safe)
    # ------------------------------------------------------------------

    def read(self) -> tuple[bool, Optional[np.ndarray]]:
        """Devuelve el frame más reciente de forma thread-safe.

        Returns:
            Tupla ``(success, frame)`` donde ``success`` indica si hay un
            frame válido disponible y ``frame`` es el array NumPy BGR o
            ``None`` si aún no se ha capturado ningún frame.

        Note:
            El frame devuelto es una **copia independiente** para evitar
            condiciones de carrera con el hilo de captura.
        """
        with self._lock:
            if self._frame is not None:
                return self._ret, self._frame.copy()
            return False, None

    # ------------------------------------------------------------------
    # Lectura asíncrona (asyncio-compatible)
    # ------------------------------------------------------------------

    async def read_async(self) -> tuple[bool, Optional[np.ndarray]]:
        """Devuelve el frame más reciente sin bloquear el event loop.

        Delega la lectura thread-safe a ``asyncio.get_event_loop()
        .run_in_executor()`` para que la adquisición del ``Lock`` y la
        copia del frame NumPy no bloqueen el bucle de ``asyncio`` donde
        coexiste el lazo de control de MAVSDK.

        Returns:
            Tupla ``(success, frame)`` idéntica a ``read()``.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.read)

    # ------------------------------------------------------------------
    # Liberación de recursos
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Detiene el hilo de captura y libera los recursos de OpenCV."""
        self._running = False

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None

        if self._capture is not None:
            self._capture.release()
            self._capture = None

        self._frame = None
        self._ret = False

        logger.info("CameraReader detenido y recursos liberados.")

    def is_opened(self) -> bool:
        """Consulta si la captura de video está activa.

        Returns:
            ``True`` si el ``VideoCapture`` subyacente está abierto.
        """
        if self._capture is not None:
            return self._capture.isOpened()
        return False

    # ------------------------------------------------------------------
    # Context Manager (para uso con `with`)
    # ------------------------------------------------------------------

    def __enter__(self) -> CameraReader:
        """Inicia la captura al entrar al bloque ``with``."""
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        """Detiene la captura al salir del bloque ``with``."""
        self.stop()

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return (
            f"CameraReader(port={self._port}, "
            f"{self._width}x{self._height}, {status})"
        )
