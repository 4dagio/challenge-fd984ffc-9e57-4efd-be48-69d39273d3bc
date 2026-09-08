"""Caso de uso: aplicar los artefactos de assessment a una solución."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ..domain import scoring
from ..domain.models import (
    SEVERITY_ORDER,
    Artifact,
    ArtifactResult,
    Assessment,
    Criterion,
    CriterionResult,
    Finding,
    RoadmapItem,
    Solution,
)

SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}
EFFORT_RANK = {"bajo": 0, "medio": 1, "alto": 2}


class EvaluateSolution:
    """Orquesta la aplicación de todos los artefactos sobre una solución."""

    def __init__(self, artifacts: list[Artifact]):
        if not artifacts:
            raise ValueError("Se requiere al menos un artefacto de assessment")
        total_weight = round(sum(a.weight for a in artifacts), 6)
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(
                f"Los pesos de los artefactos deben sumar 1.0 (actual: {total_weight})"
            )
        self.artifacts = sorted(artifacts, key=lambda a: a.id)

    # ------------------------------------------------------------------ #
    def execute(self, solution: Solution, now: datetime | None = None) -> Assessment:
        now = now or datetime.now(ZoneInfo("America/Bogota"))
        artifact_results = tuple(
            self._apply_artifact(artifact, solution) for artifact in self.artifacts
        )
        overall = scoring.weighted_average(
            [(r.score, r.artifact.weight) for r in artifact_results]
        )
        findings = tuple(
            sorted(
                (f for r in artifact_results for f in r.findings),
                key=lambda f: (not f.blocking, SEVERITY_RANK[f.severity], f.id),
            )
        )
        verdict, reason = self._verdict(artifact_results, findings)
        return Assessment(
            solution=solution,
            generated_at=now.strftime("%Y-%m-%dT%H:%M %Z"),
            artifact_results=artifact_results,
            overall_score=round(overall, 1),
            maturity_level=scoring.maturity_level_for(overall),
            verdict=verdict,
            verdict_reason=reason,
            findings=findings,
            heatmap=self._heatmap(artifact_results),
            roadmap=self._roadmap(findings),
        )

    # ------------------------------------------------------------------ #
    def _apply_artifact(self, artifact: Artifact, solution: Solution) -> ArtifactResult:
        results: list[CriterionResult] = []
        findings: list[Finding] = []
        for criterion in artifact.criteria:
            result, finding = self._apply_criterion(artifact, criterion, solution)
            results.append(result)
            if finding:
                findings.append(finding)
        scored = [
            (r.score, r.criterion.weight) for r in results if r.score is not None
        ]
        score = round(scoring.weighted_average(scored) * 100, 1)
        gate_passed = None
        if artifact.is_gate:
            gate_passed = all(r.score is None or r.score >= 1.0 for r in results)
        return ArtifactResult(
            artifact=artifact,
            results=tuple(results),
            score=score,
            gate_passed=gate_passed,
            findings=tuple(findings),
        )

    def _apply_criterion(
        self, artifact: Artifact, criterion: Criterion, solution: Solution
    ) -> tuple[CriterionResult, Finding | None]:
        evidence = solution.inputs.get(criterion.id)
        if evidence is None:
            result = CriterionResult(
                criterion=criterion,
                score=0.0,
                label=scoring.LABEL_MISSING,
                evidence="La solución no aportó evidencia para este criterio.",
                source="—",
            )
            finding = self._finding(
                artifact, criterion, result, missing=True, blocking=False
            )
            return result, finding

        if evidence.not_applicable:
            result = CriterionResult(
                criterion=criterion,
                score=None,
                label=scoring.LABEL_NA,
                evidence=evidence.evidence,
                source=evidence.source,
            )
            return result, None

        score = scoring.score_input(artifact.scale, criterion, evidence)
        detail = self._detail(artifact, criterion, evidence)
        result = CriterionResult(
            criterion=criterion,
            score=score,
            label=scoring.label_for_score(score),
            evidence=evidence.evidence,
            source=evidence.source,
            detail=detail,
        )
        if score >= 1.0:
            return result, None
        blocking = self._is_blocking(artifact, criterion, score)
        return result, self._finding(artifact, criterion, result, False, blocking)

    @staticmethod
    def _detail(artifact: Artifact, criterion: Criterion, evidence) -> str:
        if artifact.scale == "maturity":
            level = evidence.level
            description = (criterion.maturity_levels or {}).get(str(level), "")
            return f"Nivel {level}/4 — {description}" if description else f"Nivel {level}/4"
        if artifact.scale == "scenario" and criterion.measure:
            m = criterion.measure
            return (
                f"Medido: {evidence.measured:g} {m.unit} · Objetivo: {m.comparator} "
                f"{m.target:g} {m.unit}"
            )
        return f"Estado declarado: {evidence.status}"

    @staticmethod
    def _is_blocking(artifact: Artifact, criterion: Criterion, score: float) -> bool:
        # Un límite violado o un criterio de alta criticidad que falla en un
        # gate son bloqueantes para producción.
        if score > 0.0:
            return False
        if artifact.kind == "risk-catalog":
            return True
        return artifact.is_gate and criterion.criticality == "alta"

    @staticmethod
    def _finding(
        artifact: Artifact,
        criterion: Criterion,
        result: CriterionResult,
        missing: bool,
        blocking: bool,
    ) -> Finding:
        severity = scoring.severity_for(
            criterion.criticality, result.score or 0.0, missing=missing
        )
        title = (
            f"Sin evidencia para: {criterion.name}"
            if missing
            else f"{result.label}: {criterion.name}"
        )
        return Finding(
            id=f"H-{criterion.id}",
            criterion_id=criterion.id,
            artifact_id=artifact.id,
            artifact_name=artifact.name,
            title=title,
            severity=severity,
            theme=criterion.theme,
            quality_attributes=criterion.quality_attributes,
            evidence=result.evidence + (f" ({result.detail})" if result.detail else ""),
            recommendation=criterion.recommendation,
            effort=criterion.effort,
            kb_refs=criterion.kb_refs,
            blocking=blocking,
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _verdict(
        results: tuple[ArtifactResult, ...], findings: tuple[Finding, ...]
    ) -> tuple[str, str]:
        criticals = [f for f in findings if f.severity == "Crítico"]
        blockers = [f for f in findings if f.blocking]
        gates_failed = [r for r in results if r.gate_passed is False]
        if criticals or blockers:
            return (
                "NO APTO para nuevas liberaciones críticas sin plan de remediación",
                f"{len(criticals)} hallazgo(s) críticos y {len(blockers)} bloqueante(s) "
                "violan límites innegociables del Chapter.",
            )
        if gates_failed:
            names = ", ".join(r.artifact.name for r in gates_failed)
            return (
                "APTO CON CONDICIONES",
                f"No supera el/los quality gate(s): {names}.",
            )
        return ("APTO", "Sin hallazgos críticos ni bloqueantes; quality gates superados.")

    @staticmethod
    def _heatmap(results: tuple[ArtifactResult, ...]) -> dict[str, float]:
        buckets: dict[str, list[tuple[float, float]]] = {}
        for r in results:
            for cr in r.results:
                if cr.score is None:
                    continue
                for qa in cr.criterion.quality_attributes:
                    buckets.setdefault(qa, []).append((cr.score, cr.criterion.weight))
        return {
            qa: round(scoring.weighted_average(pairs) * 100, 1)
            for qa, pairs in sorted(buckets.items())
        }

    @staticmethod
    def _roadmap(findings: tuple[Finding, ...]) -> tuple[RoadmapItem, ...]:
        by_theme: dict[str, list[Finding]] = {}
        for f in findings:
            by_theme.setdefault(f.theme, []).append(f)
        items: list[RoadmapItem] = []
        for theme, group in by_theme.items():
            top = min(group, key=lambda f: SEVERITY_RANK[f.severity])
            actions: list[str] = []
            for f in group:
                if f.recommendation not in actions:
                    actions.append(f.recommendation)
            effort = max(group, key=lambda f: EFFORT_RANK.get(f.effort, 1)).effort
            items.append(
                RoadmapItem(
                    theme=theme,
                    horizon=scoring.HORIZON_BY_SEVERITY[top.severity],
                    severity=top.severity,
                    actions=tuple(actions),
                    criteria=tuple(sorted({f.criterion_id for f in group})),
                    effort=effort,
                )
            )
        items.sort(key=lambda i: (SEVERITY_RANK[i.severity], -len(i.criteria), i.theme))
        return tuple(items)
