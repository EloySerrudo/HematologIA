"""Aggregated queries for the dashboard views.

This repo is read-only: it exposes a single ``get_personal_stats`` function
that returns the four metrics the Personal dashboard cards display, all
filtered by the current operario and limited to *today* in local time.

Date comparisons use SQLite's ``date('now', 'localtime')`` so they match the
operator's local calendar day rather than UTC.
"""
from __future__ import annotations

from src.database.connection import get_connection
from src.database.models import DashboardStats


def get_personal_stats(id_operario: int) -> DashboardStats:
    """Compute today's stats for the given operario.

    Returns:
        DashboardStats with the four metric values. Counts are zero when
        nothing has been done today; ``duracion_promedio_segundos`` is None
        when no analyses have been completed today.
    """
    with get_connection() as conn:
        # --- Imágenes capturadas hoy por este operario ---
        # Una captura "pertenece" al operario que dueña del estudio donde está.
        cap_row = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM capturas c
            JOIN estudios e ON c.id_estudio = e.id_estudio
            WHERE e.id_operario = ?
              AND date(c.fecha_captura) = date('now', 'localtime')
            """,
            (id_operario,),
        ).fetchone()

        # --- Análisis realizados hoy ---
        # Un análisis está "realizado" cuando fecha_analisis no es NULL.
        ana_row = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM estudios
            WHERE id_operario = ?
              AND fecha_analisis IS NOT NULL
              AND date(fecha_analisis) = date('now', 'localtime')
            """,
            (id_operario,),
        ).fetchone()

        # --- Reportes generados hoy ---
        rep_row = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM reportes r
            JOIN estudios e ON r.id_estudio = e.id_estudio
            WHERE e.id_operario = ?
              AND date(r.fecha_generacion) = date('now', 'localtime')
            """,
            (id_operario,),
        ).fetchone()

        # --- Tiempo promedio de análisis hoy (segundos) ---
        # AVG ignora NULLs automáticamente. Si no hay filas, el resultado es NULL.
        dur_row = conn.execute(
            """
            SELECT AVG(duracion_segundos) AS avg_dur
            FROM estudios
            WHERE id_operario = ?
              AND fecha_analisis IS NOT NULL
              AND duracion_segundos IS NOT NULL
              AND date(fecha_analisis) = date('now', 'localtime')
            """,
            (id_operario,),
        ).fetchone()

    return DashboardStats(
        imagenes_capturadas_hoy=int(cap_row["n"] or 0),
        analisis_realizados_hoy=int(ana_row["n"] or 0),
        reportes_generados_hoy=int(rep_row["n"] or 0),
        duracion_promedio_segundos=dur_row["avg_dur"],
    )
