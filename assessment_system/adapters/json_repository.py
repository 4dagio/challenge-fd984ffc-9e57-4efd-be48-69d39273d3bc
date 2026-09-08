"""Adaptador de persistencia: carga artefactos y soluciones desde JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..domain.models import (
    Artifact,
    Criterion,
    EvidenceInput,
    ScenarioMeasure,
    Solution,
)

REQUIRED_ARTIFACT_FIELDS = (
    "id", "slug", "name", "kind", "scale", "purpose", "application",
    "source", "original_dimension", "weight", "criteria",
)
REQUIRED_CRITERION_FIELDS = (
    "id", "name", "description", "quality_attributes", "criticality",
    "theme", "recommendation", "effort",
)
VALID_SCALES = ("maturity", "boolean", "tristate", "conformance", "scenario")
VALID_CRITICALITY = ("alta", "media", "baja")
VALID_EFFORT = ("bajo", "medio", "alto")


class RepositoryError(ValueError):
    """Un archivo de datos no cumple el esquema esperado."""


def _require(data: dict[str, Any], fields: tuple[str, ...], where: str) -> None:
    missing = [f for f in fields if f not in data]
    if missing:
        raise RepositoryError(f"{where}: faltan campos obligatorios {missing}")


def _criterion_from_dict(raw: dict[str, Any], artifact_id: str) -> Criterion:
    _require(raw, REQUIRED_CRITERION_FIELDS, f"Criterio en {artifact_id}")
    if raw["criticality"] not in VALID_CRITICALITY:
        raise RepositoryError(f"{raw['id']}: criticidad inválida '{raw['criticality']}'")
    if raw["effort"] not in VALID_EFFORT:
        raise RepositoryError(f"{raw['id']}: esfuerzo inválido '{raw['effort']}'")
    measure = None
    if "measure" in raw:
        m = raw["measure"]
        measure = ScenarioMeasure(
            metric=m["metric"], unit=m["unit"],
            target=float(m["target"]), comparator=m["comparator"],
        )
    return Criterion(
        id=raw["id"],
        name=raw["name"],
        description=raw["description"],
        quality_attributes=tuple(raw["quality_attributes"]),
        criticality=raw["criticality"],
        theme=raw["theme"],
        recommendation=raw["recommendation"],
        effort=raw["effort"],
        weight=float(raw.get("weight", 1.0)),
        kb_refs=tuple(raw.get("kb_refs", ())),
        scenario=raw.get("scenario"),
        measure=measure,
        maturity_levels=raw.get("maturity_levels"),
    )


def artifact_from_dict(raw: dict[str, Any]) -> Artifact:
    _require(raw, REQUIRED_ARTIFACT_FIELDS, f"Artefacto {raw.get('id', '?')}")
    if raw["scale"] not in VALID_SCALES:
        raise RepositoryError(f"{raw['id']}: escala inválida '{raw['scale']}'")
    criteria = tuple(_criterion_from_dict(c, raw["id"]) for c in raw["criteria"])
    if not criteria:
        raise RepositoryError(f"{raw['id']}: el artefacto no tiene criterios")
    ids = [c.id for c in criteria]
    if len(ids) != len(set(ids)):
        raise RepositoryError(f"{raw['id']}: identificadores de criterio duplicados")
    if raw["scale"] == "scenario" and any(c.measure is None for c in criteria):
        raise RepositoryError(f"{raw['id']}: todo escenario requiere 'measure'")
    return Artifact(
        id=raw["id"], slug=raw["slug"], name=raw["name"], kind=raw["kind"],
        scale=raw["scale"], purpose=raw["purpose"], application=raw["application"],
        source=raw["source"], original_dimension=raw["original_dimension"],
        weight=float(raw["weight"]), criteria=criteria,
        is_gate=bool(raw.get("is_gate", False)),
    )


def solution_from_dict(raw: dict[str, Any]) -> Solution:
    _require(
        raw,
        ("id", "name", "client", "domain", "version", "description",
         "context", "quality_priorities", "assessment_inputs"),
        f"Solución {raw.get('id', '?')}",
    )
    inputs: dict[str, EvidenceInput] = {}
    for cid, item in raw["assessment_inputs"].items():
        inputs[cid] = EvidenceInput(
            criterion_id=cid,
            status=item.get("status"),
            level=item.get("level"),
            measured=float(item["measured"]) if "measured" in item else None,
            evidence=item.get("evidence", ""),
            source=item.get("source", ""),
            not_applicable=bool(item.get("not_applicable", False)),
        )
    return Solution(
        id=raw["id"], name=raw["name"], client=raw["client"], domain=raw["domain"],
        version=raw["version"], description=raw["description"],
        context=raw["context"], quality_priorities=tuple(raw["quality_priorities"]),
        inputs=inputs,
        local_decisions=tuple(raw.get("local_decisions", ())),
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RepositoryError(f"{path}: JSON inválido ({exc})") from exc


class JsonArtifactRepository:
    def __init__(self, directory: Path):
        self.directory = Path(directory)

    def load_all(self) -> list[Artifact]:
        files = sorted(self.directory.glob("*.json"))
        if not files:
            raise RepositoryError(f"No hay artefactos en {self.directory}")
        artifacts = [artifact_from_dict(_read_json(p)) for p in files]
        ids = [a.id for a in artifacts]
        if len(ids) != len(set(ids)):
            raise RepositoryError("Identificadores de artefacto duplicados")
        return artifacts


class JsonSolutionRepository:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> Solution:
        return solution_from_dict(_read_json(self.path))
