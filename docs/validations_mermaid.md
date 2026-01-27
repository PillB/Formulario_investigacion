# Validaciones y reglas de negocio (Mermaid)

Este documento resume **todas las validaciones y reglas cruzadas** encontradas en el
código para el formulario Tkinter. Se tomó como referencia el **Design document CM.pdf**
(ubicado en la raíz del repositorio) y se verificó que las validaciones de formato
requeridas por dicho documento existen en la implementación actual.

> **Nota de comportamiento:** las validaciones no se ejecutan al inicio, sino
> **después de una edición de campo**. Esto se logra con `FieldValidator`, que
> reacciona a `FocusOut`, selección de combobox y eventos de edición/pegado.

## 1) Ciclo general de validación en UI

```mermaid
flowchart TD
    edit["Usuario edita campo"] --> event["Evento: FocusOut / ComboboxSelected / Paste / Cut"]
    event --> fv["validators.FieldValidator._on_change"]
    fv -->|arma validación| debounce["_schedule_validation (debounce)"]
    debounce --> run["_run_validation -> validate_callback"]
    run --> result{¿Error?}
    result -->|Sí| tooltip["ValidationTooltip.show"]
    result -->|No| hide["ValidationTooltip.hide"]
    run --> panel["FieldValidator.status_consumer -> app._publish_field_validation"]
    panel --> vp["ValidationPanel.update_entry"]
    vp --> focus["Doble click / botón 'Corregir ahora' -> focus del widget"]

    note["No se valida al iniciar: solo tras edición"] --> fv
```

**Fuentes:** `validators.py` (FieldValidator y validadores) y `app.py` (ValidationPanel + `_publish_field_validation`).

## 2) Panel de validación (UI)

```mermaid
flowchart LR
    fv["FieldValidator"] -->|status_consumer| publish["FraudCaseApp._publish_field_validation"]
    publish --> payload["_derive_validation_payload"]
    payload --> vp["ValidationPanel.update_entry"]
    vp --> tree["TreeView: estado + detalle + origen"]
    vp --> focus["Focus seleccionado -> _focus_widget_from_validation_panel"]
```

**Reglas clave:**
- Si el widget es un combobox y el valor está vacío, se marca como error.
- Cada entrada tiene severidad (`ok`, `warning`, `error`) y puede mapearse a un widget.

**Fuentes:** `app.py` (ValidationPanel, `_publish_field_validation`).

## 3) Validaciones de formato base (Design document CM.pdf)

```mermaid
flowchart TD
    formats["Validaciones de formato (validators.py)"] --> case_id["Número de caso: AAAA-NNNN"]
    formats --> team_id["ID Team Member: letra + 5 dígitos"]
    formats --> claim_id["ID Reclamo: C########"]
    formats --> analitica["Código analítica: 10 dígitos inicia 43/45/46/56"]
    formats --> agency_code["Código agencia: 6 dígitos"]
    formats --> product_id["ID Producto: reglas por tipo"]
    formats --> client_id["ID Cliente: reglas por tipo (DNI/RUC/Pasaporte/etc.)"]
    formats --> date_fmt["Fechas: YYYY-MM-DD"]
    formats --> money_fmt["Montos: >=0, 12 dígitos enteros, 2 decimales"]
```

**Fuentes:** `validators.py`.

## 4) Validaciones por sección

### 4.1 Caso (CaseFrame + app.validate_data)

```mermaid
flowchart TD
    case_fields["Caso"] --> case_id["validate_case_id"]
    case_fields --> tipo["validate_required_text + catálogo TIPO_INFORME_LIST"]
    case_fields --> tax["TAXONOMIA: categoría 1 -> 2 -> modalidad"]
    case_fields --> canal["CANAL_LIST"]
    case_fields --> proceso["PROCESO_LIST + validate_process_id"]
    case_fields --> fechas["validate_date_text (ocurrencia/descubrimiento)"]
    proceso --> lookup["process_details.csv (catalog_service) para autopoblado"]
```

**Reglas destacadas (Design document CM.pdf):**
- Fechas en formato `YYYY-MM-DD`.
- Ocurrencia < Descubrimiento y ambas ≤ hoy (aplicado por `validate_date_text` + `validate_product_dates`).

**Fuentes:** `ui/frames/case.py`, `validators.py`, `app.py`.

### 4.2 Clientes (ClientFrame + app.validate_data)

```mermaid
flowchart TD
    client["Cliente"] --> tipo_id["TIPO_ID_LIST + validate_client_id"]
    client --> flag["FLAG_CLIENTE_LIST"]
    client --> phone["validate_phone_list"]
    client --> email["validate_email_list"]
    client --> accionado["ACCIONADO_OPTIONS + validate_multi_selection"]
    client --> dup["ID único por cliente"]
```

**Fuentes:** `ui/frames/clients.py`, `validators.py`, `app.py`.

### 4.3 Colaboradores (TeamMemberFrame + app.validate_data)

```mermaid
flowchart TD
    team["Colaborador"] --> id_team["validate_team_member_id"]
    team --> flag["FLAG_COLABORADOR_LIST"]
    team --> tipo_falta["TIPO_FALTA_LIST"]
    team --> tipo_sancion["TIPO_SANCION_LIST"]
    team --> agency["validate_agency_code"]
    team --> catalog["TEAM_HIERARCHY_CATALOG + AGENCY_CATALOG"]
    team --> cond["Condición: División DCA/Canales + Área contiene 'area comercial' -> agencia obligatoria"]
    team --> dup["ID único por colaborador"]
```

**Fuentes:** `ui/frames/team.py`, `validators.py`, `app.py`.

