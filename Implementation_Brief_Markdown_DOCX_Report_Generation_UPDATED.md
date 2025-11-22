# Implementation Brief: Markdown/DOCX Report Generation

We must generate a full **Informe de Gerencia** report with all sections and tables described in the template. For each field or section, the source of data in the app is identified (or flagged if missing) and any calculations/formulas are specified. Sections include the institutional header, antecedentes, collaborator detail, modus operandi, hallazgos, descargos, riesgos, normas, conclusiones, recomendaciones, anexos, firma, and resumen.

---

## Encabezado Institucional

Fields and mappings: According to the template, the header includes fields such as **Dirigido a, Referencia, Área de Reporte, Fecha de reporte, Categoría del evento (nivel 1 y 2), Tipología del evento, Importe investigado, Contingencia, Pérdida total, Normal, Vencido, Judicial, Castigo, Analítica Contable, Centro de Costos, Producto, Procesos impactados, and N° de Reclamos**. We map these as follows:

- **Dirigido a**: Concatenate the divisions/areas/services of all involved collaborators. In code, this is built as `destinatarios_text` by combining each collaborator’s division, area and service.  

- **Referencia**: A brief case summary. The app currently builds a generic summary: e.g.  
  `“N colaboradores investigados, M productos afectados, monto investigado total X, modalidad Y”`.  
  (If a more detailed narrative is needed, it must come from analyst input.)

- **Área de Reporte**: Not explicitly captured. We may interpret this as the reporting unit (e.g. “Seguridad Corporativa”). If needed, add a new fixed field or use the main analyst’s division.

- **Fecha de reporte**: The report date. The app stores `fecha_de_ocurrencia` (case occurrence date) in `case['fecha_de_ocurrencia']`. If this is not the report date, a new date field should be added to the UI.

- **Categoría del evento (1 y 2)**: From the case data. In `CaseData.caso`, the fields `categoria1` and `categoria2` hold these values.

- **Tipología de evento (modalidad)**: Mapped to `modalidad` in case.

- **Importe investigado**: Total investigated amount. Compute as sum of all products’ `monto_investigado`:

  ```python
  Importe_investigado = sum(p["monto_investigado"] for p in case_data.productos)
  ```

- **Contingencia**: Total contingent amount. Formula:

  ```python
  Contingencia = sum(p["monto_contingencia"] for p in case_data.productos)
  ```

- **Pérdida total**: Total loss amount. Formula:

  ```python
  Perdida_total = sum(p["monto_perdida_fraude"] for p in case_data.productos)
  ```

### Normal / Vencido / Judicial / Castigo (SBS) **(UPDATED)**

**Normal / Vencido / Judicial / Castigo (SBS)**: Balances by status. Not present in the app. The product data does not record loan statuses.

- For the **current version** of the report, **no new fields or logic are added** in the UI or data model.
- In the generated Markdown/DOCX, the cells for **Normal**, **Vencido**, **Judicial** and **Castigo** in the header will be left **blank** (or with a placeholder such as “–”) so that the user can fill them **manually** based on external credit-status information (e.g. BCP/SBS reports).

In a **future version**, if required, fields could be added (for example, add fields in the **Productos** section for current balance in each status) so that:

- Normal = sum balances of products in “Normal” (current)  
- Vencido = sum balances of products in “Vencido” (arrears)  
- Judicial = sum balances in “Judicial” (legal)  
- Castigo = sum balances in “Castigado” (written-off)

These formulas are kept as **future enhancement notes** only; they are **not implemented** in the current version.

### Analítica Contable **(UPDATED)**

**Analítica Contable**: Refers to analytic accounting / accounting analysis codes.

Instead of adding a new standalone field in **Productos** or **Caso**, this field should **reuse the Analítica Contable and coding fields already present in the reclamos**:

