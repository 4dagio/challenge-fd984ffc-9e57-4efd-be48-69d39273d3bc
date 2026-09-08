"""Adaptador de presentación: informes en Markdown.

Genera dos documentos a partir de un Assessment:
- El informe ejecutivo para tomadores de decisión (Fase 3 del reto).
- El registro detallado de aplicación de artefactos (Fase 2 del reto).
"""
from __future__ import annotations

from ..domain.models import SEVERITY_ORDER, Assessment, ArtifactResult, Finding

LABEL_ICON = {
    "Cumple": "✅",
    "Parcial": "⚠️",
    "No cumple": "❌",
    "Sin evidencia": "❓",
    "No aplica": "➖",
}
SEVERITY_ICON = {"Crítico": "🔴", "Alto": "🟠", "Medio": "🟡", "Bajo": "🟢"}


def _heat(score: float) -> str:
    if score >= 80:
        return "🟩"
    if score >= 60:
        return "🟨"
    if score >= 40:
        return "🟧"
    return "🟥"


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _refs(refs: tuple[str, ...]) -> str:
    return ", ".join(f"`{r}`" for r in refs) if refs else "—"


# --------------------------------------------------------------------------- #
# Informe ejecutivo
# --------------------------------------------------------------------------- #

def render_executive_report(a: Assessment) -> str:
    s = a.solution
    grouped = a.findings_by_severity()
    total_criteria = sum(len(r.results) for r in a.artifact_results)
    blockers = [f for f in a.findings if f.blocking]
    out: list[str] = []
    w = out.append

    w(f"# Informe de Evaluación de Arquitectura — {s.name}")
    w("")
    w("| Campo | Valor |")
    w("|---|---|")
    w(f"| **Solución evaluada** | {s.name} (v{s.version}) |")
    w(f"| **Cliente / Dominio** | {s.client} · {s.domain} |")
    w(f"| **Fecha de evaluación** | {a.generated_at} |")
    w(f"| **Marco de referencia** | Artefactos de assessment del Chapter de Arquitectura de Pragma |")
    w(f"| **Artefactos aplicados** | {len(a.artifact_results)} artefactos · {total_criteria} criterios |")
    w("")

    w("## 1. Resumen ejecutivo")
    w("")
    w(f"**Puntaje global: {a.overall_score:.1f} / 100 — {a.maturity_level}.**")
    w("")
    w(f"**Veredicto: {a.verdict}.** {a.verdict_reason}")
    w("")
    w(s.description)
    w("")
    w("| Severidad | Hallazgos |")
    w("|---|---:|")
    for sev in SEVERITY_ORDER:
        w(f"| {SEVERITY_ICON[sev]} {sev} | {len(grouped.get(sev, []))} |")
    w(f"| ⛔ Bloqueantes para producción | {len(blockers)} |")
    w("")
    w("### Los cinco riesgos que requieren decisión inmediata")
    w("")
    for i, f in enumerate(a.findings[:5], 1):
        w(f"{i}. **{SEVERITY_ICON[f.severity]} {f.title}** — {f.evidence}")
        w(f"   - *Acción:* {f.recommendation}")
    w("")

    w("## 2. Alcance y metodología")
    w("")
    w("La evaluación aplica de forma sistemática los artefactos de assessment del Chapter "
      "de Arquitectura. Cada artefacto declara *qué* se mide (criterios, escala y criticidad); "
      "el sistema de evaluación aporta *cómo* se mide (puntuación normalizada, severidad, "
      "gates y agregación ponderada). La evidencia proviene de repositorios, pipelines, "
      "tableros de observabilidad, documentación y entrevistas con el equipo.")
    w("")
    w("| Artefacto | Tipo | Escala | Peso | Dimensión original |")
    w("|---|---|---|---:|---|")
    for r in a.artifact_results:
        art = r.artifact
        w(f"| {art.id} · {art.name} | {art.kind} | {art.scale} | {art.weight:.0%} | {art.original_dimension} |")
    w("")
    w("**Escala de madurez global:** Nivel 1 Inicial (< 30) · Nivel 2 Gestionado (30-49) · "
      "Nivel 3 Definido (50-69) · Nivel 4 Medido (70-84) · Nivel 5 Optimizado (≥ 85).")
    w("")
    w("**Prioridades de calidad declaradas por el negocio:** " + ", ".join(s.quality_priorities) + ".")
    w("")

    w("## 3. Resultados por artefacto")
    w("")
    w("| Artefacto | Puntaje | Cumple | Parcial | No cumple | Sin evidencia | Gate |")
    w("|---|---:|---:|---:|---:|---:|---|")
    for r in a.artifact_results:
        c = r.counts
        gate = "—" if r.gate_passed is None else ("✅ Superado" if r.gate_passed else "❌ No superado")
        w(f"| {r.artifact.id} · {r.artifact.name} | {_heat(r.score)} {r.score:.1f} | "
          f"{c.get('Cumple', 0)} | {c.get('Parcial', 0)} | {c.get('No cumple', 0)} | "
          f"{c.get('Sin evidencia', 0)} | {gate} |")
    w("")
    w("```mermaid")
    w("xychart-beta")
    w('    title "Puntaje por artefacto (0-100)"')
    w("    x-axis [" + ", ".join(f'"{r.artifact.id}"' for r in a.artifact_results) + "]")
    w('    y-axis "Puntaje" 0 --> 100')
    w("    bar [" + ", ".join(f"{r.score:.1f}" for r in a.artifact_results) + "]")
    w("```")
    w("")

    w("## 4. Mapa de calor por atributo de calidad")
    w("")
    w("| Atributo de calidad | Puntaje | Lectura |")
    w("|---|---:|---|")
    for qa, score in sorted(a.heatmap.items(), key=lambda kv: kv[1]):
        reading = (
            "Fortaleza" if score >= 80 else
            "Aceptable con mejoras" if score >= 60 else
            "Debilidad relevante" if score >= 40 else
            "Debilidad crítica"
        )
        w(f"| {qa} | {_heat(score)} {score:.1f} | {reading} |")
    w("")

    w("## 5. Hallazgos")
    w("")
    for sev in SEVERITY_ORDER:
        items = grouped.get(sev, [])
        if not items:
            continue
        w(f"### {SEVERITY_ICON[sev]} {sev} ({len(items)})")
        w("")
        w("| ID | Hallazgo | Artefacto | Evidencia | Bloqueante |")
        w("|---|---|---|---|---|")
        for f in items:
            w(f"| {f.id} | {_md_escape(f.title)} | {f.artifact_id} | {_md_escape(f.evidence)} | "
              f"{'⛔ Sí' if f.blocking else 'No'} |")
        w("")

    w("## 6. Recomendaciones y hoja de ruta")
    w("")
    w("Las recomendaciones se agrupan por tema y se ubican en un horizonte según la severidad "
      "máxima de los hallazgos que las originan. Cada acción está trazada a los criterios que la "
      "motivan y a la referencia del Chapter que la respalda.")
    w("")
    for horizon in dict.fromkeys(i.horizon for i in a.roadmap):
        w(f"### Horizonte {horizon}")
        w("")
        for item in (i for i in a.roadmap if i.horizon == horizon):
            w(f"**{SEVERITY_ICON[item.severity]} {item.theme.capitalize()}** "
              f"(esfuerzo {item.effort}; criterios {', '.join(item.criteria)})")
            for action in item.actions:
                w(f"- {action}")
            w("")

    w("## 7. Decisiones que implica este informe")
    w("")
    w("| # | Decisión para el comité | Opciones | Recomendación del equipo evaluador |")
    w("|---|---|---|---|")
    w("| 1 | ¿Se autoriza continuar liberando funcionalidad de negocio antes de cerrar los bloqueantes? | Congelar liberaciones críticas / Continuar con plan de remediación en paralelo / Continuar sin cambios | "
      "Continuar solo funcionalidad no crítica; los bloqueantes de límites del Chapter se cierran en el horizonte 0-30 días. |")
    w("| 2 | ¿Se financia la remediación como iniciativa propia o se absorbe en el backlog del producto? | Iniciativa con capacidad dedicada / Absorción en sprints (regla 20%) | "
      "Capacidad dedicada para los temas críticos; el resto vía regla del Boy Scout y registro formal de deuda técnica. |")
    w("| 3 | ¿Qué desviaciones frente a las decisiones (ADRs) del Chapter se aceptan formalmente? | Aceptar con ADR local / Corregir / Escalar al Chapter | "
      "Las desviaciones no justificadas requieren ADR local o corrección; las justificadas se mantienen y se revisan anualmente. |")
    w("| 4 | ¿Se adoptan los escenarios de calidad (ASR) como SLOs contractuales del producto? | Sí, con tableros y alertas / Solo como referencia | "
      "Adoptarlos como SLOs medidos en producción para hacer visible el impacto de negocio de cada decisión. |")
    w("| 5 | ¿Cuándo se repite la evaluación? | Trimestral / Semestral / Por hito | "
      "Re-evaluación al cierre del horizonte 0-30 días y luego trimestral, integrando los criterios automatizables como fitness functions en CI/CD. |")
    w("")

    w("## 8. Conclusiones")
    w("")
    w(_conclusions(a))
    w("")
    w("## Anexos")
    w("")
    w("- Registro detallado de aplicación de artefactos y evidencias: `aplicacion/resultados_aplicacion.md`.")
    w("- Resultados en formato máquina: `informe/resultados_evaluacion.json`.")
    w("- Documentación de los artefactos: `artefactos/documentacion_artefactos.md`.")
    w("")
    w("---")
    w(f"*Informe generado automáticamente por el sistema de evaluación el {a.generated_at}. "
      "Los juicios sobre evidencia fueron consignados por el equipo evaluador; el sistema aplica "
      "las reglas de puntuación y agregación de forma determinista y reproducible.*")
    return "\n".join(out)


