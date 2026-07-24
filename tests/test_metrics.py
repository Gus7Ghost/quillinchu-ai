"""
Suite de pruebas unitarias del módulo de métricas — Quillinchu AI.

Valida la exactitud matemática del RMSE, la generación dinámica
de nombres de archivo CSV, el comportamiento del logger en memoria
y las funciones del generador de reportes.

References:
    - spec/features/004 - metricas cientificas/spec.md §Requisito
      de calidad: «Las fórmulas estadísticas aplicadas (RMSE absoluto)
      están respaldadas por pruebas unitarias».
    - spec/features/004 - metricas cientificas/plan.md §4.
    - tech-stack.md: «pytest y unittest para verificar de forma
      robusta la suite de visión, control y seguridad».
"""

from __future__ import annotations

import csv
import math
import os
import tempfile
from datetime import date
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from src.control.guidance_law import GuidanceParams
from src.metrics.logger import MetricsLogger, build_csv_filename
from src.metrics.calculations import (
    compute_metrics,
    compute_rmse,
    load_csv,
)

# ===========================================================================
# TestComputeRMSE — Validación matemática del RMSE
# ===========================================================================


class TestComputeRMSE:
    """Pruebas de la función pura ``compute_rmse``.

    Valida la fórmula: RMSE = sqrt( (1/n) * Σ vᵢ² ).
    """

    def test_single_value(self) -> None:
        """RMSE de un solo valor es su valor absoluto."""
        assert compute_rmse([5.0]) == pytest.approx(5.0)

    def test_single_negative_value(self) -> None:
        """RMSE de un valor negativo es su valor absoluto."""
        assert compute_rmse([-3.0]) == pytest.approx(3.0)

    def test_known_values(self) -> None:
        """Cálculo manual verificado: RMSE([1, 2, 3]) = sqrt(14/3)."""
        values: list[float] = [1.0, 2.0, 3.0]
        expected: float = math.sqrt((1 + 4 + 9) / 3)
        assert compute_rmse(values) == pytest.approx(expected)

    def test_all_zeros(self) -> None:
        """RMSE de una secuencia de ceros es 0.0."""
        assert compute_rmse([0.0, 0.0, 0.0]) == pytest.approx(0.0)

    def test_symmetric_errors(self) -> None:
        """Errores simétricos positivos y negativos producen el
        mismo RMSE que sus valores absolutos.
        """
        positive: list[float] = [3.0, 4.0, 5.0]
        negative: list[float] = [-3.0, -4.0, -5.0]
        assert compute_rmse(positive) == pytest.approx(
            compute_rmse(negative)
        )

    def test_mixed_sign_errors(self) -> None:
        """RMSE con signos mixtos: sqrt((9+16+25)/3) = sqrt(50/3)."""
        values: list[float] = [3.0, -4.0, 5.0]
        expected: float = math.sqrt((9 + 16 + 25) / 3)
        assert compute_rmse(values) == pytest.approx(expected)

    def test_empty_raises_value_error(self) -> None:
        """Una secuencia vacía debe lanzar ``ValueError``."""
        with pytest.raises(ValueError, match="vacía"):
            compute_rmse([])

    def test_large_dataset_precision(self) -> None:
        """Verifica precisión con 10000 valores constantes."""
        n: int = 10000
        constant: float = 7.5
        values: list[float] = [constant] * n
        # RMSE de valores constantes = valor absoluto del constante.
        assert compute_rmse(values) == pytest.approx(constant)


# ===========================================================================
# TestBuildCSVFilename — Nomenclatura dinámica del CSV
# ===========================================================================