- Take the relevant Analítica Contable / coding values from `case_data.reclamos` (e.g. the Analítica Contable and coding fields used in the reclamo frame).
- Build the header value by joining the **unique** codes into a single string (e.g. separated by `";"`).
- If there are **no reclamos** or no analytic/coding values, leave this field blank or use “–”.

This aligns the header’s **Analítica Contable** with the existing reclamo coding structure, and avoids introducing a new, redundant field in the current version.

### Centro de Costos **(UPDATED)**

**Centro de Costos**: Cost center.

- This is associated with the **case**. Add a new input field in `Caso` (e.g. `caso["centro_costos"]`) to capture it.
- The value should be a **number or list of numbers separated by `";"`**, where **each number is at least 5 digits long**.  
  Examples: `"12345"` or `"12345;67890;54321"`.

**Validation**:

1. Split the string on `";"`.  
2. Trim spaces from each token.  
3. Check that every token:
   - Is all digits.
   - Has length `>= 5`.

In the report, display the `centro_costos` string exactly as entered/validated (e.g. `"12345;67890"`).

### Remaining header fields (unchanged)

- **Producto (financiero involucrado)**: Could use the first product’s type or list unique product types. E.g., use `productos[0]["tipo_producto"]` if one main product. Otherwise list all distinct `tipo_producto` from `case_data.productos`.

- **Procesos impactados**: Likely the case’s `proceso` or processes of the products. The case has a `proceso` field in `caso`.

- **N° de Reclamos**: Number of linked claims. Compute `len(case_data.reclamos)`. These reclamos come from products (see code collecting `data["reclamos"]`).

All of the above fields (except those flagged missing) should be populated in the **Encabezado** table. Missing ones must be added to the UI or left blank as “–” in the final report, per template instructions.

---

## Antecedentes (Narrative)

This is free text describing case context. The app stores this in the analysis section: `case_data.analisis["antecedentes"]`. Map this directly to the **“Antecedentes”** section. No computation needed.

---

## Detalle de los Colaboradores Involucrados (Table) **(PARTIALLY UPDATED)**

The template table columns are **Nombres y Apellidos, Matrícula, Cargo, Falta cometida, Fecha Carta de Inmediatez, Fecha Carta de Renuncia**. Map as follows:

- **Nombres y Apellidos (UPDATED)**:  
  Add explicit name fields for each collaborator and **auto-fill** them from the team details CSV using `id_colaborador` as key (as in `ui/frames/team.py`). When the investigator selects or enters `id_colaborador`, look up the corresponding full name in the team CSV and store it in the collaborator data (e.g. `colaborador["nombre_completo"]`). Use this stored full name to populate the **Nombres y Apellidos** column. If the ID is not found in the CSV, allow manual entry or leave this as “–”.

- **Matrícula**: Mapped to `id_colaborador` from each `colaborador` record.

- **Cargo**: Mapped to `puesto` (position).

- **Falta cometida**: Mapped to `tipo_falta`.

- **Fecha Carta de Inmediatez (UPDATED)**:  
  Add a new **optional** date entry for “Fecha de Carta de Inmediatez” per collaborator (e.g. `colaborador["fecha_carta_inmediatez"]`). Some workers will **not** receive a carta de inmediatez (summons for interview), so this field may be empty. It is a date field and should be subject to the same date validations used elsewhere in the app (valid date, and any global timeline rules you already enforce).

- **Fecha Carta de Renuncia (UPDATED)**:  
  Add a similar **optional** date field per collaborator (e.g. `colaborador["fecha_carta_renuncia"]`). Some workers will **not** have a carta de renuncia (resignation letter), so this field may also be empty. It is a date field and should use the same date validations as above.

Populate one row per collaborator (`case_data.colaboradores`). If any field is not applicable or missing, use “–” as per template guidance.

---

## Modus Operandi (Narrative)

Free text. Map to `case_data.analisis["modus_operandi"]`. (No table, just narrative.)

---

## Principales Hallazgos (Table + Text) **(UPDATED BEHAVIOR)**

