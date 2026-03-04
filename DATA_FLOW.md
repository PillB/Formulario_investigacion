# DATA_FLOW.md

## Canonical investigation object

`report_builder.CaseData` is the canonical normalized object for reporting. It stores:
`caso`, `clientes`, `colaboradores`, `productos`, `reclamos`, `involucramientos`, `riesgos`, `normas`, `analisis`, `encabezado`, `operaciones`, `anexos`, `firmas`, `recomendaciones_categorias`, `responsables`.

## Data flow narrative

1. UI capture occurs in `app.FraudCaseApp` frames and tab stores.
2. Field-level validations call helpers from `validators.py` (dates, amounts, IDs, catalogs).
3. Duplicate controls use technical key checks in `app.py` + `utils/technical_key.py`.
4. When exporting report, app passes current payload to report builders.
5. `CaseData.from_mapping()` normalizes raw dict payload.
6. `build_alerta_temprana_sections()` derives deterministic section text.
7. `build_executive_summary()` derives executive card blocks.
8. `build_alerta_temprana_ppt()` lays out slides and optionally synthesizes section text with LLM prompt.

## Section → source fields mapping

| Slide section | Primary sources | Secondary/fallback | Notes |
|---|---|---|---|
| Encabezado | `caso.id_caso`, `encabezado.referencia`, investigator fields | category/modalidad/proceso/canal concatenation | Built by `_case_title` and masthead population. |
| Mensaje clave (resumen ejecutivo) | `analisis.comentario_breve`, `analisis.hallazgos` | `N/A` | `_build_resumen_section` / `build_executive_summary`. |
| Puntos de soporte | product totals + product/client counts | placeholders | Uses `_aggregate_amounts`. |
| Evidencia/trazabilidad | `caso` dates + `encabezado` fields + refs | placeholders | Uses `[Tab: Campo]` reference tagging. |
| Resumen (alerta) | `analisis.comentario_breve`/`hallazgos` + montos + counts | placeholders | Contains support/evidence bundles. |
| Cronología | `analisis` narrative fields | sorted `operaciones` + date fallback | `_build_cronologia_section`. |
| Análisis | hallazgo principal, control-failure sentence | antecedentes/modus/conclusiones/comentario_amplio | `_extract_control_failure_sentence` heuristic. |
| Riesgos identificados | `riesgos[].{id,descripcion,criticidad,planes_accion}` | placeholder | `_build_riesgos_section`. |
| Recomendaciones | `analisis.recomendaciones` then `analisis.acciones` | operaciones acciones | renamed from immediate actions concept. |
| Responsables | explicit `responsables[]` roles | colaboradores fallback | Prefers scope unidad/producto over investigated people. |

## Validation and transformation seams

- Date format/order/today constraints: `validate_date_text`, `validate_product_dates`.
- Amount parsing/range/precision: `validate_money_bounds`, `sum_investigation_components`.
- IDs: `validate_case_id`, `validate_reclamo_id`, `validate_codigo_analitica`, `validate_client_id`, team member validators.
- Duplicate prevention: technical key combination in app realtime checks.

