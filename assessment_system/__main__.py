"""Interfaz de línea de comandos del sistema de evaluación.

Uso:
    python3 -m assessment_system evaluate [--artifacts DIR] [--solution FILE] [--out DIR]
    python3 -m assessment_system list-artifacts [--artifacts DIR]
    python3 -m assessment_system validate [--artifacts DIR] [--solution FILE]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .adapters.html_report import render_html_report
from .adapters.json_export import render_json
from .adapters.json_repository import (
    JsonArtifactRepository,
    JsonSolutionRepository,
    RepositoryError,
)
from .adapters.markdown_report import render_application_log, render_executive_report
from .application.evaluate import EvaluateSolution
from .domain.scoring import ScoringError

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACTS = ROOT / "data" / "artifacts"
DEFAULT_SOLUTION = ROOT / "data" / "solutions" / "investcore-portfolio.json"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="assessment_system",
        description="Aplica los artefactos de assessment del Chapter de Arquitectura a una solución.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    ev = sub.add_parser("evaluate", help="Evalúa una solución y genera los informes")
    ev.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    ev.add_argument("--solution", type=Path, default=DEFAULT_SOLUTION)
    ev.add_argument("--out", type=Path, default=ROOT, help="Directorio raíz de salida")
    ev.add_argument("--format", choices=("md", "html", "json", "all"), default="all")

    ls = sub.add_parser("list-artifacts", help="Lista los artefactos disponibles")
    ls.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)

    va = sub.add_parser("validate", help="Valida esquema, pesos y cobertura de evidencias")
    va.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    va.add_argument("--solution", type=Path, default=DEFAULT_SOLUTION)
    return p


def cmd_list(args: argparse.Namespace) -> int:
    artifacts = JsonArtifactRepository(args.artifacts).load_all()
    print(f"{'ID':<5} {'Peso':>5}  {'Tipo':<13} {'Crit.':>5}  Nombre")
    for a in sorted(artifacts, key=lambda x: x.id):
        print(f"{a.id:<5} {a.weight:>5.0%}  {a.kind:<13} {len(a.criteria):>5}  {a.name}")
    print(f"\nTotal: {len(artifacts)} artefactos, {sum(len(a.criteria) for a in artifacts)} criterios.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    artifacts = JsonArtifactRepository(args.artifacts).load_all()
    solution = JsonSolutionRepository(args.solution).load()
    EvaluateSolution(artifacts)  # valida pesos
    expected = {c.id for a in artifacts for c in a.criteria}
    provided = set(solution.inputs)
    missing = sorted(expected - provided)
    unknown = sorted(provided - expected)
    print(f"Artefactos: {len(artifacts)} · Criterios: {len(expected)} · Evidencias: {len(provided)}")
    if missing:
        print(f"⚠️  Criterios sin evidencia ({len(missing)}): {', '.join(missing)}")
    if unknown:
        print(f"⚠️  Evidencias sin criterio ({len(unknown)}): {', '.join(unknown)}")
    if not missing and not unknown:
        print("✅ Cobertura completa: toda evidencia corresponde a un criterio y viceversa.")
    return 1 if unknown else 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    artifacts = JsonArtifactRepository(args.artifacts).load_all()
    solution = JsonSolutionRepository(args.solution).load()
    assessment = EvaluateSolution(artifacts).execute(solution)

    out = Path(args.out)
    (out / "informe").mkdir(parents=True, exist_ok=True)
    (out / "aplicacion").mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if args.format in ("md", "all"):
        p = out / "informe" / "informe_evaluacion.md"
        p.write_text(render_executive_report(assessment), encoding="utf-8")
        written.append(p)
        p = out / "aplicacion" / "resultados_aplicacion.md"
        p.write_text(render_application_log(assessment), encoding="utf-8")
        written.append(p)
    if args.format in ("html", "all"):
        p = out / "informe" / "informe_evaluacion.html"
        p.write_text(render_html_report(assessment), encoding="utf-8")
        written.append(p)
    if args.format in ("json", "all"):
        p = out / "informe" / "resultados_evaluacion.json"
        p.write_text(render_json(assessment), encoding="utf-8")
        written.append(p)

    print(f"Solución: {solution.name} (v{solution.version})")
    print(f"Puntaje global: {assessment.overall_score:.1f}/100 — {assessment.maturity_level}")
    print(f"Veredicto: {assessment.verdict}")
    print("Por artefacto:")
    for r in assessment.artifact_results:
        gate = "" if r.gate_passed is None else (" [gate ✅]" if r.gate_passed else " [gate ❌]")
        print(f"  {r.artifact.id} {r.score:>5.1f}  {r.artifact.name}{gate}")
    sev = assessment.findings_by_severity()
    print("Hallazgos: " + " · ".join(f"{k}: {len(v)}" for k, v in sev.items()))
    print("Archivos generados:")
    for p in written:
        print(f"  - {p.relative_to(out) if p.is_relative_to(out) else p}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "evaluate":
            return cmd_evaluate(args)
        if args.command == "list-artifacts":
            return cmd_list(args)
        if args.command == "validate":
            return cmd_validate(args)
    except (RepositoryError, ScoringError, ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
