# WALKTHROUGH.md

## Core walkthrough observations (block-level)

1. `report/alerta_temprana.py::_build_prompt` composes section prompt with case metadata.
2. `_build_prompt` now enforces process/control framing and anti-blame language.
3. `_build_prompt` now requires strict JSON output schema.
4. `_build_prompt` injects section-specific word limits from `SECTION_WORD_LIMITS`.
5. `SECTION_WORD_LIMITS` includes aliases with/without accents.
6. `SECTION_MAX_NEW_TOKENS` controls generation budget by section.
7. `_synthesize_section_text` maps visible section name to dictionary keys.
8. `_synthesize_section_text` short-circuits to placeholder when source is empty.
9. `_synthesize_section_text` avoids LLM call if no substantive section content exists.
10. `_synthesize_section_text` falls back to deterministic section if LLM returns nothing.
11. `SpanishSummaryHelper` lazy-loads transformers pipeline only on first need.
12. `SpanishSummaryHelper.summarize` caches by `(section,prompt,max_tokens)`.
13. Summarizer sets deterministic seed via `set_seed(0)`.
14. `_fit_text_to_box` adjusts font from default down to minimum.
15. `_fit_text_to_box` truncates and logs warning if overflow remains.
16. `_truncate_text_to_fit` preserves word boundary near 60% threshold.
17. `_split_body_paragraphs` recognizes bullet prefixes and normalizes content.
18. `_add_section_panel` draws background shape + header + text box.
19. `_add_masthead` centralizes slide title/case metadata header rendering.
20. `_add_executive_summary_slide` composes three stacked panels.
21. `build_alerta_temprana_ppt` always produces two slides.
22. `build_alerta_temprana_ppt` renames action section to visible "Recomendaciones".
23. `build_alerta_temprana_ppt` writes layout rationale to slide notes.
24. `report/alerta_temprana_content.py::_build_resumen_section` embeds support and evidence blocks.
25. `_build_resumen_section` adds source references `[Tab: field]`.
26. `_build_resumen_section` computes monetary totals via `_aggregate_amounts`.
27. `_build_cronologia_section` prioritizes analysis narrative over operation rows.
28. `_build_cronologia_section` sorts operation events by parsed date + original index.
29. `_build_cronologia_section` uses fallback dates from case/product if operation date missing.
30. `_build_analisis_section` extracts primary finding from hallazgos.
31. `_build_analisis_section` attempts explicit control-failure sentence extraction.
32. `_extract_control_failure_sentence` uses regex for “falló/falla ... control”.
33. `_build_riesgos_section` renders risk id, description, criticidad, plan.
34. `_build_recomendaciones_section` prioritizes `analisis.recomendaciones` over legacy `acciones`.
35. `_build_responsables_section` prioritizes explicit role owners over collaborators.
36. `build_alerta_temprana_sections` returns both `recomendaciones` and alias `acciones`.
37. `build_executive_summary` assembles headline + support + evidence lists.
38. `build_executive_summary` includes cross-tab traceability references.
39. `report_builder.CaseData` is normalized mapping object for report input.
40. `CaseData.from_mapping` defensively defaults missing collections.
41. `validators.validate_case_id` enforces `AAAA-NNNN` pattern.
42. `validators.validate_date_text` supports ordering constraints (`must_be_before/after`).
43. `validators.validate_date_text` enforces “not future” with `enforce_max_today`.
44. `validators.validate_money_bounds` enforces non-negative, <=2 decimals.
45. `validators.validate_money_bounds` enforces <=12 integer digits.
46. `validators.validate_reclamo_id` enforces `C` + 8 digits.
47. `validators.validate_codigo_analitica` enforces prefixes 43/45/46/56 and 10 digits.
48. `app.py` central validation gathers per-tab errors and shows `messagebox.showerror`.
49. `app.py` includes realtime duplicate technical-key checks with cooldown.
50. `utils/technical_key.build_technical_key` centralizes duplicate key tuple format.

## Mismatch notes vs interview requirements

- Word limits are prompt-level, not hard post-generation validators (partial coverage).
- Prompt schema is enforced by instruction; parser/validator for JSON response is NOT FOUND IN REPO.
- Some executive sections are merged text blocks; sectioned traceability for each block can be improved.

