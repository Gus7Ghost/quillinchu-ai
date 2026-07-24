"""
Funciones puras de cálculo de métricas — Quillinchu AI.

Contiene las funciones matemáticas puras (sin dependencias
pesadas) utilizadas tanto por el ``report_generator.py`` como
por las pruebas unitarias. Separado de ``report_generator.py``
para evitar importar ``matplotlib`` en contextos donde no se
necesita (tests, lazo de vuelo).

References:
    - spec/features/004 - metricas cientificas/plan.md §3.
"""

from __future__ import annotations

import csv
import math
import os
from typing import Dict, List, Sequence


def compute_rmse(values: Sequence[float]) -> float:
    """Calcula el Root Mean Square Error (RMSE) de una secuencia.

    Fórmula::

        RMSE = sqrt( (1/n) * Σ vᵢ² )

    Args:
        values: Secuencia de valores numéricos (errores o magnitudes).
            No debe estar vacía.

    Returns:
        El RMSE escalar calculado.

    Raises:
        ValueError: Si la secuencia está vacía.
    """
    n: int = len(values)
    if n == 0:
        raise ValueError(
            "La secuencia de valores está vacía. "
            "No se puede calcular el RMSE."
        )
    sum_sq: float = sum(v * v for v in values)
    return math.sqrt(sum_sq / n)


def load_csv(filepath: str) -> List[Dict[str, float]]:
    """Lee un CSV de telemetría y devuelve los registros como dicts.

    Convierte todas las columnas numéricas a ``float`` para los
    cálculos posteriores. La columna ``frame`` se preserva como
    ``float`` (representación numérica del índice).

    Args:
        filepath: Ruta absoluta o relativa al archivo CSV.

    Returns:
        Lista de diccionarios con las columnas del CSV.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si el CSV no contiene registros.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Archivo CSV no encontrado: {filepath}")

    records: List[Dict[str, float]] = []
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed: Dict[str, float] = {
                key: float(value) for key, value in row.items()
            }
            records.append(parsed)

    if not records:
        raise ValueError(f"El archivo CSV está vacío: {filepath}")

    return records


def compute_metrics(
    records: List[Dict[str, float]],
) -> Dict[str, float]:
    """Calcula todas las métricas científicas a partir de los registros.

    Métricas calculadas:
        - ``rmse_pos_x``: RMSE del error de posición en X.
        - ``rmse_pos_y``: RMSE del error de posición en Y.
        - ``rmse_vel_forward``: RMSE de velocidad forward.
        - ``rmse_vel_yaw``: RMSE de velocidad yaw.
        - ``avg_hz``: Frecuencia promedio del lazo (1/dt).
        - ``avg_latency_ms``: Latencia promedio en milisegundos.
        - ``n_frames``: Número total de frames.

    Args:
        records: Lista de registros parseados del CSV.

    Returns:
        Diccionario con todas las métricas calculadas.
    """
    error_x: list[float] = [r["error_x"] for r in records]
    error_y: list[float] = [r["error_y"] for r in records]
    vel_fwd: list[float] = [r["vel_forward"] for r in records]
    vel_yaw: list[float] = [r["vel_yaw"] for r in records]
    latencies: list[float] = [r["latency_ms"] for r in records]

    # Frecuencia: solo dt > 0 (el primer frame suele tener dt=0).
    dt_valid: list[float] = [r["dt"] for r in records if r["dt"] > 0.0]
    avg_hz: float = 0.0
    if dt_valid:
        avg_hz = 1.0 / (sum(dt_valid) / len(dt_valid))

    avg_latency: float = sum(latencies) / len(latencies)

    return {
        "rmse_pos_x": compute_rmse(error_x),
        "rmse_pos_y": compute_rmse(error_y),
        "rmse_vel_forward": compute_rmse(vel_fwd),
        "rmse_vel_yaw": compute_rmse(vel_yaw),
        "avg_hz": round(avg_hz, 2),
        "avg_latency_ms": round(avg_latency, 3),
        "n_frames": float(len(records)),
    }
