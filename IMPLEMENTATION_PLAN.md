# IMPLEMENTATION_PLAN.md

## Exact edits

1. **File:** `report/alerta_temprana.py`
   - **Function:** `_build_prompt`
   - **Change:** replace free-form narrative prompt with stricter template including:
     - exact instruction `Enfócate en fallas de control/proceso (no en culpas individuales).`
     - explicit JSON output schema
     - section-specific word limits
     - `fuentes` traceability requirement

2. **File:** `tests/test_alerta_temprana_export.py`
   - **Test update:** adapt expectations to new prompt sentence and section-word-limit sentence format.

3. **File:** `tests/test_prompts_snapshot.py` (new)
   - **Add tests:** snapshot-like assertions for prompt schema, anti-blame text, and section word limits.

4. **File:** `tests/test_report_generation.py` (new)
   - **Add tests:** missing-data report generation does not crash, emits `N/A`, includes `Recomendaciones`.

## Minimal safe rollout

- Keep synthesis fallback path unchanged to avoid regressions when LLM is unavailable.
- Avoid parser enforcement changes in runtime until a dedicated JSON parser integration is added.

