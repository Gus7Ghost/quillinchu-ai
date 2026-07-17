"""
Suite de pruebas unitarias del módulo de visión — Quillinchu AI.

Valida el comportamiento de todos los componentes del pipeline de visión
mediante mocks, sin dependencias de hardware (GStreamer, GPU, pesos .pt).

References:
    - plan.md §5: Suite de pruebas unitarias y validación de Hz.
    - tech-stack.md: «pytest y unittest para verificar de forma robusta
      la suite de visión, control y seguridad».
    - spec.md: Criterios de aceptación verificables.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Optional
from unittest.mock import MagicMock, PropertyMock, patch

import numpy as np
import pytest

from src.vision import Detection, TargetState
from src.vision.camera_reader import CameraReader
from src.vision.detector import HeadDetector
from src.vision.tracker import DeepSortTracker
from src.vision.pipeline import VisionPipeline


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


def _make_detection(
    x_min: float = 100.0,
    y_min: float = 50.0,
    x_max: float = 150.0,
    y_max: float = 100.0,
    confidence: float = 0.85,
) -> Detection:
    """Crea una Detection de prueba con valores predeterminados."""
    return Detection(bbox=(x_min, y_min, x_max, y_max), confidence=confidence)


# ===========================================================================
# TestTargetState
# ===========================================================================


class TestTargetState:
    """Valida la estructura de datos TargetState."""

    def test_creation_with_defaults(self) -> None:
        """TargetState se crea correctamente con timestamp automático."""
        target = TargetState(
            track_id=1,
            bbox=(10.0, 20.0, 30.0, 40.0),
            confidence=0.9,
        )
        assert target.track_id == 1
        assert target.bbox == (10.0, 20.0, 30.0, 40.0)
        assert target.confidence == 0.9
        assert target.timestamp > 0.0

    def test_creation_with_explicit_timestamp(self) -> None:
        """TargetState acepta un timestamp explícito."""
        ts = 12345.6789
        target = TargetState(
            track_id=2,
            bbox=(0.0, 0.0, 50.0, 50.0),
            confidence=0.75,
            timestamp=ts,
        )
        assert target.timestamp == ts

    def test_immutability(self) -> None:
        """TargetState es inmutable (frozen dataclass)."""
        target = TargetState(
            track_id=1,
            bbox=(10.0, 20.0, 30.0, 40.0),
            confidence=0.9,
        )
        with pytest.raises(AttributeError):
            target.track_id = 99  # type: ignore[misc]

    def test_fields_types(self) -> None:
        """Los campos de TargetState tienen los tipos correctos."""
        target = TargetState(
            track_id=5,
            bbox=(1.0, 2.0, 3.0, 4.0),
            confidence=0.5,
            timestamp=100.0,
        )
        assert isinstance(target.track_id, int)
        assert isinstance(target.bbox, tuple)
        assert len(target.bbox) == 4
        assert isinstance(target.confidence, float)
        assert isinstance(target.timestamp, float)


# ===========================================================================
# TestDetection
# ===========================================================================


class TestDetection:
    """Valida la estructura de datos Detection."""

    def test_creation(self) -> None:
        """Detection se crea correctamente como NamedTuple."""
        det = Detection(bbox=(10.0, 20.0, 30.0, 40.0), confidence=0.8)
        assert det.bbox == (10.0, 20.0, 30.0, 40.0)
        assert det.confidence == 0.8

    def test_unpacking(self) -> None:
        """Detection soporta unpacking posicional."""
        det = Detection(bbox=(1.0, 2.0, 3.0, 4.0), confidence=0.6)
        bbox, conf = det
        assert bbox == (1.0, 2.0, 3.0, 4.0)
        assert conf == 0.6


# ===========================================================================
# TestCameraReader
# ===========================================================================


class TestCameraReader:
    """Valida el lector de cámara GStreamer con mocks."""

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

    def test_read_returns_none_before_start(self) -> None:
        """read() devuelve (False, None) si no se ha iniciado la captura."""
        reader = CameraReader()
        ret, frame = reader.read()
        assert ret is False
        assert frame is None

    def test_is_opened_before_start(self) -> None:
        """is_opened() devuelve False antes de iniciar."""
        reader = CameraReader()
        assert reader.is_opened() is False

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


# ===========================================================================
# TestHeadDetector
# ===========================================================================


class TestHeadDetector:
    """Valida el detector de cabezas con mock del modelo YOLO."""

    @patch("src.vision.detector.YOLO")
    def test_detect_returns_detections(self, mock_yolo_class: MagicMock) -> None:
        """detect() devuelve lista de Detection con formato correcto."""
        # Configurar mock del modelo YOLO.
        mock_model = MagicMock()
        mock_yolo_class.return_value = mock_model

        # Simular resultado de inferencia.
        mock_box = MagicMock()
        mock_box.xyxy = [MagicMock()]
        mock_box.xyxy[0].cpu.return_value.numpy.return_value = np.array(
            [100.0, 50.0, 200.0, 150.0]
        )
        mock_box.conf = [MagicMock()]
        mock_box.conf[0].cpu.return_value.numpy.return_value = np.float64(
            0.92
        )

        mock_result = MagicMock()
        mock_result.boxes = [mock_box]
        mock_model.predict.return_value = [mock_result]

        detector = HeadDetector(weights_path="test.pt")
        frame = _make_dummy_frame()
        detections = detector.detect(frame)

        assert len(detections) == 1
        assert isinstance(detections[0], Detection)
        assert detections[0].bbox == (100.0, 50.0, 200.0, 150.0)
        assert abs(detections[0].confidence - 0.92) < 1e-6

    @patch("src.vision.detector.YOLO")
    def test_detect_empty_results(self, mock_yolo_class: MagicMock) -> None:
        """detect() devuelve lista vacía cuando no hay detecciones."""
        mock_model = MagicMock()
        mock_yolo_class.return_value = mock_model

        mock_result = MagicMock()
        mock_result.boxes = []
        mock_model.predict.return_value = [mock_result]

        detector = HeadDetector(weights_path="test.pt")
        detections = detector.detect(_make_dummy_frame())

        assert detections == []

    @patch("src.vision.detector.YOLO")
    def test_confidence_threshold_setter(
        self, mock_yolo_class: MagicMock
    ) -> None:
        """El setter de confidence_threshold valida el rango [0.0, 1.0]."""
        mock_yolo_class.return_value = MagicMock()
        detector = HeadDetector(weights_path="test.pt")

        detector.confidence_threshold = 0.7
        assert detector.confidence_threshold == 0.7

        with pytest.raises(ValueError):
            detector.confidence_threshold = 1.5

        with pytest.raises(ValueError):
            detector.confidence_threshold = -0.1

    @patch("src.vision.detector.YOLO")
    def test_detect_multiple_boxes(self, mock_yolo_class: MagicMock) -> None:
        """detect() devuelve múltiples detecciones correctamente."""
        mock_model = MagicMock()
        mock_yolo_class.return_value = mock_model

        boxes = []
        for i in range(3):
            mock_box = MagicMock()
            offset = float(i * 100)
            mock_box.xyxy = [MagicMock()]
            mock_box.xyxy[0].cpu.return_value.numpy.return_value = np.array(
                [offset, offset, offset + 50, offset + 50]
            )
            mock_box.conf = [MagicMock()]
            mock_box.conf[0].cpu.return_value.numpy.return_value = np.float64(
                0.8 + i * 0.05
            )
            boxes.append(mock_box)

        mock_result = MagicMock()
        mock_result.boxes = boxes
        mock_model.predict.return_value = [mock_result]

        detector = HeadDetector(weights_path="test.pt")
        detections = detector.detect(_make_dummy_frame())

        assert len(detections) == 3
        for det in detections:
            assert isinstance(det, Detection)
            assert len(det.bbox) == 4


# ===========================================================================
# TestDeepSortTracker
# ===========================================================================


class TestDeepSortTracker:
    """Valida el tracker Deep SORT con mocks."""

    @patch("src.vision.tracker.DeepSort")
    def test_update_returns_target_states(
        self, mock_ds_class: MagicMock
    ) -> None:
        """update() devuelve TargetState con IDs y bboxes correctos."""
        mock_tracker = MagicMock()
        mock_ds_class.return_value = mock_tracker

        # Simular un track confirmado.
        mock_track = MagicMock()
        mock_track.is_confirmed.return_value = True
        mock_track.track_id = 1
        mock_track.to_ltrb.return_value = [100.0, 50.0, 200.0, 150.0]
        mock_tracker.update_tracks.return_value = [mock_track]

        tracker = DeepSortTracker()
        detections = [_make_detection()]
        frame = _make_dummy_frame()

        targets = tracker.update(detections, frame)

        assert len(targets) == 1
        assert isinstance(targets[0], TargetState)
        assert targets[0].track_id == 1
        assert targets[0].bbox == (100.0, 50.0, 200.0, 150.0)
        assert targets[0].timestamp > 0.0

    @patch("src.vision.tracker.DeepSort")
    def test_unconfirmed_tracks_excluded(
        self, mock_ds_class: MagicMock
    ) -> None:
        """update() excluye tracks no confirmados."""
        mock_tracker = MagicMock()
        mock_ds_class.return_value = mock_tracker

        mock_track = MagicMock()
        mock_track.is_confirmed.return_value = False
        mock_tracker.update_tracks.return_value = [mock_track]

        tracker = DeepSortTracker()
        targets = tracker.update([_make_detection()], _make_dummy_frame())

        assert len(targets) == 0

    @patch("src.vision.tracker.DeepSort")
    def test_id_consistency_across_frames(
        self, mock_ds_class: MagicMock
    ) -> None:
        """El mismo objeto en frames consecutivos conserva el mismo ID."""
        mock_tracker = MagicMock()
        mock_ds_class.return_value = mock_tracker

        # Simular el mismo track en múltiples frames.
        mock_track = MagicMock()
        mock_track.is_confirmed.return_value = True
        mock_track.track_id = 42
        mock_track.to_ltrb.return_value = [100.0, 50.0, 200.0, 150.0]
        mock_tracker.update_tracks.return_value = [mock_track]

        tracker = DeepSortTracker()
        detection = _make_detection()
        frame = _make_dummy_frame()

        ids: list[int] = []
        for _ in range(10):
            targets = tracker.update([detection], frame)
            if targets:
                ids.append(targets[0].track_id)

        # Todos los IDs deben ser idénticos.
        assert len(set(ids)) == 1
        assert ids[0] == 42

    @patch("src.vision.tracker.DeepSort")
    def test_id_retention_after_occlusion(
        self, mock_ds_class: MagicMock
    ) -> None:
        """Deep SORT retiene el ID después de una oclusión temporal.

        Simula la desaparición del objetivo por ~30 frames y verifica
        que el tracker reasigna el mismo ID al reaparecer.
        """
        mock_tracker = MagicMock()
        mock_ds_class.return_value = mock_tracker

        mock_track = MagicMock()
        mock_track.is_confirmed.return_value = True
        mock_track.track_id = 7
        mock_track.to_ltrb.return_value = [120.0, 60.0, 180.0, 120.0]

        tracker = DeepSortTracker(max_age=30)
        detection = _make_detection(120.0, 60.0, 180.0, 120.0)
        frame = _make_dummy_frame()

        # Fase 1: Objetivo visible (5 frames).
        mock_tracker.update_tracks.return_value = [mock_track]
        pre_occlusion_ids: list[int] = []
        for _ in range(5):
            targets = tracker.update([detection], frame)
            if targets:
                pre_occlusion_ids.append(targets[0].track_id)

        # Fase 2: Oclusión (30 frames, sin detecciones visibles).
        mock_tracker.update_tracks.return_value = []
        for _ in range(30):
            tracker.update([], frame)

        # Fase 3: Reaparición con el mismo ID.
        mock_tracker.update_tracks.return_value = [mock_track]
        post_occlusion_ids: list[int] = []
        for _ in range(5):
            targets = tracker.update([detection], frame)
            if targets:
                post_occlusion_ids.append(targets[0].track_id)

        # El ID debe ser el mismo antes y después de la oclusión.
        assert len(pre_occlusion_ids) > 0
        assert len(post_occlusion_ids) > 0
        assert pre_occlusion_ids[0] == post_occlusion_ids[0]

    @patch("src.vision.tracker.DeepSort")
    def test_empty_detections(self, mock_ds_class: MagicMock) -> None:
        """update() con lista vacía de detecciones devuelve lista vacía."""
        mock_tracker = MagicMock()
        mock_ds_class.return_value = mock_tracker
        mock_tracker.update_tracks.return_value = []

        tracker = DeepSortTracker()
        targets = tracker.update([], _make_dummy_frame())

        assert targets == []

    @patch("src.vision.tracker.DeepSort")
    def test_reset(self, mock_ds_class: MagicMock) -> None:
        """reset() reinicializa el tracker de Deep SORT."""
        mock_ds_class.return_value = MagicMock()
        tracker = DeepSortTracker()

        tracker.reset()

        # Verificar que DeepSort se instanció dos veces (init + reset).
        assert mock_ds_class.call_count == 2


# ===========================================================================
# TestVisionPipeline
# ===========================================================================


class TestVisionPipeline:
    """Valida el orquestador del pipeline de visión."""

    def _build_mock_pipeline(
        self,
        num_targets: int = 1,
    ) -> tuple[VisionPipeline, queue.Queue[TargetState]]:
        """Construye un VisionPipeline con componentes mock.

        Returns:
            Tupla (pipeline, output_queue) para inspección en los tests.
        """
        mock_camera = MagicMock(spec=CameraReader)
        mock_camera.read.return_value = (True, _make_dummy_frame())

        mock_detector = MagicMock(spec=HeadDetector)
        detections = [_make_detection() for _ in range(num_targets)]
        mock_detector.detect.return_value = detections

        mock_tracker = MagicMock(spec=DeepSortTracker)
        targets = [
            TargetState(
                track_id=i + 1,
                bbox=(100.0, 50.0, 200.0, 150.0),
                confidence=0.9,
            )
            for i in range(num_targets)
        ]
        mock_tracker.update.return_value = targets

        output_queue: queue.Queue[TargetState] = queue.Queue(maxsize=4)

        pipeline = VisionPipeline(
            camera=mock_camera,
            detector=mock_detector,
            tracker=mock_tracker,
            output_queue=output_queue,
        )

        return pipeline, output_queue

    def test_pipeline_publishes_target_state(self) -> None:
        """El pipeline publica TargetState en la cola de salida."""
        pipeline, output_queue = self._build_mock_pipeline()

        pipeline.start()
        time.sleep(0.15)
        pipeline.stop()

        assert not output_queue.empty()
        target = output_queue.get_nowait()
        assert isinstance(target, TargetState)
        assert target.track_id == 1

    def test_pipeline_non_blocking_publish(self) -> None:
        """La publicación no bloquea cuando la cola está llena."""
        pipeline, output_queue = self._build_mock_pipeline()

        # Cola de tamaño 1 para forzar el descarte.
        small_queue: queue.Queue[TargetState] = queue.Queue(maxsize=1)
        pipeline._output_queue = small_queue

        pipeline.start()
        time.sleep(0.15)
        pipeline.stop()

        # La cola debe tener exactamente 1 elemento (el más reciente).
        assert small_queue.qsize() <= 1

    def test_pipeline_fps_reporting(self) -> None:
        """get_fps() devuelve un valor positivo después de procesar frames."""
        pipeline, _ = self._build_mock_pipeline()

        pipeline.start()
        time.sleep(1.2)  # Esperar al menos un intervalo de medición de FPS.
        fps = pipeline.get_fps()
        pipeline.stop()

        assert fps > 0.0

    def test_pipeline_throughput_above_15hz(self) -> None:
        """El pipeline con mocks ligeros supera la meta de 15 Hz.

        Nota: Esta prueba valida que el pipeline no introduce cuellos
        de botella propios. La validación real en hardware se realiza
        manualmente en el laboratorio.
        """
        pipeline, _ = self._build_mock_pipeline()

        pipeline.start()
        time.sleep(1.5)
        fps = pipeline.get_fps()
        pipeline.stop()

        assert fps >= 15.0, (
            f"FPS del pipeline ({fps:.1f} Hz) por debajo del mínimo "
            f"científico de 15 Hz."
        )

    def test_pipeline_stop_idempotent(self) -> None:
        """stop() es seguro de llamar múltiples veces."""
        pipeline, _ = self._build_mock_pipeline()

        pipeline.start()
        time.sleep(0.05)
        pipeline.stop()
        pipeline.stop()  # No debe lanzar excepción.

    def test_pipeline_handles_no_frame(self) -> None:
        """El pipeline continúa sin error cuando la cámara no devuelve frame."""
        mock_camera = MagicMock(spec=CameraReader)
        mock_camera.read.return_value = (False, None)

        mock_detector = MagicMock(spec=HeadDetector)
        mock_tracker = MagicMock(spec=DeepSortTracker)
        output_queue: queue.Queue[TargetState] = queue.Queue(maxsize=4)

        pipeline = VisionPipeline(
            camera=mock_camera,
            detector=mock_detector,
            tracker=mock_tracker,
            output_queue=output_queue,
        )

        pipeline.start()
        time.sleep(0.1)
        pipeline.stop()

        # El detector no debe haber sido invocado.
        mock_detector.detect.assert_not_called()
        assert output_queue.empty()

    def test_pipeline_multiple_targets(self) -> None:
        """El pipeline publica múltiples TargetState cuando hay varios tracks."""
        pipeline, output_queue = self._build_mock_pipeline(num_targets=3)

        pipeline.start()
        time.sleep(0.15)
        pipeline.stop()

        targets: list[TargetState] = []
        while not output_queue.empty():
            targets.append(output_queue.get_nowait())

        assert len(targets) >= 1
        for target in targets:
            assert isinstance(target, TargetState)