def _conclusions(a: Assessment) -> str:
    strongest = sorted(a.heatmap.items(), key=lambda kv: -kv[1])[:3]
    weakest = sorted(a.heatmap.items(), key=lambda kv: kv[1])[:3]
    gates = [r for r in a.artifact_results if r.gate_passed is not None]
    gate_text = ""
    if gates:
        gate_text = " ".join(
            f"El quality gate **{r.artifact.name}** {'se supera' if r.gate_passed else 'no se supera'} "
            f"({r.counts.get('Cumple', 0)} de {len(r.results)} verificaciones cumplidas)."
            for r in gates
        )
    return (
        f"La solución alcanza **{a.overall_score:.1f} / 100 ({a.maturity_level})**. "
        f"Sus fortalezas están en {', '.join(f'{qa} ({sc:.0f})' for qa, sc in strongest)}; "
        f"sus debilidades principales en {', '.join(f'{qa} ({sc:.0f})' for qa, sc in weakest)}. "
        f"{gate_text} "
        f"El veredicto es **{a.verdict}**: {a.verdict_reason} "
        "La hoja de ruta prioriza cerrar primero las violaciones a límites innegociables del Chapter, "
        "luego las desviaciones no justificadas frente a las decisiones institucionales y, por último, "
        "elevar la madurez de gobierno y observabilidad para que la arquitectura sea medible y evolutiva."
    )


