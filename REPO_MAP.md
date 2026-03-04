# REPO_MAP.md

## Top-level map and entry points

- `main.py`: launcher that creates Tk root, instantiates `FraudCaseApp`, and starts `mainloop()`. 
- `app.py`: main Tkinter application (UI tabs, validation orchestration, persistence hooks, report exports).
- `validators.py`: reusable validation functions (fechas, montos, IDs, catálogos, errores con `messagebox.showerror`).
- `report_builder.py`: canonical `CaseData` mapping + file naming and export row builders (`eventos`, `llave_tecnica`).
- `report/alerta_temprana.py`: PPTX generation for Alerta Temprana + prompt builder (`_build_prompt`) + optional LLM summarization.
- `report/alerta_temprana_content.py`: deterministic content synthesis for sections + executive summary payload.
- `report/resumen_ejecutivo.py`: markdown executive summary generator.
- `report/carta_inmediatez.py`: carta generation module.
- `utils/technical_key.py`: technical key helpers for duplicate prevention.
- `utils/persistence_manager.py`: persistence abstraction used by app state management.
- `models/catalog_service.py` + `models/autofill_service.py`: catalogs/autofill model services.
- `ui/main_window.py`, `ui/frames/*`: frame-level UI components and layout.
- `tests/test_alerta_temprana_export.py`: primary coverage for alerta sections, prompt expectations, PPT generation.
- `tests/test_resumen_ejecutivo_export.py`: coverage for executive summary export behavior.

## Runtime model

- Execution mode: **desktop GUI app (Tkinter)**.
- Start command: `python main.py`.
- Reports are generated from app actions, including `generate_alerta_temprana_ppt()` in `app.py`.

## PPT and prompt locations

- PPT generation engine: `python-pptx` (optional import) in `report/alerta_temprana.py`.
- Prompt construction: `_build_prompt()` in `report/alerta_temprana.py`.
- Section content inputs/fallbacks: `build_alerta_temprana_sections()` in `report/alerta_temprana_content.py`.

