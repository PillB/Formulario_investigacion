# TEST_PLAN.md

## Coverage targets

1. Prompt structure snapshot coverage
   - Assert anti-blame instruction sentence exact match.
   - Assert strict JSON schema string appears.
   - Assert section-specific word limit text appears.

2. Word-limit contract coverage
   - Validate `_build_prompt("Resumen")` and `_build_prompt("Análisis")` include expected ranges.

3. Missing/partial data fallback coverage
   - Generate PPT with minimal dataset and assert placeholders (`N/A`) render.

4. Generation stability
   - Ensure `build_alerta_temprana_ppt` creates 2-slide deck and key section labels.

## Test files

- `tests/test_prompts_snapshot.py` (new)
- `tests/test_report_generation.py` (new)
- `tests/test_alerta_temprana_export.py` (updated expectations)

## Execution

- `pytest -q tests/test_prompts_snapshot.py tests/test_report_generation.py tests/test_alerta_temprana_export.py`