This section includes a table of questionable operations and accompanying narrative. The table columns from the template are: **N°, Fecha de aprobación, Cliente/DNI, Ingreso Bruto Mensual, Empresa Empleadora, Vendedor del Inmueble, Vendedor del Crédito, Producto, Importe Desembolsado (S/), Saldo Deudor (S/), Status (BCP/SBS)**. The narrative part is `case_data.analisis["hallazgos"]`.

### Current behavior (v1)

Mapping and notes: Currently the app does not collect the detailed operational data needed to fill this table. For the **current version** of the app:

- The report generator should create an **empty table** with the required columns and a **small fixed number of blank rows** (e.g. 3–5).
- The investigator will **fill all cells manually** in the generated Markdown/DOCX based on investigative findings and external data (payroll, contract records, etc.).
- Only the **narrative** part is automatically populated, using `case_data.analisis["hallazgos"]`.

### Future mapping (not implemented yet)

If, in a future version, we decide to populate this table programmatically from app data, we could map as follows:

- **N°**: Sequential counter (1, 2, …).

- **Fecha de aprobación**: Not captured (products have `fecha_ocurrencia` and `fecha_descubrimiento`, but no approval date). Consider using `fecha_de_ocurrencia` or add an approval date field.

- **Cliente / DNI**: Could join each product’s `id_cliente` to the client list and retrieve name/ID. The app has `id_cliente` in products and the client details in `case_data.clientes`, but this is not done automatically. If needed, add code to look up client name/ID from clients.

- **Ingreso Bruto Mensual / Empresa Empleadora / Vendedores**: Not in the app. These are investigative findings typically obtained from external data (e.g. payroll, contract records). Mark as missing or to be filled manually.

- **Producto**: Map to each product’s `tipo_producto`.

- **Importe Desembolsado (S/)**: Map to each product’s `monto_investigado`. A summary row with `Total desembolsado = sum of monto_investigado` may be added if desired.

- **Saldo Deudor (S/)**: The outstanding debt balance. The app has `monto_recuperado` and `monto_pago_deuda`, but no explicit “saldo” field. If needed, calculate:

  ```python
  Saldo = monto_investigado - (monto_recuperado + monto_pago_deuda)
  ```

  Otherwise, consider adding a “Saldo pendiente” field.

- **Status (BCP/SBS)**: No such field. Likely refers to internal credit status vs official classification (Normal/Vencido/Judicial/Castigo). These would require either user input or logic based on balances. Currently missing; add if required in a future version.

### Narrative (unchanged)

Narrative: The investigator’s written findings go in `case_data.analisis["hallazgos"]`.

If, in a future version, the table is implemented programmatically, code should iterate over the relevant transactions/products. For now, this section will **always contain the blank table plus the narrative**, with the table content filled manually by the user.

---

## Descargos de los Colaboradores (Narrative)

Free text summarizing each implicated collaborator’s defense. Map to `case_data.analisis["descargos"]`. If a collaborator gave no statement, note that manually. No table is generated; this is narrative text.

---

## Riesgos Identificados y Debilidades (Table)

Table columns (from template): **Líder del riesgo, ID Riesgo (GRC), Descripción del riesgo de fraude, Criticidad del riesgo, Exposición residual (USD), ID Plan de Acción**. Use the app’s risk data:

- **ID Riesgo**: `risk["id_riesgo"]`.
- **Líder del riesgo**: `risk["lider"]` (the owner of the risk).
- **Descripción del riesgo de fraude**: `risk["descripcion"]`. The current report builder omitted this, but it should be included.
- **Criticidad**: `risk["criticidad"]`.
- **Exposición residual (USD)**: `risk["exposicion_residual"]`.
- **ID Plan de Acción**: `risk["planes_accion"]` (if no plan exists, use “–”).

Fill one row per risk (`case_data.riesgos`). This matches the fields listed in code and the template.

---

## Normas Transgredidas (List or Table)

