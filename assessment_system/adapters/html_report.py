"""Adaptador de presentación: informe ejecutivo en HTML.

`render_html_report(assessment)` produce un documento HTML autocontenido.
`render_html_report(assessment, standalone=False)` produce solo el fragmento
(título, estilos y contenido) para publicarlo en una página alojada.
"""
from __future__ import annotations

from html import escape

from ..domain.models import SEVERITY_ORDER, Assessment

SEV_CLASS = {"Crítico": "critico", "Alto": "alto", "Medio": "medio", "Bajo": "bajo"}
LABEL_CLASS = {
    "Cumple": "ok", "Parcial": "warn", "No cumple": "bad",
    "Sin evidencia": "missing", "No aplica": "na",
}

FONTS = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&'
    'family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
)

CSS = """
:root{
  --ground:#F2F4F6;--surface:#FFFFFF;--surface-2:#E9EDF1;--line:#D5DCE3;
  --ink:#152029;--ink-2:#3E4C59;--muted:#6B7A88;
  --accent:#0E5C86;--accent-ink:#FFFFFF;--accent-soft:#DCEBF4;
  --critico:#B3261E;--alto:#C4661A;--medio:#A98514;--bajo:#2C7A4B;
  --critico-soft:#F8E4E2;--alto-soft:#F9E9DA;--medio-soft:#F7F0D2;--bajo-soft:#DFF0E5;
  --bar-track:#E3E8ED;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ground:#0E1419;--surface:#161D24;--surface-2:#1E2730;--line:#2B3641;
    --ink:#E7ECF0;--ink-2:#C3CCD5;--muted:#8E9CAA;
    --accent:#5DAAD6;--accent-ink:#0E1419;--accent-soft:#17303F;
    --critico:#F08A82;--alto:#E9A15C;--medio:#D9BC4C;--bajo:#6CC08F;
    --critico-soft:#3A1F1D;--alto-soft:#3A2A1A;--medio-soft:#36301A;--bajo-soft:#1B3325;
    --bar-track:#242E38;
  }
}
:root[data-theme="dark"]{
  --ground:#0E1419;--surface:#161D24;--surface-2:#1E2730;--line:#2B3641;
  --ink:#E7ECF0;--ink-2:#C3CCD5;--muted:#8E9CAA;
  --accent:#5DAAD6;--accent-ink:#0E1419;--accent-soft:#17303F;
  --critico:#F08A82;--alto:#E9A15C;--medio:#D9BC4C;--bajo:#6CC08F;
  --critico-soft:#3A1F1D;--alto-soft:#3A2A1A;--medio-soft:#36301A;--bajo-soft:#1B3325;
  --bar-track:#242E38;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font:15px/1.55 "IBM Plex Sans",-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1040px;margin:0 auto;padding:36px 22px 64px}
h1,h2,h3{font-family:"Source Serif 4",Georgia,"Times New Roman",serif;font-weight:600;
  letter-spacing:-.01em;text-wrap:balance;margin:0}
h1{font-size:2.05rem;line-height:1.15}
h2{font-size:1.35rem;margin:44px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line)}
h3{font-size:1.05rem;margin:22px 0 10px;color:var(--ink-2)}
p{max-width:68ch}
code,.mono{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.86em}
.eyebrow{font-size:.74rem;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);font-weight:600}
header{display:grid;gap:10px;padding-bottom:22px;border-bottom:2px solid var(--ink)}
header .meta{display:flex;flex-wrap:wrap;gap:6px 22px;color:var(--muted);font-size:.9rem}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:24px 0 18px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:16px 18px;display:grid;gap:4px;align-content:start}
.kpi .v{font-family:"Source Serif 4",Georgia,serif;font-size:2.2rem;font-weight:600;line-height:1;font-variant-numeric:tabular-nums}
.kpi .v.small{font-size:1.25rem;line-height:1.25;padding-top:6px}
.kpi .l{color:var(--muted);font-size:.82rem}
.kpi.score{grid-template-columns:auto 1fr;gap:6px 16px;align-items:center}
.kpi.score svg{grid-row:1/3}
.ring-track{stroke:var(--bar-track)}.ring-value{stroke:var(--accent)}
.verdict{display:grid;grid-template-columns:6px 1fr;border:1px solid var(--line);border-radius:6px;overflow:hidden;background:var(--surface)}
.verdict .stripe{background:var(--critico)}.verdict.cond .stripe{background:var(--alto)}.verdict.ok .stripe{background:var(--bajo)}
.verdict .body{padding:14px 18px}.verdict .body strong{font-family:"Source Serif 4",Georgia,serif;font-size:1.08rem}
.lede{margin:22px 0 0;color:var(--ink-2)}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:6px;background:var(--surface)}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th,td{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:var(--surface-2);font-weight:600;font-size:.78rem;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-2)}
tr:last-child td{border-bottom:0}
td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
td.id{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.82rem;white-space:nowrap;color:var(--ink-2)}
.chip{display:inline-block;padding:2px 9px;border-radius:3px;font-size:.74rem;font-weight:600;letter-spacing:.03em;white-space:nowrap;border:1px solid transparent}
.chip.critico{background:var(--critico-soft);color:var(--critico);border-color:var(--critico)}
.chip.alto{background:var(--alto-soft);color:var(--alto);border-color:var(--alto)}
.chip.medio{background:var(--medio-soft);color:var(--medio);border-color:var(--medio)}
.chip.bajo{background:var(--bajo-soft);color:var(--bajo);border-color:var(--bajo)}
.ok{color:var(--bajo);font-weight:600}.warn{color:var(--medio);font-weight:600}.bad{color:var(--critico);font-weight:600}.missing{color:var(--muted)}.na{color:var(--muted)}
.bar{height:8px;background:var(--bar-track);border-radius:2px;overflow:hidden;min-width:110px}
.bar span{display:block;height:100%}
.risks{list-style:none;margin:0;padding:0;display:grid;gap:10px;counter-reset:r}
.risks li{display:grid;grid-template-columns:auto 1fr;gap:12px;background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:12px 14px}
.risks .n{font-family:"Source Serif 4",Georgia,serif;font-size:1.4rem;color:var(--muted);line-height:1.1;min-width:1.3em}
.risks .t{font-weight:600}.risks .e{color:var(--ink-2);margin:4px 0}.risks .a{color:var(--ink);font-size:.92rem}
.risks .a b{color:var(--accent)}
.horizons{display:grid;gap:18px}
.horizon{display:grid;grid-template-columns:150px 1fr;gap:18px;padding-top:14px;border-top:1px solid var(--line)}
.horizon .when{font-family:"Source Serif 4",Georgia,serif;font-size:1.15rem;font-weight:600;line-height:1.2}
.horizon .when small{display:block;font-family:"IBM Plex Sans",sans-serif;font-size:.78rem;color:var(--muted);font-weight:400;margin-top:4px}
.theme{margin-bottom:14px}
.theme h4{margin:0 0 6px;font-size:.98rem;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.theme h4 small{color:var(--muted);font-weight:400;font-size:.8rem}
.theme ul{margin:0;padding-left:18px;color:var(--ink-2)}
.theme li{margin:3px 0}
.decisions td:first-child{font-family:"Source Serif 4",Georgia,serif;font-size:1.1rem;color:var(--muted)}
footer{color:var(--muted);font-size:.84rem;margin-top:48px;border-top:1px solid var(--line);padding-top:12px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:640px){.horizon{grid-template-columns:1fr}h1{font-size:1.6rem}}
"""


