"""Adaptador de salida: resultados en JSON para consumo por otras herramientas."""
from __future__ import annotations

import json
from dataclasses import asdict

from ..domain.models import Assessment


def render_json(a: Assessment) -> str:
    payload = {
        "solution": {
            "id": a.solution.id,
            "name": a.solution.name,
            "client": a.solution.client,
            "version": a.solution.version,
        },
        "generated_at": a.generated_at,
        "overall_score": a.overall_score,
        "maturity_level": a.maturity_level,
        "verdict": a.verdict,
        "verdict_reason": a.verdict_reason,
        "heatmap": a.heatmap,
        "artifacts": [
            {
                "id": r.artifact.id,
                "name": r.artifact.name,
                "kind": r.artifact.kind,
                "weight": r.artifact.weight,
                "score": r.score,
                "gate_passed": r.gate_passed,
                "counts": r.counts,
                "criteria": [
                    {
                        "id": cr.criterion.id,
                        "name": cr.criterion.name,
                        "score": cr.score,
                        "label": cr.label,
                        "detail": cr.detail,
                        "evidence": cr.evidence,
                        "source": cr.source,
                        "quality_attributes": list(cr.criterion.quality_attributes),
                    }
                    for cr in r.results
                ],
            }
            for r in a.artifact_results
        ],
        "findings": [asdict(f) for f in a.findings],
        "roadmap": [asdict(i) for i in a.roadmap],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