class TestBuildCSVFilename:
    """Pruebas de la generación dinámica de nombres de archivo."""

    def test_default_params_format(self) -> None:
        """El nombre incluye la fecha de hoy y los Kp/Kd defaults."""
        params = GuidanceParams()
        filename: str = build_csv_filename(params)
        today: str = date.today().isoformat()

        assert filename.startswith(f"exp_{today}")
        assert f"Kp{params.kp_yaw}" in filename
        assert f"Kd{params.kd_yaw}" in filename
        assert filename.endswith(".csv")

    def test_custom_params_format(self) -> None:
        """El nombre refleja las ganancias personalizadas."""
        params = GuidanceParams(kp_yaw=0.25, kd_yaw=0.05)
        filename: str = build_csv_filename(params)

        assert "Kp0.25" in filename
        assert "Kd0.05" in filename

    def test_date_changes_with_mock(self) -> None:
        """Simula una fecha distinta para verificar inyección."""
        params = GuidanceParams()
        mock_date = date(2026, 1, 15)

        with patch(
            "src.metrics.logger.date"
        ) as mock_date_cls:
            mock_date_cls.today.return_value = mock_date
            mock_date_cls.side_effect = lambda *a, **kw: date(*a, **kw)
            filename: str = build_csv_filename(params)

        assert "2026-01-15" in filename

    def test_filename_has_no_spaces(self) -> None:
        """El nombre de archivo no debe contener espacios."""
        params = GuidanceParams()
        filename: str = build_csv_filename(params)
        assert " " not in filename


# ===========================================================================
# TestMetricsLogger — Recolector pasivo en memoria
# ===========================================================================


class TestMetricsLogger:
    """Pruebas del ``MetricsLogger`` — recolector en RAM."""

    def test_initial_state(self) -> None:
        """Un logger recién creado tiene 0 registros."""
        logger = MetricsLogger()
        assert logger.frame_count == 0
        assert logger.records == []

    def test_log_iteration_increments_frame(self) -> None:
        """Cada ``log_iteration`` incrementa el frame_count."""
        logger = MetricsLogger()
        logger.log_iteration(
            dt=0.033, error_x=10.0, error_y=-5.0,
            vel_forward=0.5, vel_yaw=2.0,
        )
        assert logger.frame_count == 1

        logger.log_iteration(
            dt=0.034, error_x=8.0, error_y=-3.0,
            vel_forward=0.4, vel_yaw=1.5,
        )
        assert logger.frame_count == 2

    def test_log_iteration_stores_record(self) -> None:
        """Los registros almacenados contienen las columnas correctas."""
        logger = MetricsLogger()
        logger.log_iteration(
            dt=0.033, error_x=12.5, error_y=-8.0,
            vel_forward=0.4, vel_yaw=3.2,
        )

        records: List[Dict[str, Any]] = logger.records
        assert len(records) == 1

        record: Dict[str, Any] = records[0]
        assert record["frame"] == 1
        assert record["dt"] == pytest.approx(0.033, abs=1e-5)
        assert record["error_x"] == pytest.approx(12.5, abs=1e-3)
        assert record["error_y"] == pytest.approx(-8.0, abs=1e-3)
        assert record["vel_forward"] == pytest.approx(0.4, abs=1e-5)
        assert record["vel_yaw"] == pytest.approx(3.2, abs=1e-5)

    def test_latency_ms_conversion(self) -> None:
        """``latency_ms`` debe ser ``dt * 1000``."""
        logger = MetricsLogger()
        logger.log_iteration(
            dt=0.05, error_x=0.0, error_y=0.0,
            vel_forward=0.0, vel_yaw=0.0,
        )
        record: Dict[str, Any] = logger.records[0]
        assert record["latency_ms"] == pytest.approx(50.0, abs=0.01)

    def test_log_iteration_no_exception(self) -> None:
        """``log_iteration`` no debe lanzar excepciones con valores
        extremos (cero, negativos, flotantes grandes).
        """
        logger = MetricsLogger()
        # No debe lanzar ninguna excepción.
        logger.log_iteration(
            dt=0.0, error_x=0.0, error_y=0.0,
            vel_forward=0.0, vel_yaw=0.0,
        )
        logger.log_iteration(
            dt=1.0, error_x=-999.0, error_y=999.0,
            vel_forward=-100.0, vel_yaw=100.0,
        )
        logger.log_iteration(
            dt=0.001, error_x=1e-10, error_y=-1e-10,
            vel_forward=1e-8, vel_yaw=1e-8,
        )
        assert logger.frame_count == 3

    def test_records_returns_copy(self) -> None:
        """``records`` debe devolver una copia, no la lista interna."""
        logger = MetricsLogger()
        logger.log_iteration(
            dt=0.033, error_x=1.0, error_y=2.0,
            vel_forward=0.1, vel_yaw=0.2,
        )
        copy_a = logger.records
        copy_b = logger.records
        assert copy_a is not copy_b
        assert copy_a == copy_b

    def test_export_empty_raises_runtime_error(self) -> None:
        """Exportar sin datos debe lanzar ``RuntimeError``."""
        logger = MetricsLogger()
        params = GuidanceParams()
        with pytest.raises(RuntimeError, match="No hay registros"):
            logger.export_to_csv(params)

    def test_export_to_csv_creates_file(self, tmp_path: Any) -> None:
        """``export_to_csv`` crea un archivo CSV en el directorio logs."""
        logger = MetricsLogger()
        logger.log_iteration(
            dt=0.033, error_x=10.0, error_y=-5.0,
            vel_forward=0.5, vel_yaw=2.0,
        )
        logger.log_iteration(
            dt=0.034, error_x=8.0, error_y=-3.0,
            vel_forward=0.4, vel_yaw=1.5,
        )

        params = GuidanceParams(kp_yaw=0.1, kd_yaw=0.01)

        # Ejecutar en tmp_path para no contaminar el proyecto.
        with patch("os.getcwd", return_value=str(tmp_path)):
            filepath: str = logger.export_to_csv(params)

        assert os.path.isfile(filepath)
        assert filepath.endswith(".csv")

        # Verificar contenido.
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows: list[dict[str, str]] = list(reader)

        assert len(rows) == 2
        assert rows[0]["frame"] == "1"
        assert rows[1]["frame"] == "2"

    def test_export_no_overwrite(self, tmp_path: Any) -> None:
        """Exportaciones consecutivas no sobrescriben archivos previos."""
        params = GuidanceParams(kp_yaw=0.1, kd_yaw=0.01)

        # Primera exportación.
        logger_1 = MetricsLogger()
        logger_1.log_iteration(
            dt=0.033, error_x=10.0, error_y=-5.0,
            vel_forward=0.5, vel_yaw=2.0,
        )

        with patch("os.getcwd", return_value=str(tmp_path)):
            path_1: str = logger_1.export_to_csv(params)

        # Segunda exportación con los mismos parámetros.
        logger_2 = MetricsLogger()
        logger_2.log_iteration(
            dt=0.035, error_x=12.0, error_y=-6.0,
            vel_forward=0.6, vel_yaw=2.5,
        )

        with patch("os.getcwd", return_value=str(tmp_path)):
            path_2: str = logger_2.export_to_csv(params)

        # Ambos archivos deben existir con rutas distintas.
        assert os.path.isfile(path_1)
        assert os.path.isfile(path_2)
        assert path_1 != path_2


