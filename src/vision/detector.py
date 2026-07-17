"""
Detector de cabezas con YOLOv8 — Quillinchu AI.

Carga los pesos personalizados ``HeadDetect.pt`` mediante la biblioteca
``ultralytics`` y ejecuta la inferencia sobre frames BGR, devolviendo
una lista de detecciones filtradas por confianza mínima.

References:
    - plan.md §2: Implementación de la detección de cabezas (YOLOv8).
    - mission.md: Modelo enfocado en diámetro cefálico (~0.23 m).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import numpy as np
from ultralytics import YOLO

from src.vision import Detection

logger = logging.getLogger(__name__)


class HeadDetector:
    """Detector de cabezas humanas basado en YOLOv8.

    Encapsula la carga del modelo y la inferencia, exponiendo una
    interfaz limpia que devuelve objetos ``Detection`` tipados.

    Args:
        weights_path: Ruta al archivo de pesos entrenados (default:
            ``HeadDetect.pt``).
        confidence: Umbral mínimo de confianza para aceptar una
            detección [0.0, 1.0] (default: 0.5).
        device: Dispositivo de inferencia — ``"cpu"`` o ``"cuda"``
            (default: ``"cpu"``).
    """

    def __init__(
        self,
        weights_path: Union[str, Path] = "HeadDetect.pt",
        confidence: float = 0.5,
        device: str = "cpu",
    ) -> None:
        self._weights_path: Path = Path(weights_path)
        self._confidence: float = confidence
        self._device: str = device

        self._model: YOLO = YOLO(str(self._weights_path))
        self._model.to(self._device)

        logger.info(
            "HeadDetector cargado — pesos: %s, confianza: %.2f, device: %s.",
            self._weights_path,
            self._confidence,
            self._device,
        )

    @property
    def confidence_threshold(self) -> float:
        """Devuelve el umbral de confianza configurado."""
        return self._confidence

    @confidence_threshold.setter
    def confidence_threshold(self, value: float) -> None:
        """Actualiza el umbral de confianza.

        Args:
            value: Nuevo umbral de confianza [0.0, 1.0].

        Raises:
            ValueError: Si el valor está fuera del rango válido.
        """
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"El umbral de confianza debe estar entre 0.0 y 1.0, "
                f"se recibió: {value}"
            )
        self._confidence = value

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Ejecuta la inferencia YOLOv8 sobre un frame BGR.

        Args:
            frame: Imagen BGR como array NumPy de forma ``(H, W, 3)``.

        Returns:
            Lista de ``Detection`` con las cajas delimitadoras y
            confianzas que superan el umbral configurado.
        """
        results = self._model.predict(
            source=frame,
            conf=self._confidence,
            device=self._device,
            verbose=False,
        )

        detections: list[Detection] = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())

                detection = Detection(
                    bbox=(
                        float(xyxy[0]),
                        float(xyxy[1]),
                        float(xyxy[2]),
                        float(xyxy[3]),
                    ),
                    confidence=conf,
                )
                detections.append(detection)

        return detections
