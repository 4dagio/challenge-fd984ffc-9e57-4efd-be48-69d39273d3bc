"""Pruebas del caso de uso de evaluación con artefactos sintéticos."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from assessment_system.application.evaluate import EvaluateSolution
from assessment_system.domain.models import (
    Artifact,
    Criterion,
    EvidenceInput,
    ScenarioMeasure,
    Solution,
)


def _criterion(cid, criticality="media", theme="tema", measure=None, weight=1.0):
    return Criterion(
        id=cid, name=f"Criterio {cid}", description="d",
        quality_attributes=("seguridad",), criticality=criticality, theme=theme,
        recommendation=f"Recomendación {cid}", effort="bajo", weight=weight,
        measure=measure,
    )


def _artifact(aid, scale, criteria, weight, kind="checklist", is_gate=False):
    return Artifact(
        id=aid, slug=aid.lower(), name=f"Artefacto {aid}", kind=kind, scale=scale,
        purpose="p", application="a", source="s", original_dimension="o",
        weight=weight, criteria=tuple(criteria), is_gate=is_gate,
    )


def _solution(inputs):
    return Solution(
        id="sol", name="Solución", client="Cliente", domain="Dominio", version="1",
        description="desc", context={}, quality_priorities=("seguridad",),
        inputs={k: EvidenceInput(criterion_id=k, **v) for k, v in inputs.items()},
    )


FIXED_NOW = datetime(2026, 9, 8, 10, 0, tzinfo=ZoneInfo("America/Bogota"))


class EvaluateSolutionTests(unittest.TestCase):
    def test_weights_must_sum_to_one(self):
        a = _artifact("A1", "boolean", [_criterion("C1")], 0.5)
        with self.assertRaises(ValueError):
            EvaluateSolution([a])

    def test_scores_findings_and_verdict(self):
        gate = _artifact(
            "A1", "boolean",
            [_criterion("G1", "alta"), _criterion("G2", "baja")],
            0.5, kind="gate", is_gate=True,
        )
        limits = _artifact(
            "A2", "tristate", [_criterion("L1", "alta"), _criterion("L2", "media")],
            0.5, kind="risk-catalog",
        )
        solution = _solution({
            "G1": {"status": "pass", "evidence": "ok"},
            "G2": {"status": "partial", "evidence": "casi"},
            "L1": {"status": "violated", "evidence": "mal"},
            "L2": {"status": "compliant", "evidence": "bien"},
        })
        result = EvaluateSolution([gate, limits]).execute(solution, now=FIXED_NOW)

        by_id = {r.artifact.id: r for r in result.artifact_results}
        self.assertEqual(by_id["A1"].score, 75.0)
        self.assertFalse(by_id["A1"].gate_passed)
        self.assertEqual(by_id["A2"].score, 50.0)
        self.assertIsNone(by_id["A2"].gate_passed)
        self.assertEqual(result.overall_score, 62.5)
        self.assertEqual(result.maturity_level, "Nivel 3 - Definido")

        findings = {f.criterion_id: f for f in result.findings}
        self.assertEqual(set(findings), {"G2", "L1"})
        self.assertEqual(findings["L1"].severity, "Crítico")
        self.assertTrue(findings["L1"].blocking)
        self.assertEqual(findings["G2"].severity, "Bajo")
        self.assertFalse(findings["G2"].blocking)
        self.assertTrue(result.verdict.startswith("NO APTO"))
        # El bloqueante se ordena primero
        self.assertEqual(result.findings[0].criterion_id, "L1")

    def test_missing_evidence_is_a_finding(self):
        a = _artifact("A1", "boolean", [_criterion("C1", "alta")], 1.0)
        result = EvaluateSolution([a]).execute(_solution({}), now=FIXED_NOW)
        self.assertEqual(result.artifact_results[0].results[0].label, "Sin evidencia")
        self.assertEqual(result.findings[0].severity, "Alto")
        self.assertEqual(result.artifact_results[0].score, 0.0)

    def test_not_applicable_is_excluded_from_score(self):
        a = _artifact("A1", "boolean", [_criterion("C1"), _criterion("C2")], 1.0)
        solution = _solution({
            "C1": {"status": "pass", "evidence": "ok"},
            "C2": {"not_applicable": True, "evidence": "no aplica"},
        })
        result = EvaluateSolution([a]).execute(solution, now=FIXED_NOW)
        self.assertEqual(result.artifact_results[0].score, 100.0)
        self.assertEqual(result.verdict, "APTO")
        self.assertEqual(result.findings, ())

    def test_scenario_scale_and_heatmap(self):
        m = ScenarioMeasure("p95", "ms", 2000, "<=")
        a = _artifact("A1", "scenario", [_criterion("Q1", "alta", measure=m)], 1.0,
                      kind="scenarios")
        result = EvaluateSolution([a]).execute(
            _solution({"Q1": {"measured": 4000, "evidence": "lento"}}), now=FIXED_NOW
        )
        self.assertEqual(result.artifact_results[0].score, 50.0)
        self.assertEqual(result.heatmap, {"seguridad": 50.0})
        self.assertIn("Medido: 4000 ms", result.artifact_results[0].results[0].detail)

    def test_roadmap_groups_by_theme_and_horizon(self):
        a = _artifact(
            "A1", "boolean",
            [_criterion("C1", "alta", theme="secretos"),
             _criterion("C2", "media", theme="secretos"),
             _criterion("C3", "baja", theme="docs")],
            1.0,
        )
        solution = _solution({
            "C1": {"status": "fail", "evidence": "x"},
            "C2": {"status": "partial", "evidence": "y"},
            "C3": {"status": "partial", "evidence": "z"},
        })
        result = EvaluateSolution([a]).execute(solution, now=FIXED_NOW)
        self.assertEqual([i.theme for i in result.roadmap], ["secretos", "docs"])
        secretos = result.roadmap[0]
        self.assertEqual(secretos.horizon, "0-30 días")
        self.assertEqual(secretos.criteria, ("C1", "C2"))
        self.assertEqual(len(secretos.actions), 2)
        self.assertEqual(result.roadmap[1].horizon, "Backlog (> 180 días)")


if __name__ == "__main__":
    unittest.main()