# ===========================================================================
# TestComputeMetrics — Métricas integradas
# ===========================================================================


class TestComputeMetrics:
    """Pruebas de ``compute_metrics`` con datos sintéticos."""

    @pytest.fixture
    def sample_records(self) -> List[Dict[str, float]]:
        """Genera registros sintéticos para pruebas."""
        return [
            {
                "frame": 1.0,
                "dt": 0.0,
                "latency_ms": 0.0,
                "error_x": 10.0,
                "error_y": -5.0,
                "vel_forward": 0.5,
                "vel_yaw": 2.0,
            },
            {
                "frame": 2.0,
                "dt": 0.033,
                "latency_ms": 33.0,
                "error_x": 8.0,
                "error_y": -3.0,
                "vel_forward": 0.4,
                "vel_yaw": 1.5,
            },
            {
                "frame": 3.0,
                "dt": 0.034,
                "latency_ms": 34.0,
                "error_x": 6.0,
                "error_y": -1.0,
                "vel_forward": 0.3,
                "vel_yaw": 1.0,
            },
        ]

    def test_rmse_pos_x(
        self, sample_records: List[Dict[str, float]]
    ) -> None:
        """RMSE de error_x calculado correctamente."""
        metrics: Dict[str, float] = compute_metrics(sample_records)
        # sqrt((100 + 64 + 36) / 3) = sqrt(200/3)
        expected: float = math.sqrt(200.0 / 3.0)
        assert metrics["rmse_pos_x"] == pytest.approx(expected)

    def test_rmse_pos_y(
        self, sample_records: List[Dict[str, float]]
    ) -> None:
        """RMSE de error_y calculado correctamente."""
        metrics: Dict[str, float] = compute_metrics(sample_records)
        # sqrt((25 + 9 + 1) / 3) = sqrt(35/3)
        expected: float = math.sqrt(35.0 / 3.0)
        assert metrics["rmse_pos_y"] == pytest.approx(expected)

    def test_rmse_vel_forward(
        self, sample_records: List[Dict[str, float]]
    ) -> None:
        """RMSE de vel_forward calculado correctamente."""
        metrics: Dict[str, float] = compute_metrics(sample_records)
        # sqrt((0.25 + 0.16 + 0.09) / 3) = sqrt(0.5/3)
        expected: float = math.sqrt(0.5 / 3.0)
        assert metrics["rmse_vel_forward"] == pytest.approx(expected)

    def test_rmse_vel_yaw(
        self, sample_records: List[Dict[str, float]]
    ) -> None:
        """RMSE de vel_yaw calculado correctamente."""
        metrics: Dict[str, float] = compute_metrics(sample_records)
        # sqrt((4 + 2.25 + 1) / 3) = sqrt(7.25/3)
        expected: float = math.sqrt(7.25 / 3.0)
        assert metrics["rmse_vel_yaw"] == pytest.approx(expected)

    def test_avg_hz_excludes_zero_dt(
        self, sample_records: List[Dict[str, float]]
    ) -> None:
        """El cálculo de Hz promedio excluye frames con dt=0."""
        metrics: Dict[str, float] = compute_metrics(sample_records)
        # Solo dt válidos: [0.033, 0.034]. avg_dt = 0.0335.
        # Hz = 1 / 0.0335 ≈ 29.85
        expected_hz: float = 1.0 / ((0.033 + 0.034) / 2.0)
        assert metrics["avg_hz"] == pytest.approx(expected_hz, abs=0.1)

    def test_n_frames(
        self, sample_records: List[Dict[str, float]]
    ) -> None:
        """El conteo de frames es correcto."""
        metrics: Dict[str, float] = compute_metrics(sample_records)
        assert metrics["n_frames"] == pytest.approx(3.0)


