"""
Pruebas unitarias del lector de cámara GStreamer — Quillinchu AI.

Valida el comportamiento de ``CameraReader`` de forma aislada, sin
dependencias de hardware (GStreamer, cámara) ni de librerías pesadas
(ultralytics, deep_sort_realtime).

Estas pruebas pueden ejecutarse con el Python del sistema:
    /usr/bin/python3 -m pytest tests/test_camera_reader.py -v

References:
    - plan.md §1: Configuración de la captura de video por red (GStreamer).
    - spec.md: Criterio «flujo de video se lee y decodifica desde UDP 5600».
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.vision.camera_reader import CameraReader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dummy_frame(
    width: int = 1280,
    height: int = 720,
    channels: int = 3,
) -> np.ndarray:
    """Genera un frame BGR sintético para pruebas."""
    return np.random.randint(
        0, 255, (height, width, channels), dtype=np.uint8
    )


# ===========================================================================
# TestCameraReader — Pipeline GStreamer
# ===========================================================================


class TestCameraReaderPipeline:
    """Valida la configuración del pipeline GStreamer."""

    def test_gst_pipeline_format(self) -> None:
        """El pipeline GStreamer contiene el puerto y dimensiones correctas."""
        reader = CameraReader(port=5600, width=1920, height=1080)
        pipeline = reader.gst_pipeline
        assert "port=5600" in pipeline
        assert "width=1920" in pipeline
        assert "height=1080" in pipeline
        assert "appsink" in pipeline
        assert "drop=true" in pipeline

    def test_default_parameters(self) -> None:
        """CameraReader usa valores por defecto correctos."""
        reader = CameraReader()
        pipeline = reader.gst_pipeline
        assert "port=5600" in pipeline
        assert "width=1280" in pipeline
        assert "height=720" in pipeline

    def test_gst_pipeline_contains_rtp_elements(self) -> None:
        """El pipeline GStreamer incluye la cadena completa RTP/H.264."""
        reader = CameraReader()
        pipeline = reader.gst_pipeline
        assert "udpsrc" in pipeline
        assert "rtph264depay" in pipeline
        assert "h264parse" in pipeline
        assert "avdec_h264" in pipeline
        assert "videoconvert" in pipeline
        assert "format=BGR" in pipeline

    def test_custom_port(self) -> None:
        """El pipeline acepta puertos personalizados."""
        reader = CameraReader(port=5601)
        assert "port=5601" in reader.gst_pipeline
        assert reader.port == 5601


# ===========================================================================
# TestCameraReader — Propiedades
# ===========================================================================


class TestCameraReaderProperties:
    """Valida las propiedades de acceso de CameraReader."""

    def test_property_accessors(self) -> None:
        """Las propiedades port, width, height devuelven valores correctos."""
        reader = CameraReader(port=5601, width=1920, height=1080)
        assert reader.port == 5601
        assert reader.width == 1920
        assert reader.height == 1080

    def test_repr_stopped(self) -> None:
        """__repr__() muestra estado 'stopped' cuando no está en ejecución."""
        reader = CameraReader(port=5600, width=1280, height=720)
        assert "5600" in repr(reader)
        assert "1280x720" in repr(reader)
        assert "stopped" in repr(reader)

    def test_is_opened_before_start(self) -> None:
        """is_opened() devuelve False antes de iniciar."""
        reader = CameraReader()
        assert reader.is_opened() is False

    def test_read_returns_none_before_start(self) -> None:
        """read() devuelve (False, None) si no se ha iniciado la captura."""
        reader = CameraReader()
        ret, frame = reader.read()
        assert ret is False
        assert frame is None


# ===========================================================================
# TestCameraReader — Captura con mocks
# ===========================================================================


class TestCameraReaderCapture:
    """Valida la captura de video con mocks de VideoCapture."""

    @patch("src.vision.camera_reader.cv2.VideoCapture")
    def test_start_and_read(self, mock_vc_class: MagicMock) -> None:
        """start() lanza el hilo y read() devuelve el frame capturado."""
        dummy_frame = _make_dummy_frame()
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.read.return_value = (True, dummy_frame)
        mock_vc_class.return_value = mock_capture

        reader = CameraReader()
        reader.start()

        # Esperar a que el hilo de captura procese al menos un frame.
        time.sleep(0.1)

        ret, frame = reader.read()
        assert ret is True
        assert frame is not None
        assert frame.shape == dummy_frame.shape

        reader.stop()

    @patch("src.vision.camera_reader.cv2.VideoCapture")
    def test_start_raises_on_failed_open(
        self, mock_vc_class: MagicMock
    ) -> None:
        """start() lanza RuntimeError si VideoCapture no se puede abrir."""
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = False
        mock_vc_class.return_value = mock_capture

        reader = CameraReader()
        with pytest.raises(RuntimeError, match="No se pudo abrir"):
            reader.start()

    @patch("src.vision.camera_reader.cv2.VideoCapture")
    def test_stop_releases_resources(self, mock_vc_class: MagicMock) -> None:
        """stop() detiene el hilo y libera el VideoCapture."""
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.read.return_value = (True, _make_dummy_frame())
        mock_vc_class.return_value = mock_capture

        reader = CameraReader()
        reader.start()
        time.sleep(0.05)
        reader.stop()

        mock_capture.release.assert_called_once()

    @patch("src.vision.camera_reader.cv2.VideoCapture")
    def test_read_returns_copy(self, mock_vc_class: MagicMock) -> None:
        """read() devuelve una copia del frame, no una referencia."""
        dummy_frame = _make_dummy_frame()
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.read.return_value = (True, dummy_frame)
        mock_vc_class.return_value = mock_capture

        reader = CameraReader()
        reader.start()
        time.sleep(0.1)

        _, frame1 = reader.read()
        _, frame2 = reader.read()

        # Deben ser copias independientes.
        assert frame1 is not frame2

        reader.stop()

    @patch("src.vision.camera_reader.cv2.VideoCapture")
    def test_stop_clears_frame_state(self, mock_vc_class: MagicMock) -> None:
        """stop() limpia el frame almacenado y el flag de retorno."""
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.read.return_value = (True, _make_dummy_frame())
        mock_vc_class.return_value = mock_capture

        reader = CameraReader()
        reader.start()
        time.sleep(0.05)
        reader.stop()

        ret, frame = reader.read()
        assert ret is False
        assert frame is None

    @patch("src.vision.camera_reader.cv2.VideoCapture")
    def test_start_idempotent(self, mock_vc_class: MagicMock) -> None:
        """Llamar start() dos veces no crea hilos duplicados."""
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.read.return_value = (True, _make_dummy_frame())
        mock_vc_class.return_value = mock_capture

        reader = CameraReader()
        reader.start()
        reader.start()  # No debe lanzar excepción ni crear otro hilo.

        # VideoCapture solo se instanció una vez.
        assert mock_vc_class.call_count == 1

        reader.stop()


# ===========================================================================
# TestCameraReader — API Asíncrona
# ===========================================================================


class TestCameraReaderAsync:
    """Valida la interfaz asíncrona para integración con asyncio."""

    @patch("src.vision.camera_reader.cv2.VideoCapture")
    def test_read_async_returns_frame(self, mock_vc_class: MagicMock) -> None:
        """read_async() devuelve el frame más reciente vía asyncio."""
        dummy_frame = _make_dummy_frame()
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.read.return_value = (True, dummy_frame)
        mock_vc_class.return_value = mock_capture

        reader = CameraReader()
        reader.start()
        time.sleep(0.1)

        async def _test() -> tuple[bool, Optional[np.ndarray]]:
            return await reader.read_async()

        ret, frame = asyncio.run(_test())
        assert ret is True
        assert frame is not None
        assert frame.shape == dummy_frame.shape

        reader.stop()

    def test_read_async_before_start(self) -> None:
        """read_async() devuelve (False, None) si no se ha iniciado."""
        reader = CameraReader()

        async def _test() -> tuple[bool, Optional[np.ndarray]]:
            return await reader.read_async()

        ret, frame = asyncio.run(_test())
        assert ret is False
        assert frame is None

    @patch("src.vision.camera_reader.cv2.VideoCapture")
    def test_read_async_does_not_block_event_loop(
        self, mock_vc_class: MagicMock
    ) -> None:
        """read_async() se ejecuta concurrentemente con otras coroutines."""
        dummy_frame = _make_dummy_frame()
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.read.return_value = (True, dummy_frame)
        mock_vc_class.return_value = mock_capture

        reader = CameraReader()
        reader.start()
        time.sleep(0.1)

        async def _test() -> None:
            # Ejecutar read_async concurrentemente con un sleep.
            result, other = await asyncio.gather(
                reader.read_async(),
                asyncio.sleep(0.01, result="done"),
            )
            ret, frame = result
            assert ret is True
            assert frame is not None
            assert other == "done"

        asyncio.run(_test())
        reader.stop()


# ===========================================================================
# TestCameraReader — Context Manager
# ===========================================================================


class TestCameraReaderContextManager:
    """Valida el protocolo de context manager (with statement)."""

    @patch("src.vision.camera_reader.cv2.VideoCapture")
    def test_context_manager_starts_and_stops(
        self, mock_vc_class: MagicMock
    ) -> None:
        """CameraReader funciona como context manager (with statement)."""
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.read.return_value = (True, _make_dummy_frame())
        mock_vc_class.return_value = mock_capture

        with CameraReader() as reader:
            time.sleep(0.05)
            assert reader._running is True

        # Después de salir del bloque, debe estar detenido.
        mock_capture.release.assert_called_once()

    @patch("src.vision.camera_reader.cv2.VideoCapture")
    def test_context_manager_on_exception(
        self, mock_vc_class: MagicMock
    ) -> None:
        """El context manager libera recursos incluso ante excepciones."""
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.read.return_value = (True, _make_dummy_frame())
        mock_vc_class.return_value = mock_capture

        with pytest.raises(ValueError):
            with CameraReader() as reader:
                time.sleep(0.05)
                raise ValueError("Error de prueba")

        # Recursos liberados a pesar de la excepción.
        mock_capture.release.assert_called_once()
