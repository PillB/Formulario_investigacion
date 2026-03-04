# RCA_AND_FIXES.md

## Root cause analysis and fixes

1. **Symptom:** Prompt could still be interpreted as person-focused.
   - **Root cause:** Anti-blame rule not explicit/strict enough in `_build_prompt`.
   - **Fix:** Added exact sentence requiring control/process focus and no individual blame.
   - **Verify:** prompt snapshot test checks exact sentence.

2. **Symptom:** LLM response format varied unpredictably.
   - **Root cause:** No explicit structured output schema in prompt.
   - **Fix:** Added mandatory JSON schema instruction.
   - **Verify:** snapshot test asserts schema string exists.

3. **Symptom:** Traceability was not guaranteed in generated section prose.
   - **Root cause:** prompt lacked required source-list key.
   - **Fix:** `fuentes` list now mandatory in schema.
   - **Verify:** snapshot tests assert `fuentes` requirement text.

4. **Symptom:** Section limits not clearly tied to each section.
   - **Root cause:** generic wording allowed ambiguity.
   - **Fix:** changed text to “Extensión objetivo para la sección '<name>' ...”.
   - **Verify:** tests assert for Resumen and Análisis limits.

5. **Symptom:** Potential drift between new prompt and existing tests.
   - **Root cause:** old assertions referenced previous wording.
   - **Fix:** updated `tests/test_alerta_temprana_export.py` expectations.
   - **Verify:** targeted pytest run passes.

6. **Symptom:** Missing data could risk generation failures.
   - **Root cause:** no dedicated regression for minimal payload path.
   - **Fix:** added report generation test with sparse payload.
   - **Verify:** test checks file exists, 2 slides, `N/A` and `Recomendaciones` present.

7. **Symptom:** Prompt redesign lacked reproducible artifact.
   - **Root cause:** no snapshot-focused prompt test file.
   - **Fix:** added `tests/test_prompts_snapshot.py`.
   - **Verify:** file includes deterministic prompt assertions.

8. **Symptom:** Spec/code alignment around “Acciones inmediatas”.
   - **Root cause:** legacy naming in requirements history.
   - **Fix:** retained rendered section as `Recomendaciones` and documented alias strategy.
   - **Verify:** report test asserts `Recomendaciones` appears.

9. **Symptom:** Ambiguous fallback behavior when data is missing.
   - **Root cause:** behavior spread across multiple helper functions.
   - **Fix:** documented fallback `N/A` contract in prompt and test plan.
   - **Verify:** sparse report generation test.

10. **Symptom:** Hard requirement for process/control narrative not codified as acceptance.
    - **Root cause:** requirement lived in interview notes, not executable checks.
    - **Fix:** codified in tests + design spec acceptance list.
    - **Verify:** prompt snapshot + updated prompt assertion test.