def _bar(score: float) -> str:
    color = (
        "var(--bajo)" if score >= 80 else "var(--medio)" if score >= 60
        else "var(--alto)" if score >= 40 else "var(--critico)"
    )
    return f'<div class="bar" aria-hidden="true"><span style="width:{score:.0f}%;background:{color}"></span></div>'


def _ring(score: float) -> str:
    r, c = 34, 2 * 3.14159 * 34
    dash = c * score / 100
    return (
        f'<svg width="84" height="84" viewBox="0 0 84 84" aria-hidden="true">'
        f'<circle class="ring-track" cx="42" cy="42" r="{r}" fill="none" stroke-width="8"/>'
        f'<circle class="ring-value" cx="42" cy="42" r="{r}" fill="none" stroke-width="8" '
        f'stroke-linecap="butt" stroke-dasharray="{dash:.1f} {c - dash:.1f}" '
        f'transform="rotate(-90 42 42)"/></svg>'
    )


def render_html_report(a: Assessment, standalone: bool = True) -> str:
    s = a.solution
    grouped = a.findings_by_severity()
    blockers = [f for f in a.findings if f.blocking]
    total_criteria = sum(len(r.results) for r in a.artifact_results)
    verdict_class = "ok" if a.verdict == "APTO" else "cond" if a.verdict.startswith("APTO") else ""
    short_name = s.name.split(" — ")[0]
    h: list[str] = []
    w = h.append

    if standalone:
        w("<!doctype html><html lang='es'><head><meta charset='utf-8'>")
        w("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    w(f"<title>Evaluación {escape(short_name)}</title>")
    w(FONTS)
    w(f"<style>{CSS}</style>")
    if standalone:
        w("</head><body>")
    w("<main>")

    w("<header>")
    w("<div class='eyebrow'>Informe de evaluación de arquitectura · Artefactos de assessment del Chapter de Arquitectura</div>")
    w(f"<h1>{escape(s.name)}</h1>")
    w(f"<div class='meta'><span>{escape(s.client)}</span><span>Versión {escape(s.version)}</span>"
      f"<span>Evaluado el {escape(a.generated_at)}</span>"
      f"<span>{len(a.artifact_results)} artefactos · {total_criteria} criterios</span></div>")
    w("</header>")

    w("<div class='kpis'>")
    w(f"<div class='kpi score'>{_ring(a.overall_score)}<div class='v'>{a.overall_score:.1f}</div>"
      f"<div class='l'>Puntaje global sobre 100</div></div>")
    w(f"<div class='kpi'><div class='v small'>{escape(a.maturity_level)}</div><div class='l'>Nivel de madurez arquitectónica</div></div>")
    w(f"<div class='kpi'><div class='v'>{len(grouped.get('Crítico', []))}</div><div class='l'>Hallazgos críticos</div></div>")
    w(f"<div class='kpi'><div class='v'>{len(blockers)}</div><div class='l'>Bloqueantes para producción</div></div>")
    w("</div>")
    w(f"<div class='verdict {verdict_class}'><div class='stripe'></div><div class='body'>"
      f"<strong>Veredicto: {escape(a.verdict)}.</strong><br>{escape(a.verdict_reason)}</div></div>")
    w(f"<p class='lede'>{escape(s.description)}</p>")

    w("<h2>1. Riesgos que requieren decisión inmediata</h2><ol class='risks'>")
    for i, f in enumerate(a.findings[:5], 1):
        w(f"<li><div class='n'>{i}</div><div>"
          f"<div class='t'><span class='chip {SEV_CLASS[f.severity]}'>{f.severity}</span> {escape(f.title)}</div>"
          f"<div class='e'>{escape(f.evidence)}</div>"
          f"<div class='a'><b>Acción</b> · {escape(f.recommendation)}</div></div></li>")
    w("</ol>")

    w("<h2>2. Resultados por artefacto</h2><div class='wrap'><table><thead><tr><th>Artefacto</th><th>Puntaje</th><th></th>"
      "<th>Cumple</th><th>Parcial</th><th>No cumple</th><th>Sin evidencia</th><th>Gate</th></tr></thead><tbody>")
    for r in a.artifact_results:
        c = r.counts
        gate = "—" if r.gate_passed is None else ("<span class='ok'>Superado</span>" if r.gate_passed else "<span class='bad'>No superado</span>")
        w(f"<tr><td><span class='mono'>{r.artifact.id}</span> · {escape(r.artifact.name)}</td><td class='num'>{r.score:.1f}</td><td>{_bar(r.score)}</td>"
          f"<td class='num'>{c.get('Cumple', 0)}</td><td class='num'>{c.get('Parcial', 0)}</td><td class='num'>{c.get('No cumple', 0)}</td>"
          f"<td class='num'>{c.get('Sin evidencia', 0)}</td><td>{gate}</td></tr>")
    w("</tbody></table></div>")

    w("<h2>3. Mapa de calor por atributo de calidad</h2><div class='wrap'><table><thead><tr><th>Atributo</th><th>Puntaje</th><th></th><th>Lectura</th></tr></thead><tbody>")
    for qa, score in sorted(a.heatmap.items(), key=lambda kv: kv[1]):
        reading = ("Fortaleza" if score >= 80 else "Aceptable con mejoras" if score >= 60
                   else "Debilidad relevante" if score >= 40 else "Debilidad crítica")
        w(f"<tr><td>{escape(qa.capitalize())}</td><td class='num'>{score:.1f}</td><td>{_bar(score)}</td><td>{reading}</td></tr>")
    w("</tbody></table></div>")

    w("<h2>4. Hallazgos</h2>")
    for sev in SEVERITY_ORDER:
        items = grouped.get(sev, [])
        if not items:
            continue
        w(f"<h3><span class='chip {SEV_CLASS[sev]}'>{sev}</span> {len(items)} hallazgo{'s' if len(items) != 1 else ''}</h3>")
        w("<div class='wrap'><table><thead><tr><th>ID</th><th>Hallazgo</th><th>Artefacto</th><th>Evidencia</th><th>Recomendación</th><th>Bloq.</th></tr></thead><tbody>")
        for f in items:
            w(f"<tr><td class='id'>{f.id}</td><td>{escape(f.title)}</td><td class='id'>{f.artifact_id}</td><td>{escape(f.evidence)}</td>"
              f"<td>{escape(f.recommendation)}</td><td>{'Sí' if f.blocking else ''}</td></tr>")
        w("</tbody></table></div>")

    w("<h2>5. Hoja de ruta</h2><div class='horizons'>")
    for horizon in dict.fromkeys(i.horizon for i in a.roadmap):
        items = [i for i in a.roadmap if i.horizon == horizon]
        n_crit = sum(len(i.criteria) for i in items)
        w(f"<div class='horizon'><div class='when'>{escape(horizon)}<small>{len(items)} tema{'s' if len(items) != 1 else ''} · {n_crit} criterios</small></div><div>")
        for item in items:
            w(f"<div class='theme'><h4><span class='chip {SEV_CLASS[item.severity]}'>{item.severity}</span> {escape(item.theme.capitalize())} "
              f"<small>esfuerzo {item.effort} · <span class='mono'>{', '.join(item.criteria)}</span></small></h4><ul>")
            for action in item.actions:
                w(f"<li>{escape(action)}</li>")
            w("</ul></div>")
        w("</div></div>")
    w("</div>")

    w("<h2>6. Decisiones que implica este informe</h2><div class='wrap'><table class='decisions'><thead><tr><th>#</th><th>Decisión para el comité</th><th>Opciones</th><th>Recomendación del equipo evaluador</th></tr></thead><tbody>")
    decisions = (
        ("¿Se autoriza continuar liberando funcionalidad de negocio antes de cerrar los bloqueantes?",
         "Congelar liberaciones críticas · Continuar con remediación en paralelo · Continuar sin cambios",
         "Continuar solo funcionalidad no crítica; los bloqueantes de límites del Chapter se cierran en el horizonte 0-30 días."),
        ("¿Se financia la remediación como iniciativa propia o se absorbe en el backlog del producto?",
         "Capacidad dedicada · Absorción en sprints (regla 20%)",
         "Capacidad dedicada para los temas críticos; el resto vía regla del Boy Scout y registro formal de deuda técnica."),
        ("¿Qué desviaciones frente a las decisiones (ADRs) del Chapter se aceptan formalmente?",
         "Aceptar con ADR local · Corregir · Escalar al Chapter",
         "Las desviaciones no justificadas requieren ADR local o corrección; las justificadas se mantienen y se revisan anualmente."),
        ("¿Se adoptan los escenarios de calidad (ASR) como SLOs contractuales del producto?",
         "Sí, con tableros y alertas · Solo como referencia",
         "Adoptarlos como SLOs medidos en producción para hacer visible el impacto de negocio de cada decisión."),
        ("¿Cuándo se repite la evaluación?",
         "Trimestral · Semestral · Por hito",
         "Al cierre del horizonte 0-30 días y luego trimestral, integrando los criterios automatizables como fitness functions en CI/CD."),
    )
    for i, (q, o, rec) in enumerate(decisions, 1):
        w(f"<tr><td>{i}</td><td>{escape(q)}</td><td>{escape(o)}</td><td>{escape(rec)}</td></tr>")
    w("</tbody></table></div>")

    w("<h2>7. Detalle por criterio</h2>")
    for r in a.artifact_results:
        w(f"<h3><span class='mono'>{r.artifact.id}</span> · {escape(r.artifact.name)} — {r.score:.1f}</h3>")
        w("<div class='wrap'><table><thead><tr><th>ID</th><th>Criterio</th><th>Resultado</th><th>Detalle</th><th>Evidencia</th><th>Fuente</th></tr></thead><tbody>")
        for cr in r.results:
            w(f"<tr><td class='id'>{cr.criterion.id}</td><td>{escape(cr.criterion.name)}</td>"
              f"<td class='{LABEL_CLASS[cr.label]}'>{cr.label}</td><td>{escape(cr.detail)}</td>"
              f"<td>{escape(cr.evidence)}</td><td>{escape(cr.source)}</td></tr>")
        w("</tbody></table></div>")

    w(f"<footer>Generado por el sistema de evaluación el {escape(a.generated_at)}. El sistema aplica reglas de "
      "puntuación deterministas sobre evidencias consignadas por el equipo evaluador; los juicios sobre la evidencia son humanos.</footer>")
    w("</main>")
    if standalone:
        w("</body></html>")
    return "".join(h)
