"""
Recolector pasivo de telemetría — Quillinchu AI.

Almacena los datos de rendimiento en memoria RAM (listas nativas
de Python) durante la ejecución del lazo de vuelo. Toda operación
de I/O se difiere al momento explícito de exportación mediante
``export_to_csv()``, garantizando **cero micro-bloqueos** en el
pipeline de control en tiempo real.

Diseño:
    - Cada iteración se registra como un diccionario ligero con
      ``log_iteration()``.
    - El volcado a disco se realiza mediante el módulo ``csv`` de
      la biblioteca estándar (prohibido ``pandas`` en el lazo de
      vuelo — ver ``plan.md`` §Decisiones).
    - El nombre del archivo CSV se genera dinámicamente inyectando
      la fecha actual y las ganancias PID para trazabilidad
      experimental (ver ``spec.md`` §Criterios de aceptación).

References:
    - spec/features/004 - metricas cientificas/spec.md
    - spec/features/004 - metricas cientificas/plan.md §1-§2.
    - tech-stack.md §Convenciones: Type Hints obligatorios.
"""

from __future__ import annotations

import csv
import logging
import os
from datetime import date
from typing import Any, Dict, List

from src.control.guidance_law import GuidanceParams

logger = logging.getLogger(__name__)

# Columnas del CSV de telemetría, en orden estricto.
_CSV_COLUMNS: list[str] = [
    "frame",
    "dt",
    "latency_ms",
    "error_x",
    "error_y",
    "vel_forward",
    "vel_yaw",
]


class MetricsLogger:
    """Recolector pasivo de telemetría en memoria RAM.

    Diseñado para acoplarse al lazo de consumo principal sin
    generar operaciones de I/O durante el vuelo. Los datos se
    acumulan en una lista de diccionarios nativos y se escriben
    a disco únicamente cuando se invoca ``export_to_csv()``.

    Attributes:
        _records: Buffer en memoria con los registros de cada
            iteración del lazo de control.
        _frame_count: Contador monótono de frames procesados.

    Example:
        >>> metrics = MetricsLogger()
        >>> metrics.log_iteration(dt=0.033, error_x=12.5,
        ...     error_y=-8.0, vel_forward=0.4, vel_yaw=3.2)
        >>> metrics.export_to_csv(params=GuidanceParams())
    """

    def __init__(self) -> None:
        self._records: List[Dict[str, Any]] = []
        self._frame_count: int = 0

    # ------------------------------------------------------------------
    # Registro de iteraciones (operación en RAM pura)
    # ------------------------------------------------------------------

    def log_iteration(
        self,
        dt: float,
        error_x: float,
        error_y: float,
        vel_forward: float,
        vel_yaw: float,
    ) -> None:
        """Registra los datos de una iteración del lazo de control.

        Esta operación es O(1) amortizada y no realiza ninguna
        operación de I/O. Los datos se almacenan como un diccionario
        nativo en la lista interna ``_records``.

        Args:
            dt: Diferencial de tiempo desde la iteración anterior [s].
                Utilizado para calcular latencia y frecuencia (Hz).
            error_x: Error de posición horizontal en píxeles (eₓ).
                Positivo indica objetivo a la derecha del centro.
            error_y: Error de posición vertical en píxeles (eᵧ).
                Positivo indica objetivo debajo del centro.
            vel_forward: Velocidad lineal longitudinal comandada [m/s].
            vel_yaw: Velocidad angular de guiñada comandada [°/s].
        """
        self._frame_count += 1
        latency_ms: float = dt * 1000.0

        record: Dict[str, Any] = {
            "frame": self._frame_count,
            "dt": round(dt, 6),
            "latency_ms": round(latency_ms, 3),
            "error_x": round(error_x, 4),
            "error_y": round(error_y, 4),
            "vel_forward": round(vel_forward, 6),
            "vel_yaw": round(vel_yaw, 6),
        }
        self._records.append(record)

    # ------------------------------------------------------------------
    # Exportación a CSV (única operación de I/O)
    # ------------------------------------------------------------------

    def export_to_csv(self, params: GuidanceParams) -> str:
        """Vuelca los datos acumulados a un archivo CSV en ``logs/``.

        El nombre del archivo se genera dinámicamente con la fecha
        actual y las ganancias Kp/Kd del controlador yaw para
        asegurar la trazabilidad experimental::

            logs/exp_YYYY-MM-DD_Kp{kp_yaw}_Kd{kd_yaw}.csv

        Si el archivo ya existe, **no se sobrescribe**: se añade un
        sufijo numérico incremental (``_2``, ``_3``, …) para proteger
        métricas antiguas (ver ``spec.md`` §Caso límite).

        Args:
            params: Parámetros de guiado del experimento. Se utilizan
                ``kp_yaw`` y ``kd_yaw`` para la nomenclatura.

        Returns:
            Ruta absoluta del archivo CSV generado.

        Raises:
            RuntimeError: Si no hay registros acumulados para exportar.
        """
        if not self._records:
            raise RuntimeError(
                "No hay registros acumulados para exportar. "
                "Invoque log_iteration() al menos una vez."
            )

        logs_dir: str = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)

        filename: str = build_csv_filename(params)
        filepath: str = os.path.join(logs_dir, filename)

        # Protección contra sobrescritura de experimentos previos.
        filepath = _unique_filepath(filepath)

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(self._records)

        logger.info(
            "Telemetría exportada: %s (%d registros).",
            filepath,
            len(self._records),
        )
        return filepath

    # ------------------------------------------------------------------
    # Propiedades de solo lectura
    # ------------------------------------------------------------------

    @property
    def records(self) -> List[Dict[str, Any]]:
        """Devuelve una copia de los registros acumulados."""
        return list(self._records)

    @property
    def frame_count(self) -> int:
        """Número total de frames registrados."""
        return self._frame_count


# ======================================================================
# Funciones auxiliares a nivel de módulo
# ======================================================================


def build_csv_filename(params: GuidanceParams) -> str:
    """Construye el nombre del archivo CSV de telemetría.

    Formato::

        exp_YYYY-MM-DD_Kp{kp_yaw}_Kd{kd_yaw}.csv

    Args:
        params: Parámetros de guiado con las ganancias PID.

    Returns:
        Nombre de archivo (sin directorio).
    """
    today: str = date.today().isoformat()
    return f"exp_{today}_Kp{params.kp_yaw}_Kd{params.kd_yaw}.csv"


def _unique_filepath(filepath: str) -> str:
    """Genera una ruta única añadiendo un sufijo numérico si ya existe.

    Evita la sobrescritura accidental de experimentos anteriores.

    Args:
        filepath: Ruta candidata del archivo.

    Returns:
        ``filepath`` si no existe, o una variante con sufijo
        ``_N`` antes de la extensión.
    """
    if not os.path.exists(filepath):
        return filepath

    base, ext = os.path.splitext(filepath)
    counter: int = 2
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"
