# DESIGN_DEV_SPEC.md

## A) Goals & non-goals

### Goals
- Improve Alerta Temprana + Resumen Ejecutivo narrative quality.
- Force process/control-failure framing (not individual blame).
- Enforce predictable prompt output schema with traceability fields.
- Keep PPT generation resilient with missing/partial data.

### Non-goals
- Rebuild full UI architecture.
- Replace python-pptx engine.
- Introduce remote LLM dependencies as hard runtime requirements.

## B) Slide-by-slide spec

| Section | Purpose | Required content | Source priority | Format rules | Word limit | Do/Don't |
|---|---|---|---|---|---|---|
| Encabezado | Context anchoring | caso/código/emisor | caso + encabezado | 1 line metadata | 12-20 words | Do: factual; Don’t: judgment |
| Mensaje clave | Executive thesis | modus operandi + impacto + afectados + por qué importa + falla de control principal | analisis + montos + conteos | 2-3 sentences | 35-60 | Do: principal control gap |
| Puntos de soporte | Evidence support | hallazgos clave + fallas de proceso/control | analisis/riesgos/productos | 3-5 bullets | 70-110 | Don’t: names of investigated people |
| Evidencia/trazabilidad | Auditability | referencias a campos/evidencias | tab refs `[Tab:Campo]` | compact bullets | 70-110 | Do: cite used fields |
| Resumen (alerta) | Fast orientation | modus + impacto + #clientes/#productos | analisis + productos + clientes | 2-4 sentences | 80-120 | process-first framing |
| Cronología | Sequence clarity | timeline from analysis/ops | analisis then operaciones | ordered bullets | 90-130 | no speculation |
| Análisis | Triggering finding | hallazgo disparador + patrón + cuantificación + control gap | analisis.hallazgos/conclusiones | 3-5 bullets | 110-170 | avoid person blame |
| Riesgos identificados | Risk framing | taxonomía + proceso/canal + normas | riesgos + caso + normas | bullets with labels | 70-110 | explicit taxonomy |
| Recomendaciones | Immediate actions | recommendations by impact/feasibility | analisis.recomendaciones | action bullets | 70-110 | renamed from Acciones |
| Responsables | Accountability map | owners by unidad/producto | responsables explicit | bullet list | 55-90 | owners only, not investigated individuals |

Fallback logic: if primary source missing, use secondary; if all missing output `N/A` + `fuentes` with attempted fields.

## C) Renames and structural changes

- `Acciones inmediatas` → `Recomendaciones` (spec + rendered slide heading).
- Keep compatibility alias `acciones` in section dictionary for older callers.

## D) Prompting strategy

- Structured prompt with:
  1. Role + tone
  2. Mandatory anti-blame instruction
  3. Section-specific limits
  4. Strict JSON output schema
  5. Required `fuentes` list per section
- Explicit instruction: **“Enfócate en fallas de control/proceso (no en culpas individuales).”**

## E) Acceptance criteria (testable)

- Prompt includes exact anti-blame sentence.
- Prompt includes strict JSON schema and `fuentes` field.
- Prompt includes section-specific min/max words.
- Report generation with minimal data still produces valid PPTX with placeholders.
- Recomendaciones label appears in generated presentation.

