"""
Generador de Reportes Científicos Offline — Quillinchu AI.

Script CLI independiente que procesa los archivos CSV generados
por ``MetricsLogger`` y produce:

    1. **RMSE de Posición** (error_x, error_y en píxeles).
    2. **RMSE de Velocidad** (vel_forward, vel_yaw).
    3. **Frecuencia promedio** (Hz) del lazo de control.
    4. **Gráficos PNG**: "Error vs Frames" y "Latencia vs Frames".
    5. **Tabla Markdown** de resultados en formato académico.

Las funciones puras de cálculo (``compute_rmse``, ``load_csv``,
``compute_metrics``) residen en ``src/metrics/calculations.py``
para evitar que la importación de ``matplotlib`` se propague
al lazo de vuelo o a las pruebas unitarias.

Uso desde línea de comandos::

    python src/metrics/report_generator.py logs/exp_2026-07-23_Kp0.1_Kd0.0.csv

References:
    - spec/features/004 - metricas cientificas/spec.md §Criterios.
    - spec/features/004 - metricas cientificas/plan.md §3.
    - tech-stack.md: «pytest y unittest para verificar la suite».
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List, Sequence

import matplotlib

matplotlib.use("Agg")  # Backend sin GUI para servidores / CI.
import matplotlib.pyplot as plt  # noqa: E402

from src.metrics.calculations import (  # noqa: E402
    compute_metrics,
    compute_rmse,
    load_csv,
)


# ======================================================================
# Generación de gráficos
# ======================================================================


def generate_plots(
    records: List[Dict[str, float]],
    output_dir: str,
    csv_basename: str,
) -> tuple[str, str]:
    """Genera y guarda 2 gráficos PNG de evolución temporal.

    Gráficos generados:
        1. **Error vs Frames**: Evolución de error_x y error_y.
        2. **Latencia vs Frames**: Evolución de latency_ms.

    Args:
        records: Lista de registros parseados del CSV.
        output_dir: Directorio donde se guardarán los PNGs.
        csv_basename: Nombre base del CSV (sin extensión) para
            construir los nombres de los gráficos.

    Returns:
        Tupla con las rutas de los dos archivos PNG generados.
    """
    os.makedirs(output_dir, exist_ok=True)

    frames: list[float] = [r["frame"] for r in records]
    error_x: list[float] = [r["error_x"] for r in records]
    error_y: list[float] = [r["error_y"] for r in records]
    latencies: list[float] = [r["latency_ms"] for r in records]

    # ------------------------------------------------------------------
    # Gráfico 1: Error vs Frames
    # ------------------------------------------------------------------
    fig_error, ax_error = plt.subplots(figsize=(10, 5))
    ax_error.plot(frames, error_x, label="Error X [px]", linewidth=0.8)
    ax_error.plot(frames, error_y, label="Error Y [px]", linewidth=0.8)
    ax_error.set_xlabel("Frame")
    ax_error.set_ylabel("Error [píxeles]")
    ax_error.set_title(f"Error de Posición vs Frames — {csv_basename}")
    ax_error.legend(loc="upper right")
    ax_error.grid(True, alpha=0.3)

    error_path: str = os.path.join(
        output_dir, f"{csv_basename}_error_vs_frames.png"
    )
    fig_error.savefig(error_path, dpi=150, bbox_inches="tight")
    plt.close(fig_error)

    # ------------------------------------------------------------------
    # Gráfico 2: Latencia vs Frames
    # ------------------------------------------------------------------
    fig_lat, ax_lat = plt.subplots(figsize=(10, 5))
    ax_lat.plot(
        frames,
        latencies,
        label="Latencia [ms]",
        linewidth=0.8,
        color="tab:orange",
    )
    ax_lat.set_xlabel("Frame")
    ax_lat.set_ylabel("Latencia [ms]")
    ax_lat.set_title(f"Latencia vs Frames — {csv_basename}")
    ax_lat.legend(loc="upper right")
    ax_lat.grid(True, alpha=0.3)

    latency_path: str = os.path.join(
        output_dir, f"{csv_basename}_latencia_vs_frames.png"
    )
    fig_lat.savefig(latency_path, dpi=150, bbox_inches="tight")
    plt.close(fig_lat)

    return error_path, latency_path


# ======================================================================
# Tabla Markdown de resultados
# ======================================================================


def print_markdown_table(
    metrics: Dict[str, float],
    csv_basename: str,
) -> str:
    """Imprime y devuelve una tabla Markdown de resultados académicos.

    Formato de la tabla adaptado a las directrices del curso::

        | Configuración | Dataset | Métrica principal | Valor | Observaciones |

    Args:
        metrics: Diccionario de métricas calculadas por
            ``compute_metrics()``.
        csv_basename: Nombre del experimento (sin extensión).

    Returns:
        Cadena con la tabla Markdown completa.
    """
    n_frames: int = int(metrics["n_frames"])
    config: str = csv_basename

    rows: list[tuple[str, str, str, str]] = [
        (config, f"{n_frames} frames", "RMSE Pos X [px]",
         f"{metrics['rmse_pos_x']:.4f}"),
        (config, f"{n_frames} frames", "RMSE Pos Y [px]",
         f"{metrics['rmse_pos_y']:.4f}"),
        (config, f"{n_frames} frames", "RMSE Vel Forward [m/s]",
         f"{metrics['rmse_vel_forward']:.6f}"),
        (config, f"{n_frames} frames", "RMSE Vel Yaw [°/s]",
         f"{metrics['rmse_vel_yaw']:.6f}"),
        (config, f"{n_frames} frames", "Hz promedio",
         f"{metrics['avg_hz']:.2f}"),
        (config, f"{n_frames} frames", "Latencia prom. [ms]",
         f"{metrics['avg_latency_ms']:.3f}"),
    ]

    # Observaciones automáticas basadas en umbrales.
    observations: list[str] = []
    for _, _, metric_name, value_str in rows:
        obs: str = _auto_observation(metric_name, float(value_str))
        observations.append(obs)

    # Construcción de la tabla.
    header: str = (
        "| Configuración | Dataset | Métrica principal "
        "| Valor | Observaciones |"
    )
    separator: str = (
        "|:---|:---|:---|---:|:---|"
    )

    lines: list[str] = [header, separator]
    for i, (cfg, ds, metric_name, value_str) in enumerate(rows):
        obs: str = observations[i]
        line: str = f"| {cfg} | {ds} | {metric_name} | {value_str} | {obs} |"
        lines.append(line)

    table: str = "\n".join(lines)
    print(table)
    return table


def _auto_observation(metric_name: str, value: float) -> str:
    """Genera observaciones automáticas basadas en umbrales heurísticos.

    Args:
        metric_name: Nombre de la métrica evaluada.
        value: Valor numérico de la métrica.

    Returns:
        Cadena de texto con la observación, o cadena vacía.
    """
    if "RMSE Pos" in metric_name:
        if value < 20.0:
            return "Excelente precisión"
        if value < 50.0:
            return "Precisión aceptable"
        return "Requiere ajuste"
    if "Hz" in metric_name:
        if value >= 25.0:
            return "Tiempo real"
        if value >= 15.0:
            return "Aceptable"
        return "Por debajo del umbral"
    return ""


# ======================================================================
# Punto de entrada CLI
# ======================================================================


def main(argv: Sequence[str] | None = None) -> None:
    """Punto de entrada principal del generador de reportes.

    Args:
        argv: Argumentos de línea de comandos. Si es ``None``, se
            utiliza ``sys.argv[1:]``.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Generador de reportes científicos — Quillinchu AI. "
            "Lee un CSV de telemetría y calcula RMSE, Hz y gráficos."
        ),
    )
    parser.add_argument(
        "csv_file",
        type=str,
        help="Ruta al archivo CSV generado por MetricsLogger.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=(
            "Directorio de salida para los gráficos PNG. "
            "Por defecto, el mismo directorio del CSV."
        ),
    )

    args = parser.parse_args(argv)
    csv_path: str = args.csv_file

    # Directorio de salida: por defecto, junto al CSV.
    output_dir: str = args.output_dir or os.path.dirname(
        os.path.abspath(csv_path)
    )

    # 1. Cargar datos.
    print(f"\n📂 Cargando: {csv_path}")
    records: List[Dict[str, float]] = load_csv(csv_path)
    print(f"   → {len(records)} registros leídos.")

    # 2. Calcular métricas.
    metrics: Dict[str, float] = compute_metrics(records)

    # 3. Generar gráficos.
    csv_basename: str = os.path.splitext(os.path.basename(csv_path))[0]
    error_png, latency_png = generate_plots(
        records, output_dir, csv_basename
    )
    print(f"\n📊 Gráficos generados:")
    print(f"   → {error_png}")
    print(f"   → {latency_png}")

    # 4. Imprimir tabla de resultados.
    print("\n📋 Tabla de Resultados:\n")
    print_markdown_table(metrics, csv_basename)
    print()


if __name__ == "__main__":
    main()
