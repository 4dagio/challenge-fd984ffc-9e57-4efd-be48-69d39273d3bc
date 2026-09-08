"""Pruebas unitarias de las reglas de puntuación del dominio."""
import unittest

from assessment_system.domain import scoring
from assessment_system.domain.models import ScenarioMeasure


class StatusScoringTests(unittest.TestCase):
    def test_boolean_scale(self):
        self.assertEqual(scoring.score_status("boolean", "pass"), 1.0)
        self.assertEqual(scoring.score_status("boolean", "partial"), 0.5)
        self.assertEqual(scoring.score_status("boolean", "fail"), 0.0)

    def test_tristate_and_conformance(self):
        self.assertEqual(scoring.score_status("tristate", "at-risk"), 0.5)
        self.assertEqual(scoring.score_status("conformance", "justified-deviation"), 0.75)
        self.assertEqual(scoring.score_status("conformance", "unjustified-deviation"), 0.0)

    def test_invalid_status_raises(self):
        with self.assertRaises(scoring.ScoringError):
            scoring.score_status("boolean", "maybe")
        with self.assertRaises(scoring.ScoringError):
            scoring.score_status("unknown", "pass")


class MaturityScoringTests(unittest.TestCase):
    def test_levels_normalize_to_unit_interval(self):
        self.assertEqual(scoring.score_maturity(0), 0.0)
        self.assertEqual(scoring.score_maturity(2), 0.5)
        self.assertEqual(scoring.score_maturity(4), 1.0)

    def test_out_of_range_raises(self):
        for level in (-1, 5, None):
            with self.assertRaises(scoring.ScoringError):
                scoring.score_maturity(level)


class ScenarioScoringTests(unittest.TestCase):
    def test_met_target_scores_one(self):
        m = ScenarioMeasure("p95", "ms", 2000, "<=")
        self.assertEqual(scoring.score_scenario(m, 1500), 1.0)
        self.assertEqual(scoring.score_scenario(m, 2000), 1.0)

    def test_unmet_target_gets_partial_credit_capped(self):
        m = ScenarioMeasure("p95", "ms", 2000, "<=")
        self.assertAlmostEqual(scoring.score_scenario(m, 4000), 0.5)
        # Muy cerca del objetivo pero incumplido: nunca puntúa 1.0
        self.assertEqual(scoring.score_scenario(m, 2001), 0.9)

    def test_greater_or_equal_comparator(self):
        m = ScenarioMeasure("disp", "%", 99.9, ">=")
        self.assertEqual(scoring.score_scenario(m, 99.95), 1.0)
        self.assertLess(scoring.score_scenario(m, 99.0), 1.0)

    def test_missing_measure_raises(self):
        m = ScenarioMeasure("p95", "ms", 2000, "<=")
        with self.assertRaises(scoring.ScoringError):
            scoring.score_scenario(m, None)


class LabelsAndSeverityTests(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(scoring.label_for_score(1.0), "Cumple")
        self.assertEqual(scoring.label_for_score(0.5), "Parcial")
        self.assertEqual(scoring.label_for_score(0.0), "No cumple")
        self.assertEqual(scoring.label_for_score(None), "No aplica")

    def test_severity_matrix(self):
        self.assertEqual(scoring.severity_for("alta", 0.0), "Crítico")
        self.assertEqual(scoring.severity_for("alta", 0.5), "Alto")
        self.assertEqual(scoring.severity_for("media", 0.0), "Alto")
        self.assertEqual(scoring.severity_for("baja", 0.5), "Bajo")
        self.assertEqual(scoring.severity_for("alta", 0.0, missing=True), "Alto")
        self.assertEqual(scoring.severity_for("baja", 0.0, missing=True), "Medio")

    def test_maturity_level_thresholds(self):
        self.assertEqual(scoring.maturity_level_for(10), "Nivel 1 - Inicial")
        self.assertEqual(scoring.maturity_level_for(30), "Nivel 2 - Gestionado")
        self.assertEqual(scoring.maturity_level_for(50), "Nivel 3 - Definido")
        self.assertEqual(scoring.maturity_level_for(70), "Nivel 4 - Medido")
        self.assertEqual(scoring.maturity_level_for(85), "Nivel 5 - Optimizado")

    def test_weighted_average(self):
        self.assertEqual(scoring.weighted_average([]), 0.0)
        self.assertAlmostEqual(scoring.weighted_average([(1.0, 1), (0.0, 3)]), 0.25)


if __name__ == "__main__":
    unittest.main()
