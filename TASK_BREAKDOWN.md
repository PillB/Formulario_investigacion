# TASK_BREAKDOWN.md

## PR-sized task plan

### Task 1 — Prompt hardening for Alerta Temprana
- **Files:** `report/alerta_temprana.py`
- **Changes:** enforce anti-blame/process-focus sentence + JSON schema + fuentes + per-section limits.
- **Tests:** `tests/test_prompts_snapshot.py`, `tests/test_alerta_temprana_export.py::test_build_prompt_emphasizes_control_process_failures_and_interview_scope`.

### Task 2 — Snapshot and contract tests for prompt
- **Files:** `tests/test_prompts_snapshot.py`
- **Changes:** add snapshot-style assertions for schema and limits.
- **Tests:** run file standalone + with existing alerta tests.

### Task 3 — Resilience test for report generation
- **Files:** `tests/test_report_generation.py`
- **Changes:** minimal-case PPT generation regression test.
- **Tests:** run standalone; in environments without `python-pptx`, ensure skip semantics.

### Task 4 — Documentation pass (analysis/spec/plan)
- **Files:**
  - `REPO_MAP.md`, `DATA_FLOW.md`, `REPORT_PIPELINE.md`, `WALKTHROUGH.md`,
  - `DESIGN_DEV_SPEC.md`, `PROMPT_V2.md`, `IMPLEMENTATION_PLAN.md`,
  - `TEST_PLAN.md`, `RCA_AND_FIXES.md`, `TASK_BREAKDOWN.md`
- **Changes:** deep-dive artifacts and implementation plan.
- **Tests:** doc-only (no runtime).

