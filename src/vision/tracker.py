"""
Tracker multiobjetivo con Deep SORT — Quillinchu AI.

Integra el algoritmo de asociación temporal Deep SORT para asignar
identificadores únicos (IDs) persistentes a las cabezas detectadas,
tolerando oclusiones temporales de hasta ``max_age`` frames.

References:
    - plan.md §3: Configuración de seguimiento multiobjetivo (Deep SORT).
    - spec.md: Criterio «retener y recuperar el mismo ID único del objetivo
      si este sufre una oclusión temporal corta (≤30 frames)».
"""

from __future__ import annotations

import logging
import time

import numpy as np
from deep_sort_realtime.deepsort_tracker import DeepSort

from src.vision import Detection, TargetState

logger = logging.getLogger(__name__)


class DeepSortTracker:
    """Wrapper de Deep SORT para tracking robusto con IDs persistentes.

    Convierte las detecciones crudas del ``HeadDetector`` al formato
    requerido por ``deep_sort_realtime`` y devuelve objetos
    ``TargetState`` con identificadores estables.

    Args:
        max_age: Número máximo de frames sin detección antes de eliminar
            un track (default: 30, equivalente a ~1 segundo a 30 FPS).
        n_init: Número mínimo de detecciones consecutivas requeridas
            para confirmar un nuevo track (default: 3).
        max_cosine_distance: Distancia coseno máxima permitida para la
            asociación de embeddings de apariencia (default: 0.3).
    """

    def __init__(
        self,
        max_age: int = 30,
        n_init: int = 3,
        max_cosine_distance: float = 0.3,
    ) -> None:
        self._max_age: int = max_age
        self._n_init: int = n_init
        self._max_cosine_distance: float = max_cosine_distance

        self._tracker: DeepSort = DeepSort(
            max_age=self._max_age,
            n_init=self._n_init,
            max_cosine_distance=self._max_cosine_distance,
        )

        logger.info(
            "DeepSortTracker inicializado — max_age: %d, n_init: %d, "
            "max_cosine_dist: %.2f.",
            self._max_age,
            self._n_init,
            self._max_cosine_distance,
        )

    def update(
        self,
        detections: list[Detection],
        frame: np.ndarray,
    ) -> list[TargetState]:
        """Actualiza el tracker con las detecciones del frame actual.

        Convierte cada ``Detection`` al formato ``([x, y, w, h], conf, class)``
        requerido por ``deep_sort_realtime``, ejecuta la asociación temporal
        y devuelve los tracks confirmados como ``TargetState``.

        Args:
            detections: Lista de ``Detection`` producidas por ``HeadDetector``.
            frame: Frame BGR actual como array NumPy (requerido por Deep SORT
                para la extracción de embeddings de apariencia).

        Returns:
            Lista de ``TargetState`` con IDs persistentes, bounding boxes
            actualizados y marca de tiempo.
        """
        # Convertir detecciones al formato de deep_sort_realtime:
        # lista de ([left, top, w, h], confidence, detection_class)
        raw_detections: list[tuple[list[float], float, str]] = []

        for det in detections:
            x_min, y_min, x_max, y_max = det.bbox
            width = x_max - x_min
            height = y_max - y_min
            raw_detections.append(
                ([x_min, y_min, width, height], det.confidence, "head")
            )

        # Actualizar el tracker con las detecciones y el frame actual.
        tracks = self._tracker.update_tracks(
            raw_detections=raw_detections,
            frame=frame,
        )

        # Construir la lista de TargetState solo con tracks confirmados.
        timestamp: float = time.perf_counter()
        target_states: list[TargetState] = []

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id: int = track.track_id
            ltrb = track.to_ltrb()  # [left, top, right, bottom]

            target = TargetState(
                track_id=int(track_id),
                bbox=(
                    float(ltrb[0]),
                    float(ltrb[1]),
                    float(ltrb[2]),
                    float(ltrb[3]),
                ),
                confidence=detections[0].confidence if detections else 0.0,
                timestamp=timestamp,
            )
            target_states.append(target)

        return target_states

    def reset(self) -> None:
        """Reinicia el estado interno del tracker.

        Útil para comenzar un nuevo ciclo de tracking sin arrastrar
        tracks huérfanos de sesiones anteriores.
        """
        self._tracker = DeepSort(
            max_age=self._max_age,
            n_init=self._n_init,
            max_cosine_distance=self._max_cosine_distance,
        )
        logger.info("DeepSortTracker reiniciado.")