# --------------------------------------------------------------------------- #
# Registro detallado de aplicación
# --------------------------------------------------------------------------- #

def render_application_log(a: Assessment) -> str:
    s = a.solution
    out: list[str] = []
    w = out.append
    w(f"# Aplicación de los Artefactos de Assessment — {s.name}")
    w("")
    w(f"*Generado el {a.generated_at} por el sistema de evaluación. Este documento registra, "
      "criterio por criterio, la evidencia aportada, la fuente de la evidencia y la puntuación "
      "obtenida al aplicar cada artefacto.*")
    w("")
    w("## Solución evaluada")
    w("")
    w("| Campo | Valor |")
    w("|---|---|")
    w(f"| Nombre | {s.name} |")
    w(f"| Cliente | {s.client} |")
    w(f"| Dominio | {s.domain} |")
    w(f"| Versión evaluada | {s.version} |")
    w(f"| Prioridades de calidad | {', '.join(s.quality_priorities)} |")
    w("")
    ctx = s.context
    if "actors" in ctx or "containers" in ctx:
        w("### Contexto (C4 Nivel 1 y Nivel 2)")
        w("")
        w("```mermaid")
        w("graph TD")
        w(f'    SYS["{s.name}"]')
        for actor in ctx.get("actors", []):
            w(f'    {actor["id"]}(["{actor["name"]}"]) -->|{actor["relation"]}| SYS')
        for ext in ctx.get("external_systems", []):
            w(f'    SYS -->|{ext["relation"]}| {ext["id"]}["{ext["name"]}"]')
        w("```")
        w("")
        if "containers" in ctx:
            w("| Contenedor | Tecnología | Responsabilidad |")
            w("|---|---|---|")
            for c in ctx["containers"]:
                w(f"| {c['name']} | {c['technology']} | {c['responsibility']} |")
            w("")
    if s.local_decisions:
        w("### Decisiones locales (ADRs) de la solución")
        w("")
        w("| ID | Título | Estado |")
        w("|---|---|---|")
        for d in s.local_decisions:
            w(f"| {d['id']} | {d['title']} | {d['status']} |")
        w("")

    w("## Proceso de aplicación")
    w("")
    w("1. **Cargar artefactos** desde `data/artifacts/` (validación de esquema, pesos y escalas).")
    w("2. **Cargar la solución** con sus evidencias desde `data/solutions/`.")
    w("3. **Aplicar cada criterio**: traducir la evidencia a una puntuación 0..1 según la escala del artefacto.")
    w("4. **Generar hallazgos** para todo criterio no cumplido, con severidad derivada de la criticidad.")
    w("5. **Agregar**: puntaje por artefacto, puntaje global ponderado, mapa de calor y gates.")
    w("6. **Construir la hoja de ruta** agrupando recomendaciones por tema y horizonte.")
    w("")

    for r in a.artifact_results:
        w(_artifact_section(r))
    return "\n".join(out)