# ===========================================================================
# TestLoadCSV — Lectura del CSV
# ===========================================================================


class TestLoadCSV:
    """Pruebas de la función ``load_csv``."""

    def test_load_valid_csv(self, tmp_path: Any) -> None:
        """Carga correctamente un CSV válido."""
        csv_path: str = str(tmp_path / "test.csv")
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "frame", "dt", "latency_ms",
                    "error_x", "error_y",
                    "vel_forward", "vel_yaw",
                ],
            )
            writer.writeheader()
            writer.writerow({
                "frame": 1, "dt": 0.033, "latency_ms": 33.0,
                "error_x": 10.0, "error_y": -5.0,
                "vel_forward": 0.5, "vel_yaw": 2.0,
            })

        records = load_csv(csv_path)
        assert len(records) == 1
        assert records[0]["error_x"] == pytest.approx(10.0)

    def test_file_not_found(self) -> None:
        """Archivo inexistente lanza ``FileNotFoundError``."""
        with pytest.raises(FileNotFoundError):
            load_csv("inexistente.csv")

    def test_empty_csv_raises_value_error(self, tmp_path: Any) -> None:
        """CSV vacío (solo header) lanza ``ValueError``."""
        csv_path: str = str(tmp_path / "empty.csv")
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "frame", "dt", "latency_ms",
                    "error_x", "error_y",
                    "vel_forward", "vel_yaw",
                ],
            )
            writer.writeheader()

        with pytest.raises(ValueError, match="vacío"):
            load_csv(csv_path)
