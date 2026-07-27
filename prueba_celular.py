"""
Bench Test con Celular — Quillinchu AI.

Ejecuta el pipeline completo de visión + control + seguridad usando
la cámara de un celular (IP Webcam) como fuente de video y la laptop
como procesador. Genera CSV de telemetría y reportes científicos
(gráficos PNG + tabla Markdown) para el informe académico.

Uso::

    python prueba_celular.py --ip 192.168.0.77
    python prueba_celular.py --ip 192.168.0.77 --conf 0.4 --auto-report
    python prueba_celular.py --ip 192.168.0.77 --no-display

References:
    - agents.md: Stack y convenciones del proyecto.
    - src/metrics/logger.py: MetricsLogger (recolector pasivo en RAM).
    - src/metrics/report_generator.py: Generador de reportes offline.
"""

from __future__ import annotations

import argparse
import collections
import logging
import sys
import threading
import time
from typing import Deque, List, Optional

import cv2
import numpy as np

from src.control.guidance_law import GuidanceLaw, GuidanceParams
from src.metrics.logger import MetricsLogger
from src.safety.filter import SafetyFilter, SafetyParams
from src.vision import Detection, TargetState
from src.vision.detector import HeadDetector
from src.vision.tracker import DeepSortTracker

logger = logging.getLogger(__name__)

# ======================================================================
# Constantes de configuración
# ======================================================================

_DEFAULT_IP: str = "192.168.0.77"
_DEFAULT_PORT: int = 8080
_DEFAULT_CONFIDENCE: float = 0.65
_DEFAULT_IOU: float = 0.45
_DEFAULT_IMGSZ: int = 480
_DISPLAY_SIZE: tuple[int, int] = (854, 480)
_FPS_WINDOW: int = 30  # Ventana para media móvil del FPS
_MAX_RECONNECT_ATTEMPTS: int = 5
_RECONNECT_DELAY_S: float = 0.5
_MAX_CONSECUTIVE_FAILURES: int = 15  # Frames fallidos antes de reintentar conexión

# Colores BGR para el HUD
_COLOR_GREEN: tuple[int, int, int] = (0, 255, 0)
_COLOR_CYAN: tuple[int, int, int] = (255, 255, 0)
_COLOR_YELLOW: tuple[int, int, int] = (0, 255, 255)
_COLOR_RED: tuple[int, int, int] = (0, 0, 255)
_COLOR_WHITE: tuple[int, int, int] = (255, 255, 255)
_COLOR_HUD_BG: tuple[int, int, int] = (30, 30, 30)


# ======================================================================
# Frame Grabber (hilo dedicado anti-delay)
# ======================================================================


class FrameGrabber:
    """Lector de frames en hilo dedicado para eliminar buffer delay.

    OpenCV acumula frames en un buffer interno cuando el procesamiento
    (YOLO + Deep SORT) es más lento que la tasa del stream. Cada
    ``cap.read()`` devuelve el frame más viejo del buffer, generando
    un delay creciente e irrecuperable.

    Esta clase ejecuta ``cap.read()`` continuamente en un hilo
    separado, descartando todos los frames intermedios y conservando
    únicamente el **más reciente**. El loop principal siempre obtiene
    el frame actual, no uno atrasado.

    Attributes:
        _cap: VideoCapture de OpenCV.
        _lock: Lock para acceso thread-safe al frame.
        _frame: Último frame capturado (o None).
        _ret: Estado del último read.
        _running: Flag de control del hilo.
        _thread: Hilo de captura en segundo plano.
    """

    def __init__(self, cap: cv2.VideoCapture) -> None:
        self._cap: cv2.VideoCapture = cap
        self._lock: threading.Lock = threading.Lock()
        self._ret: bool = False
        self._frame: Optional[np.ndarray] = None
        self._running: bool = True
        self._consecutive_failures: int = 0

        # Leer el primer frame antes de arrancar el hilo
        self._ret, self._frame = self._cap.read()

        self._thread: threading.Thread = threading.Thread(
            target=self._capture_loop, daemon=True,
        )
        self._thread.start()
        logger.info("FrameGrabber iniciado (hilo anti-delay activo).")

    def _capture_loop(self) -> None:
        """Loop de captura que corre en un hilo daemon.

        Lee frames continuamente y almacena solo el más reciente.
        Los frames intermedios se descartan automáticamente por
        sobreescritura, eliminando la acumulación del buffer.
        """
        while self._running:
            ret, frame = self._cap.read()
            with self._lock:
                self._ret = ret
                self._frame = frame
                if ret:
                    self._consecutive_failures = 0
                else:
                    self._consecutive_failures += 1

    def read(self) -> tuple[bool, Optional[np.ndarray]]:
        """Devuelve el frame más reciente (thread-safe).

        Returns:
            Tupla ``(ret, frame)`` con el frame más reciente.
            ``frame`` puede ser ``None`` si la captura falló.
        """
        with self._lock:
            if self._frame is not None:
                return self._ret, self._frame.copy()
            return self._ret, None

    @property
    def consecutive_failures(self) -> int:
        """Número de lecturas fallidas consecutivas."""
        with self._lock:
            return self._consecutive_failures

    def release(self) -> None:
        """Detiene el hilo de captura y libera la cámara."""
        self._running = False
        self._thread.join(timeout=2.0)
        self._cap.release()
        logger.info("FrameGrabber detenido y cámara liberada.")

    @property
    def cap(self) -> cv2.VideoCapture:
        """Acceso al VideoCapture subyacente (solo lectura)."""
        return self._cap