def _artifact_section(r: ArtifactResult) -> str:
    art = r.artifact
    lines: list[str] = []
    w = lines.append
    w(f"## {art.id} · {art.name}")
    w("")
    w(f"- **Propósito:** {art.purpose}")
    w(f"- **Cómo se aplicó:** {art.application}")
    w(f"- **Fuente del Chapter:** `{art.source}`")
    w(f"- **Escala:** {art.scale} · **Peso en el puntaje global:** {art.weight:.0%}")
    gate = ""
    if r.gate_passed is not None:
        gate = " · **Gate:** " + ("✅ superado" if r.gate_passed else "❌ no superado")
    w(f"- **Resultado:** {r.score:.1f} / 100{gate}")
    w("")
    if art.scale == "scenario":
        w("| ID | Escenario | Estímulo → Respuesta esperada | Medida objetivo | Medido | Resultado | Fuente |")
        w("|---|---|---|---|---|---|---|")
        for cr in r.results:
            c = cr.criterion
            sc = c.scenario or {}
            m = c.measure
            stim = f"{sc.get('stimulus', '')} → {sc.get('response', '')}"
            target = f"{m.comparator} {m.target:g} {m.unit}" if m else "—"
            w(f"| {c.id} | {_md_escape(c.name)} | {_md_escape(stim)} | {target} | "
              f"{_md_escape(cr.detail.split('·')[0].replace('Medido: ', '')) if cr.detail else '—'} | "
              f"{LABEL_ICON[cr.label]} {cr.label} | {_md_escape(cr.source)} |")
        w("")
        w("**Evidencia por escenario:**")
        w("")
        for cr in r.results:
            w(f"- **{cr.criterion.id}** — {cr.evidence}")
    else:
        w("| ID | Criterio | Resultado | Detalle | Evidencia | Fuente |")
        w("|---|---|---|---|---|---|")
        for cr in r.results:
            w(f"| {cr.criterion.id} | {_md_escape(cr.criterion.name)} | {LABEL_ICON[cr.label]} {cr.label} | "
              f"{_md_escape(cr.detail) or '—'} | {_md_escape(cr.evidence)} | {_md_escape(cr.source) or '—'} |")
    w("")
    if r.findings:
        w("**Hallazgos derivados:**")
        w("")
        for f in r.findings:
            w(f"- {SEVERITY_ICON[f.severity]} **{f.id}** ({f.severity}{', bloqueante' if f.blocking else ''}): "
              f"{f.recommendation} — Referencias: {_refs(f.kb_refs)}")
    else:
        w("**Hallazgos derivados:** ninguno; todos los criterios se cumplen.")
    w("")
    return "\n".join(lines)
