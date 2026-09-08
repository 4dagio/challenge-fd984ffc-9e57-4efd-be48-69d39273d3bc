"""Modelo de dominio del sistema de evaluación.

Entidades puras (sin dependencias de infraestructura) que representan los
artefactos de assessment del Chapter de Arquitectura, la solución evaluada y
el resultado de aplicar los artefactos sobre ella.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Artefactos de assessment
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ScenarioMeasure:
    """Medida de respuesta de un escenario de atributo de calidad (ASR)."""

    metric: str
    unit: str
    target: float
    comparator: str  # "<=", ">=" o "=="


@dataclass(frozen=True)
class Criterion:
    """Criterio individual de evaluación dentro de un artefacto."""

    id: str
    name: str
    description: str
    quality_attributes: tuple[str, ...]
    criticality: str  # alta | media | baja
    theme: str
    recommendation: str
    effort: str  # bajo | medio | alto
    weight: float = 1.0
    kb_refs: tuple[str, ...] = ()
    scenario: Optional[dict[str, Any]] = None
    measure: Optional[ScenarioMeasure] = None
    maturity_levels: Optional[dict[str, str]] = None


@dataclass(frozen=True)
class Artifact:
    """Artefacto de assessment: un instrumento de evaluación con criterios."""

    id: str
    slug: str
    name: str
    kind: str  # rubric | checklist | gate | risk-catalog | conformance | scenarios
    scale: str  # maturity | boolean | tristate | conformance | scenario
    purpose: str
    application: str
    source: str
    original_dimension: str
    weight: float
    criteria: tuple[Criterion, ...]
    is_gate: bool = False

    def criterion(self, criterion_id: str) -> Criterion:
        for c in self.criteria:
            if c.id == criterion_id:
                return c
        raise KeyError(criterion_id)


# --------------------------------------------------------------------------- #
# Solución evaluada
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class EvidenceInput:
    """Evidencia aportada por la solución para un criterio."""

    criterion_id: str
    status: Optional[str] = None  # pass/partial/fail, compliant/at-risk/violated, ...
    level: Optional[int] = None  # para escalas de madurez 0-4
    measured: Optional[float] = None  # para escenarios
    evidence: str = ""
    source: str = ""
    not_applicable: bool = False


@dataclass(frozen=True)
class Solution:
    """Solución empresarial sometida a evaluación."""

    id: str
    name: str
    client: str
    domain: str
    version: str
    description: str
    context: dict[str, Any]
    quality_priorities: tuple[str, ...]
    inputs: dict[str, EvidenceInput]
    local_decisions: tuple[dict[str, str], ...] = ()


# --------------------------------------------------------------------------- #
# Resultados
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CriterionResult:
    criterion: Criterion
    score: Optional[float]  # 0..1, None cuando no aplica
    label: str  # Cumple | Parcial | No cumple | Sin evidencia | No aplica
    evidence: str
    source: str
    detail: str = ""


@dataclass(frozen=True)
class Finding:
    id: str
    criterion_id: str
    artifact_id: str
    artifact_name: str
    title: str
    severity: str  # Crítico | Alto | Medio | Bajo
    theme: str
    quality_attributes: tuple[str, ...]
    evidence: str
    recommendation: str
    effort: str
    kb_refs: tuple[str, ...]
    blocking: bool = False


@dataclass(frozen=True)
class ArtifactResult:
    artifact: Artifact
    results: tuple[CriterionResult, ...]
    score: float  # 0..100
    gate_passed: Optional[bool]
    findings: tuple[Finding, ...]

    @property
    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.results:
            counts[r.label] = counts.get(r.label, 0) + 1
        return counts


@dataclass(frozen=True)
class RoadmapItem:
    theme: str
    horizon: str
    severity: str
    actions: tuple[str, ...]
    criteria: tuple[str, ...]
    effort: str


@dataclass(frozen=True)
class Assessment:
    solution: Solution
    generated_at: str
    artifact_results: tuple[ArtifactResult, ...]
    overall_score: float
    maturity_level: str
    verdict: str
    verdict_reason: str
    findings: tuple[Finding, ...]
    heatmap: dict[str, float]
    roadmap: tuple[RoadmapItem, ...]

    def findings_by_severity(self) -> dict[str, list[Finding]]:
        grouped: dict[str, list[Finding]] = {s: [] for s in SEVERITY_ORDER}
        for f in self.findings:
            grouped.setdefault(f.severity, []).append(f)
        return grouped


SEVERITY_ORDER: tuple[str, ...] = ("Crítico", "Alto", "Medio", "Bajo")