# ======================================================================
# Funciones auxiliares
# ======================================================================


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parsea los argumentos de línea de comandos.

    Args:
        argv: Argumentos CLI. Si es ``None``, usa ``sys.argv[1:]``.

    Returns:
        Namespace con los argumentos parseados.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Quillinchu AI — Bench Test con Celular. "
            "Ejecuta el pipeline completo usando IP Webcam como fuente de video."
        ),
    )
    parser.add_argument(
        "--ip",
        type=str,
        default=_DEFAULT_IP,
        help=f"IP del celular con IP Webcam (default: {_DEFAULT_IP}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_DEFAULT_PORT,
        help=f"Puerto de IP Webcam (default: {_DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=_DEFAULT_CONFIDENCE,
        help=f"Umbral de confianza YOLO (default: {_DEFAULT_CONFIDENCE}).",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=_DEFAULT_IOU,
        help=(
            f"Umbral IoU para NMS — valores más bajos fusionan más "
            f"cajas solapadas (default: {_DEFAULT_IOU})."
        ),
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=_DEFAULT_IMGSZ,
        help=(
            f"Tamaño de entrada YOLO en px — menor = más rápido "
            f"en CPU (default: {_DEFAULT_IMGSZ})."
        ),
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Modo headless: no muestra ventana de video (útil para benchmarks).",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Desactiva la generación automática de gráficos y tabla al finalizar.",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=8,
        help=(
            "Frames sin detección antes de eliminar un track de Deep SORT "
            "(default: 8, calibrado para ~2 FPS en CPU. "
            "A 30 FPS usar 30)."
        ),
    )
    return parser.parse_args(argv)


def _connect_camera(url: str, max_attempts: int = _MAX_RECONNECT_ATTEMPTS) -> FrameGrabber:
    """Conecta a la cámara IP y retorna un FrameGrabber con hilo anti-delay.

    Args:
        url: URL del stream de video.
        max_attempts: Número máximo de intentos de conexión.

    Returns:
        ``FrameGrabber`` con hilo de captura activo.

    Raises:
        ConnectionError: Si se agotan los reintentos.
    """
    for attempt in range(1, max_attempts + 1):
        logger.info("Intento de conexión %d/%d → %s", attempt, max_attempts, url)
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            logger.info("✅ Conexión establecida.")
            # Reducir buffer interno de OpenCV al mínimo posible
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return FrameGrabber(cap)

        logger.warning(
            "❌ Intento %d/%d fallido. Reintentando en %.1f s...",
            attempt, max_attempts, _RECONNECT_DELAY_S,
        )
        cap.release()
        time.sleep(_RECONNECT_DELAY_S)

    raise ConnectionError(
        f"No se pudo conectar a {url} después de {max_attempts} intentos. "
        "Verifica que IP Webcam esté activo y el celular en la misma red WiFi."
    )


