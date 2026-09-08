"""Reglas de puntuación del dominio.

Funciones puras que traducen la evidencia aportada por una solución a una
puntuación normalizada (0..1), una etiqueta legible y una severidad. Aquí vive
el "cómo se mide"; los artefactos solo declaran "qué se mide".
"""
from __future__ import annotations

from typing import Optional

from .models import Criterion, EvidenceInput, ScenarioMeasure

STATUS_SCORES: dict[str, dict[str, float]] = {
    "boolean": {"pass": 1.0, "partial": 0.5, "fail": 0.0},
    "tristate": {"compliant": 1.0, "at-risk": 0.5, "violated": 0.0},
    "conformance": {
        "aligned": 1.0,
        "justified-deviation": 0.75,
        "partial": 0.5,
        "unjustified-deviation": 0.0,
    },
}

MATURITY_MAX_LEVEL = 4

LABEL_COMPLIANT = "Cumple"
LABEL_PARTIAL = "Parcial"
LABEL_FAILED = "No cumple"
LABEL_MISSING = "Sin evidencia"
LABEL_NA = "No aplica"

MATURITY_LEVELS: tuple[tuple[float, str], ...] = (
    (85.0, "Nivel 5 - Optimizado"),
    (70.0, "Nivel 4 - Medido"),
    (50.0, "Nivel 3 - Definido"),
    (30.0, "Nivel 2 - Gestionado"),
    (0.0, "Nivel 1 - Inicial"),
)

HORIZON_BY_SEVERITY: dict[str, str] = {
    "Crítico": "0-30 días",
    "Alto": "30-90 días",
    "Medio": "90-180 días",
    "Bajo": "Backlog (> 180 días)",
}


class ScoringError(ValueError):
    """La evidencia no es válida para la escala del artefacto."""


def score_status(scale: str, status: Optional[str]) -> float:
    table = STATUS_SCORES.get(scale)
    if table is None:
        raise ScoringError(f"Escala desconocida: {scale}")
    if status not in table:
        raise ScoringError(
            f"Estado '{status}' no válido para la escala '{scale}'. "
            f"Valores permitidos: {sorted(table)}"
        )
    return table[status]


def score_maturity(level: Optional[int]) -> float:
    if level is None or not 0 <= level <= MATURITY_MAX_LEVEL:
        raise ScoringError(
            f"Nivel de madurez '{level}' fuera de rango (0-{MATURITY_MAX_LEVEL})"
        )
    return level / MATURITY_MAX_LEVEL


def scenario_is_met(measure: ScenarioMeasure, measured: float) -> bool:
    if measure.comparator == "<=":
        return measured <= measure.target
    if measure.comparator == ">=":
        return measured >= measure.target
    if measure.comparator == "==":
        return measured == measure.target
    raise ScoringError(f"Comparador desconocido: {measure.comparator}")


def score_scenario(measure: ScenarioMeasure, measured: Optional[float]) -> float:
    """Puntúa un escenario de calidad.

    Si la medida cumple el objetivo, 1.0. Si no lo cumple, se otorga crédito
    parcial proporcional a la distancia al objetivo, con tope de 0.9 para que
    un escenario incumplido nunca puntúe como cumplido.
    """
    if measured is None:
        raise ScoringError("Un escenario requiere el campo 'measured'")
    if scenario_is_met(measure, measured):
        return 1.0
    if measure.comparator == "<=":
        ratio = measure.target / measured if measured else 0.0
    elif measure.comparator == ">=":
        ratio = measured / measure.target if measure.target else 0.0
    else:
        ratio = 0.0
    return max(0.0, min(0.9, ratio))


def score_input(scale: str, criterion: Criterion, evidence: EvidenceInput) -> float:
    if scale == "maturity":
        return score_maturity(evidence.level)
    if scale == "scenario":
        if criterion.measure is None:
            raise ScoringError(f"El criterio {criterion.id} no define 'measure'")
        return score_scenario(criterion.measure, evidence.measured)
    return score_status(scale, evidence.status)


def label_for_score(score: Optional[float]) -> str:
    if score is None:
        return LABEL_NA
    if score >= 1.0:
        return LABEL_COMPLIANT
    if score > 0.0:
        return LABEL_PARTIAL
    return LABEL_FAILED


def severity_for(criticality: str, score: float, missing: bool = False) -> str:
    """Deriva la severidad de un hallazgo a partir de la criticidad del criterio
    y de la puntuación obtenida."""
    if missing:
        return "Alto" if criticality == "alta" else "Medio"
    if score <= 0.0:
        return {"alta": "Crítico", "media": "Alto", "baja": "Medio"}[criticality]
    return {"alta": "Alto", "media": "Medio", "baja": "Bajo"}[criticality]


def maturity_level_for(score_0_100: float) -> str:
    for threshold, name in MATURITY_LEVELS:
        if score_0_100 >= threshold:
            return name
    return MATURITY_LEVELS[-1][1]


def weighted_average(pairs: list[tuple[float, float]]) -> float:
    """Promedio ponderado de (score, weight). Devuelve 0 si no hay pares."""
    total_weight = sum(w for _, w in pairs)
    if total_weight == 0:
        return 0.0
    return sum(s * w for s, w in pairs) / total_weight