### 4.4 Productos (ProductFrame + app.validate_data)

```mermaid
flowchart TD
    product["Producto"] --> prod_id["validate_product_id (según tipo)"]
    product --> tipo_prod["TIPO_PRODUCTO_LIST"]
    product --> tax["TAXONOMIA: cat1/cat2/modalidad"]
    product --> canal["CANAL_LIST"]
    product --> proceso["PROCESO_LIST"]
    product --> moneda["TIPO_MONEDA_LIST"]
    product --> fechas["validate_date_text + validate_product_dates"]
    product --> montos["validate_money_bounds + consistencia"]
    product --> reclamos["Reclamos obligatorios si pérdida/falla/contingencia > 0"]
    product --> dup_key["Llave técnica: caso+producto+cliente+colaborador+fecha+reclamo"]

    montos --> sum_rule["Monto investigado == pérdida+falla+contingencia+recuperado"]
    montos --> pago_rule["Monto pago deuda <= monto investigado"]
    montos --> cont_rule["Crédito/Tarjeta => contingencia == investigado"]
    reclamos --> reclamo_fields["ID reclamo + nombre analítica + código analítica"]
```

**Fuentes:** `ui/frames/products.py`, `validators.py`, `app.py`.

### 4.5 Reclamos (ClaimRow)

```mermaid
flowchart TD
    claim["Reclamo"] --> id["validate_reclamo_id"]
    claim --> name["validate_required_text (nombre analítica)"]
    claim --> code["validate_codigo_analitica"]
    claim --> catalog["models.analitica_catalog.ANALITICA_CATALOG"]
    claim --> required["Obligatorio si pérdida/falla/contingencia > 0"]
```

**Fuentes:** `ui/frames/products.py`, `models/analitica_catalog.py`, `validators.py`.

### 4.6 Involucramientos (colaboradores/clientes)

```mermaid
flowchart TD
    inv["Involucramiento"] --> amount["validate_money_bounds (monto asignado)"]
    inv --> id_req["ID requerido si hay monto; monto requerido si hay ID"]
    inv --> dup_key["Parte de la llave técnica en duplicados"]
```

**Fuentes:** `ui/frames/products.py`, `app.py`.

### 4.7 Riesgos

```mermaid
flowchart TD
    risk["Riesgo"] --> id["validate_risk_id / validate_catalog_risk_id"]
    risk --> catalog_mode["Modo catálogo -> criticidad obligatoria"]
    risk --> crit["CRITICIDAD_LIST"]
    risk --> exposure["validate_money_bounds (exposición residual)"]
    risk --> plans["Planes de acción separados por ';' sin duplicar"]
```

**Fuentes:** `ui/frames/risk.py`, `validators.py`, `app.py`.

### 4.8 Normas

```mermaid
flowchart TD
    norm["Norma"] --> id["validate_norm_id"]
    norm --> desc["validate_required_text descripción"]
    norm --> acapite["validate_required_text acápite"]
    norm --> detalle["validate_required_text detalle"]
    norm --> fecha["validate_date_text (fecha vigencia <= hoy)"]
```

**Fuentes:** `ui/frames/norm.py`, `validators.py`, `app.py`.

## 5) Llave técnica y duplicados (Design document CM.pdf)

```mermaid
flowchart TD
    key["Llave técnica"] --> fields["case_id + id_producto + id_cliente + id_colaborador + fecha_ocurrencia + id_reclamo"]
    fields --> build["utils.technical_key.build_technical_key"]
    build --> realtime["_check_duplicate_technical_keys_realtime"]
    build --> batch["validate_data (antes de exportar)"]
    realtime --> panel["ValidationPanel: entry realtime:duplicate"]
    realtime --> popup["messagebox.showerror (con cooldown)"]
```

**Fuentes:** `utils/technical_key.py`, `app.py`.

## 6) Validación antes de exportar y botones críticos

```mermaid
flowchart TD
    save_btn["Botón Guardar y enviar"] --> precheck["_validate_amount_consistency_before_export"]
    precheck --> validate["validate_data"]
    validate --> panel["ValidationPanel.show_batch_results"]
    validate --> msgbox["messagebox.showerror/showwarning"]
    validate --> export["exportación CSV/JSON/MD/DOCX"]

    import_btn["Botones Importar CSV"] --> header["_validate_import_headers"]
    header --> payload["validación por entidad"]
```

**Fuentes:** `app.py`, `utils/persistence_manager.py`.

## 7) Reglas cruzadas clave (Design document CM.pdf)

```mermaid
flowchart TD
    rules["Reglas cruzadas"] --> date_seq["Ocurrencia < Descubrimiento y <= hoy"]
    rules --> sum_rule["Monto investigado == suma de componentes"]
    rules --> pago_rule["Pago deuda <= investigado"]
    rules --> cont_rule["Crédito/Tarjeta => contingencia == investigado"]
    rules --> claim_req["Pérdida/Falla/Contingencia > 0 => reclamo completo obligatorio"]
    rules --> agency_req["División DCA/Canales + Área contiene 'area comercial' => agencia obligatoria"]
    rules --> dup_key["Prevención de duplicados por llave técnica"]
```

**Fuentes:** `ui/frames/products.py`, `validators.py`, `app.py`.

## 8) Validación post-edición (no en startup)

```mermaid
flowchart LR
    startup["Inicio de app"] -->|No valida| idle["Sin validaciones"]
    edit["Edición de campo"] --> triggers["FieldValidator: FocusOut / ComboboxSelected / Paste / Cut"]
    triggers --> validate["Validación + Panel"]
```

**Fuentes:** `validators.py`, `app.py`.