This section lists violated rules or policies. We have a **Normas** table in the UI, so we will output those entries. Each norma has:

- **N° de norma**: `norma["id_norma"]`.
- **Descripción**: `norma["descripcion"]`.
- **Fecha de vigencia**: `norma["fecha_vigencia"]`.

If desired as bullets instead of a table, format accordingly. (The prompt says a table or list is acceptable.) These map directly from `case_data.normas`. The template suggests including how the norma was violated; the app only stores the norma reference. Any narrative of the violation should be added manually.

---

## Conclusiones (Narrative)

Final conclusions text summarizing findings and responsibilities. Map to `case_data.analisis["conclusiones"]`. This is free text (no direct mapping from data fields).

---

## Recomendaciones y Mejoras (Narrative/Bullets)

Suggested actions. Map to `case_data.analisis["recomendaciones"]`. Typically a bullet list, but stored as text.

---

## Anexos (List)

List any supporting documents (e.g. evidence PDFs). The app does not track attachments; this section is filled manually. No mapping needed.

---

## Firma **(UPDATED)**

The **Firma** section lists the signatories (names and titles of the people who sign the report).

In the current version, we will:

- Add two **case-level fields** associated with the **primary investigator** (the user):

  - `caso["matricula_investigador"]`: the worker ID/matrícula of the primary investigator.
  - `caso["nombre_investigador"]`: the full name of that worker, **auto-completed** from the team details CSV using `matricula_investigador` as key (as in the team details frame), with manual override if needed.

- In the generated report, the **first signature block** should always be:

  ```text
  {nombre_investigador}
  Investigador Principal
  ```

  That is, the first signatory is the primary investigator with the fixed title **“Investigador Principal”**.

- Other signatories (e.g. **Gerente**, **Subgerente**) are **not captured** in the app data in this version and must be **typed or edited manually** in the final Markdown/DOCX document by the user.

---

## Resumen de Secciones y Tablas (Documentation)

*(Not part of the final report content.)* The template includes a summary table of which sections have tables and their columns. This is for developer reference only. We do not output this in the Markdown/Word report. Instead, ensure that all sections listed above are implemented.

Summary of mappings: Each output field should be pulled from `CaseData` as indicated, or computed by summing relevant product/risk values. Fields not present in the data model (e.g. Analítica Contable, Centro de Costos, Fecha cartas) are flagged for UI addition or manual entry. This expanded specification covers all report sections (colaboradores, hallazgos, riesgos, normas, firma, resumen, etc.) and aligns each report field with the app’s variables or a calculation.

Sources: Sections and field definitions are based on the official report template, and mappings use the app’s data structures (e.g. `CaseData.caso`, `case_data.productos`, `case_data.colaboradores`, etc.) as seen in the code. Each formula or mapping above is ready for implementation.

- `Plantilla_reporte.md`  
  https://github.com/PillB/Formulario_investigacion/blob/bad36cbba0f60141df98c8e07dbb9ae0fcc4902f/Plantilla_reporte.md

- `report_builder.py`  
  https://github.com/PillB/Formulario_investigacion/blob/bad36cbba0f60141df98c8e07dbb9ae0fcc4902f/report_builder.py

- `app.py`  
  https://github.com/PillB/Formulario_investigacion/blob/bad36cbba0f60141df98c8e07dbb9ae0fcc4902f/app.py

- `team.py`  
  https://github.com/PillB/Formulario_investigacion/blob/bad36cbba0f60141df98c8e07dbb9ae0fcc4902f/ui/frames/team.py

- `risk.py`  
  https://github.com/PillB/Formulario_investigacion/blob/bad36cbba0f60141df98c8e07dbb9ae0fcc4902f/ui/frames/risk.py

- `norm.py`  
  https://github.com/PillB/Formulario_investigacion/blob/bad36cbba0f60141df98c8e07dbb9ae0fcc4902f/ui/frames/norm.py
