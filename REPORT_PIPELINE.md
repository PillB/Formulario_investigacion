# REPORT_PIPELINE.md

## Module graph

`app.py` → `report.alerta_temprana.build_alerta_temprana_ppt` →
`report.alerta_temprana_content.build_alerta_temprana_sections` + `build_executive_summary` →
(optional) `SpanishSummaryHelper.summarize` using `_build_prompt` →
`python-pptx` slide composition helpers.

## Call graph (alerta)

1. UI action button triggers `FraudCaseApp.generate_alerta_temprana_ppt()`.
2. Generic report helper `_generate_report_file` invokes `build_alerta_temprana_ppt(data, output_path, llm_helper)`.
3. `build_alerta_temprana_ppt` normalizes payload with `CaseData.from_mapping`.
4. Section payloads:
   - `sections = build_alerta_temprana_sections(dataset)`
   - `resumen_ejecutivo = build_executive_summary(dataset)`
5. Slide 1: `_add_executive_summary_slide`.
6. Slide 2: section-by-section `_synthesize_section_text` + `_add_section_panel`.
7. Save presentation.

## Prompt + LLM seam

- `_synthesize_section_text` builds context lines and calls `_build_prompt`.
- `SpanishSummaryHelper` lazily loads transformers pipeline if available.
- If no LLM or generation fails, deterministic section fallback is used.

## Layout constraints

- 16:9 deck constants (`SLIDE_WIDTH_16_9`, `SLIDE_HEIGHT_16_9`).
- Text fit strategy:
  - `_fit_text_to_box` estimates line capacity and shrinks font.
  - if still oversized, `_truncate_text_to_fit` truncates with ellipsis.
- Section-specific generation token budgets in `SECTION_MAX_NEW_TOKENS`.
- Section word limits in `SECTION_WORD_LIMITS` (prompt-level guidance).

## Duplicated logic observations

- Similar sanitization and truncation exist in both `alerta_temprana.py` and `alerta_temprana_content.py`.
- Date formatting logic repeated in multiple report modules (`alerta_temprana_content.py`, `resumen_ejecutivo.py`).

## Failure modes

- Missing `python-pptx`: raises runtime error with install message.
- Missing transformers: prompt generation is skipped (fallback deterministic text).
- Empty source sections: `_synthesize_section_text` returns `N/A` and avoids LLM call.