def _draw_hud(
    frame: np.ndarray,
    fps: float,
    latency_ms: float,
    n_targets: int,
    elapsed_s: float,
    frame_count: int,
) -> None:
    """Dibuja el overlay HUD con estadísticas de rendimiento.

    Args:
        frame: Frame BGR sobre el cual dibujar (se modifica in-place).
        fps: FPS actual (media móvil).
        latency_ms: Latencia del frame actual en milisegundos.
        n_targets: Número de targets activos rastreados.
        elapsed_s: Tiempo total transcurrido desde el inicio.
        frame_count: Número total de frames procesados.
    """
    h, w = frame.shape[:2]

    # Fondo semi-transparente para el panel HUD
    overlay = frame.copy()
    panel_h = 130
    cv2.rectangle(overlay, (0, 0), (280, panel_h), _COLOR_HUD_BG, -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Título
    cv2.putText(
        frame, "QUILLINCHU AI", (10, 22),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, _COLOR_CYAN, 1, cv2.LINE_AA,
    )

    # FPS con color según rendimiento
    fps_color = _COLOR_GREEN if fps >= 25.0 else (_COLOR_YELLOW if fps >= 15.0 else _COLOR_RED)
    cv2.putText(
        frame, f"FPS: {fps:.1f}", (10, 48),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, fps_color, 1, cv2.LINE_AA,
    )

    # Latencia
    lat_color = _COLOR_GREEN if latency_ms < 50 else (_COLOR_YELLOW if latency_ms < 100 else _COLOR_RED)
    cv2.putText(
        frame, f"Latencia: {latency_ms:.1f} ms", (10, 70),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, lat_color, 1, cv2.LINE_AA,
    )

    # Targets activos
    target_color = _COLOR_GREEN if n_targets > 0 else _COLOR_YELLOW
    cv2.putText(
        frame, f"Targets: {n_targets}", (10, 92),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, target_color, 1, cv2.LINE_AA,
    )

    # Tiempo y frames
    mins, secs = divmod(int(elapsed_s), 60)
    cv2.putText(
        frame, f"Tiempo: {mins:02d}:{secs:02d}  |  #{frame_count}", (10, 114),
        cv2.FONT_HERSHEY_SIMPLEX, 0.45, _COLOR_WHITE, 1, cv2.LINE_AA,
    )


def _draw_targets(frame: np.ndarray, targets: List[TargetState]) -> None:
    """Dibuja bounding boxes e IDs para todos los targets rastreados.

    Args:
        frame: Frame BGR (se modifica in-place).
        targets: Lista de ``TargetState`` del frame actual.
    """
    for target in targets:
        x1, y1, x2, y2 = map(int, target.bbox)
        cv2.rectangle(frame, (x1, y1), (x2, y2), _COLOR_GREEN, 2)
        label = f"ID:{target.track_id} ({target.confidence:.0%})"
        # Fondo del label
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), _COLOR_GREEN, -1)
        cv2.putText(
            frame, label, (x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA,
        )


def _generate_report(csv_path: str) -> None:
    """Genera gráficos PNG y tabla Markdown a partir del CSV exportado.

    Importa ``report_generator`` de forma diferida para evitar cargar
    ``matplotlib`` durante el pipeline de video.

    Args:
        csv_path: Ruta al archivo CSV de telemetría.
    """
    import os

    from src.metrics.calculations import compute_metrics, load_csv
    from src.metrics.report_generator import generate_plots, print_markdown_table

    print("\n" + "=" * 60)
    print("📊 GENERANDO REPORTE CIENTÍFICO")
    print("=" * 60)

    records = load_csv(csv_path)
    print(f"   → {len(records)} registros cargados del CSV.")

    metrics = compute_metrics(records)

    output_dir = os.path.dirname(os.path.abspath(csv_path))
    csv_basename = os.path.splitext(os.path.basename(csv_path))[0]

    error_png, latency_png = generate_plots(records, output_dir, csv_basename)
    print(f"\n📈 Gráficos generados:")
    print(f"   → {error_png}")
    print(f"   → {latency_png}")

    print("\n📋 Tabla de Resultados:\n")
    print_markdown_table(metrics, csv_basename)
    print()


# ======================================================================
# Pipeline principal
# ======================================================================


def main(argv: list[str] | None = None) -> None:
    """Punto de entrada del bench test con celular.

    Ejecuta el pipeline completo: Detección → Tracking → Control PID →
    Filtro de Seguridad → Registro de Métricas → Exportación CSV.

    Args:
        argv: Argumentos CLI. Si es ``None``, usa ``sys.argv[1:]``.
    """
    # ------------------------------------------------------------------
    # 0. Configuración inicial
    # ------------------------------------------------------------------
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    args = _parse_args(argv)
    cam_url: str = f"http://{args.ip}:{args.port}/video"

    print("=" * 60)
    print("  QUILLINCHU AI — Bench Test con Celular")
    print("=" * 60)
    print(f"  📱 Celular: {args.ip}:{args.port}")
    print(f"  🎯 Confianza YOLO: {args.conf}")
    print(f"  🔲 NMS IoU: {args.iou}")
    print(f"  📐 Tamaño entrada: {args.imgsz}px")
    print(f"  🔄 Deep SORT max_age: {args.max_age} frames")
    print(f"  🖥️  Display: {'OFF (headless)' if args.no_display else 'ON'}")
    print(f"  📊 Reporte: {'OFF' if args.no_report else 'SÍ (automático)'}")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Conexión a la cámara
    # ------------------------------------------------------------------
    print("\n🎥 Conectando a la cámara del celular...")
    try:
        grabber = _connect_camera(cam_url)
    except ConnectionError as e:
        logger.error(str(e))
        print(f"\n❌ {e}")
        sys.exit(1)
    print("🧵 Hilo anti-delay activo (siempre se procesa el frame más reciente).")

    # ------------------------------------------------------------------
    # 2. Carga de módulos de IA
    # ------------------------------------------------------------------
    print("🧠 Cargando módulos de Visión e Inteligencia Artificial...")
    detector = HeadDetector(
        weights_path="HeadDetect.pt",
        confidence=args.conf,
        iou_threshold=args.iou,
        imgsz=args.imgsz,
        device="cpu",
    )
    tracker = DeepSortTracker(max_age=args.max_age, n_init=2)

    guidance_params = GuidanceParams()
    guidance = GuidanceLaw(params=guidance_params)
    safety = SafetyFilter(params=SafetyParams())
    metrics = MetricsLogger()

    print("✅ Pipeline inicializado correctamente.")
    if not args.no_display:
        print("⏹️  Presiona 'q' en la ventana de video para finalizar.\n")
    else:
        print("⏹️  Presiona Ctrl+C para finalizar.\n")

    # ------------------------------------------------------------------
    # 3. Variables del lazo principal
    # ------------------------------------------------------------------
    start_time: float = time.time()
    last_frame_time: float = start_time
    frame_count: int = 0
    fps_buffer: Deque[float] = collections.deque(maxlen=_FPS_WINDOW)

    csv_path: Optional[str] = None

    # ------------------------------------------------------------------
    # 4. Lazo principal (con manejo limpio de Ctrl+C)
    # ------------------------------------------------------------------
    try:
        while True:
            ret, frame = grabber.read()

            # Manejo de frames fallidos con resiliencia
            if not ret or frame is None:
                if grabber.consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        "⚠️ %d frames consecutivos fallidos. "
                        "Reintentando conexión...",
                        grabber.consecutive_failures,
                    )
                    grabber.release()
                    try:
                        grabber = _connect_camera(cam_url)
                        continue
                    except ConnectionError:
                        logger.error("Reconexión fallida. Finalizando captura.")
                        break
                continue

            frame_count += 1
            current_time: float = time.time()
            dt: float = current_time - last_frame_time
            last_frame_time = current_time
            latency_ms: float = dt * 1000.0

            # Acumular dt para media móvil del FPS
            if dt > 0:
                fps_buffer.append(dt)
            avg_fps: float = (
                1.0 / (sum(fps_buffer) / len(fps_buffer))
                if fps_buffer else 0.0
            )

            # ----------------------------------------------------------
            # 4a. Inferencia con HeadDetector → list[Detection]
            # ----------------------------------------------------------
            detections: list[Detection] = detector.detect(frame)

            # ----------------------------------------------------------
            # 4b. Tracking con DeepSortTracker → list[TargetState]
            # ----------------------------------------------------------
            targets: list[TargetState] = tracker.update(detections, frame)

            # ----------------------------------------------------------
            # 4c. Lazo de Control PID + Filtro de Seguridad
            # ----------------------------------------------------------
            raw_cmd = guidance.compute(targets)

            error_x: float = 0.0
            error_y: float = 0.0

            if targets:
                selected: TargetState = max(targets, key=lambda t: t.confidence)
                cx = (selected.bbox[0] + selected.bbox[2]) / 2.0
                cy = (selected.bbox[1] + selected.bbox[3]) / 2.0
                error_x = cx - (guidance_params.image_width / 2.0)
                error_y = cy - (guidance_params.image_height / 2.0)

            vel_forward: float = 0.0
            vel_yaw: float = 0.0

            if raw_cmd is not None:
                safe_cmd = safety.apply(
                    raw_cmd,
                    last_target_time=current_time,
                    current_time=current_time,
                )
                vel_forward = safe_cmd.forward_m_s
                vel_yaw = safe_cmd.yawspeed_deg_s

            # ----------------------------------------------------------
            # 4d. Registrar métricas SIEMPRE (con o sin detección)
            # ----------------------------------------------------------
            metrics.log_iteration(
                dt=dt,
                error_x=error_x,
                error_y=error_y,
                vel_forward=vel_forward,
                vel_yaw=vel_yaw,
            )

            # ----------------------------------------------------------
            # 4e. Visualización (si no es modo headless)
            # ----------------------------------------------------------
            if not args.no_display:
                _draw_targets(frame, targets)

                elapsed_s: float = current_time - start_time
                _draw_hud(
                    frame,
                    fps=avg_fps,
                    latency_ms=latency_ms,
                    n_targets=len(targets),
                    elapsed_s=elapsed_s,
                    frame_count=frame_count,
                )

                frame_resized = cv2.resize(frame, _DISPLAY_SIZE)
                cv2.imshow("Quillinchu AI - Bench Test con Celular", frame_resized)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    logger.info("Tecla 'q' presionada. Finalizando captura.")
                    break

    except KeyboardInterrupt:
        logger.info("Ctrl+C recibido. Finalizando captura...")
        print("\n\n⚠️ Interrupción por teclado. Exportando métricas...")

    finally:
        # ----------------------------------------------------------
        # 5. Limpieza y exportación (SIEMPRE se ejecuta)
        # ----------------------------------------------------------
        grabber.release()
        cv2.destroyAllWindows()

        total_elapsed: float = time.time() - start_time
        mins, secs = divmod(int(total_elapsed), 60)
        avg_fps_final: float = frame_count / total_elapsed if total_elapsed > 0 else 0.0

        print("\n" + "=" * 60)
        print("  RESUMEN DE LA SESIÓN")
        print("=" * 60)
        print(f"  ⏱️  Duración total: {mins:02d}:{secs:02d}")
        print(f"  🎞️  Frames procesados: {frame_count}")
        print(f"  📈 FPS promedio: {avg_fps_final:.1f}")
        print(f"  📝 Iteraciones registradas: {metrics.frame_count}")
        print("=" * 60)

        # Exportar CSV solo si hay datos registrados
        if metrics.frame_count > 0:
            try:
                csv_path = metrics.export_to_csv(params=guidance_params)
                print(f"\n✅ CSV exportado: {csv_path}")
                logger.info(
                    "Sesión finalizada — %d frames, %.1f FPS promedio, CSV: %s",
                    frame_count, avg_fps_final, csv_path,
                )
            except RuntimeError as e:
                logger.error("Error al exportar CSV: %s", e)
                print(f"\n❌ Error al exportar CSV: {e}")
        else:
            print("\n⚠️ No se registraron iteraciones. No se genera CSV.")
            logger.warning("Sesión vacía: 0 iteraciones registradas.")

    # ------------------------------------------------------------------
    # 6. Generación automática de reporte (por defecto)
    # ------------------------------------------------------------------
    if csv_path is not None and not args.no_report:
        try:
            _generate_report(csv_path)
        except Exception as e:
            logger.error("Error al generar reporte: %s", e)
            print(f"\n❌ Error al generar reporte: {e}")
    elif csv_path is not None:
        print(
            f"\n💡 Reporte desactivado. Para generarlo manualmente:\n"
            f"   python -m src.metrics.report_generator {csv_path}"
        )


if __name__ == "__main__":
    main()