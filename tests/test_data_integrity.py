"""Pruebas de integridad de los datos reales: artefactos, solución y salida."""
import json
import unittest
from pathlib import Path

from assessment_system.adapters.html_report import render_html_report
from assessment_system.adapters.json_export import render_json
from assessment_system.adapters.json_repository import (
    JsonArtifactRepository,
    JsonSolutionRepository,
)
from assessment_system.adapters.markdown_report import (
    render_application_log,
    render_executive_report,
)
from assessment_system.application.evaluate import EvaluateSolution

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = JsonArtifactRepository(ROOT / "data" / "artifacts").load_all()
SOLUTION = JsonSolutionRepository(
    ROOT / "data" / "solutions" / "investcore-portfolio.json"
).load()


class ArtifactDataTests(unittest.TestCase):
    def test_eight_artifacts_with_weights_summing_to_one(self):
        self.assertEqual(len(ARTIFACTS), 8)
        self.assertAlmostEqual(sum(a.weight for a in ARTIFACTS), 1.0)

    def test_criterion_ids_are_globally_unique(self):
        ids = [c.id for a in ARTIFACTS for c in a.criteria]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_criterion_traces_to_the_chapter_kb(self):
        for a in ARTIFACTS:
            for c in a.criteria:
                self.assertTrue(c.kb_refs, f"{c.id} sin referencias a la KB")
                for ref in c.kb_refs:
                    self.assertTrue(
                        ref.startswith(("kb/", "tools/")), f"{c.id}: referencia inesperada {ref}"
                    )

    def test_maturity_rubric_defines_all_levels(self):
        rubric = next(a for a in ARTIFACTS if a.scale == "maturity")
        for c in rubric.criteria:
            self.assertEqual(set(c.maturity_levels), {"0", "1", "2", "3", "4"}, c.id)

    def test_scenarios_have_full_bass_template(self):
        scenarios = next(a for a in ARTIFACTS if a.scale == "scenario")
        for c in scenarios.criteria:
            for key in ("source", "stimulus", "environment", "response", "response_measure"):
                self.assertIn(key, c.scenario, f"{c.id} sin '{key}'")


class SolutionDataTests(unittest.TestCase):
    def test_solution_covers_every_criterion_exactly(self):
        expected = {c.id for a in ARTIFACTS for c in a.criteria}
        self.assertEqual(set(SOLUTION.inputs), expected)

    def test_every_evidence_has_text_and_source(self):
        for cid, ev in SOLUTION.inputs.items():
            self.assertTrue(ev.evidence.strip(), f"{cid} sin evidencia")
            self.assertTrue(ev.source.strip(), f"{cid} sin fuente")


class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assessment = EvaluateSolution(ARTIFACTS).execute(SOLUTION)

    def test_scores_are_in_range(self):
        self.assertTrue(0 <= self.assessment.overall_score <= 100)
        for r in self.assessment.artifact_results:
            self.assertTrue(0 <= r.score <= 100, r.artifact.id)

    def test_gate_and_verdict_are_consistent(self):
        dod = next(r for r in self.assessment.artifact_results if r.artifact.is_gate)
        self.assertFalse(dod.gate_passed)
        self.assertTrue(self.assessment.verdict.startswith("NO APTO"))
        self.assertTrue(any(f.blocking for f in self.assessment.findings))

    def test_renderers_produce_output(self):
        md = render_executive_report(self.assessment)
        self.assertIn("# Informe de Evaluación de Arquitectura", md)
        self.assertIn("## 7. Decisiones que implica este informe", md)
        log = render_application_log(self.assessment)
        for a in ARTIFACTS:
            self.assertIn(a.name, log)
        html = render_html_report(self.assessment)
        self.assertTrue(html.startswith("<!doctype html>"))
        payload = json.loads(render_json(self.assessment))
        self.assertEqual(len(payload["artifacts"]), 8)
        self.assertEqual(payload["overall_score"], self.assessment.overall_score)


if __name__ == "__main__":
    unittest.main()
