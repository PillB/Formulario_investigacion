# Wireframes y jerarquía de layout

Estos artefactos documentan la estructura y los rótulos visibles de la aplicación Tkinter según el orden real de pestañas configurado en `app.py`. Todas las etiquetas y nombres de campo provienen de los módulos de UI (por ejemplo `ui/frames/case.py`, `ui/frames/clients.py`, `ui/frames/products.py`, `ui/frames/team.py`, `ui/frames/risk.py`, `ui/frames/norm.py`, y las funciones `build_analysis_tab`, `build_actions_tab`, `build_summary_tab` en `app.py`). Para extraer los textos se usaron búsquedas dirigidas con `rg` sobre `ui/` y la lectura manual de las funciones de construcción de pestañas.

## Contenido
- `layout_hierarchy.mmd`: diagrama de alto nivel con el orden del `Notebook` ("Caso y participantes", "Riesgos", "Normas", "Análisis y narrativas", "Acciones", "Resumen") y los bloques principales de cada pestaña.
- `tab01_caso_participantes.mmd`: wireframe en blanco y negro de la pestaña principal con sus cuatro secciones (Datos generales del caso, Clientes implicados, Productos investigados, Colaboradores involucrados) y campos clave como "Número de caso (AAAA-XXXX)", "Tipo de informe", taxonomía, investigador, fechas, centro de costos, datos de clientes, productos (montos y reclamos) y colaboradores.
- `tab02_riesgos.mmd`: vista de la pestaña "Riesgos" con tabla encabezado y acordeones por riesgo (ID riesgo, Criticidad, Líder, Exposición residual, Descripción, Planes de acción).
- `tab03_normas.mmd`: vista de la pestaña "Normas" con tabla de resumen y acordeones (ID de norma, Fecha de vigencia, Descripción).
- `tab04_analisis.mmd`: pestaña "Análisis y narrativas" con textos enriquecidos (Antecedentes, Modus operandi, Hallazgos principales, Descargos del colaborador, Conclusiones, Recomendaciones y mejoras) y las secciones extendidas activables (Encabezado extendido, Recomendaciones categorizadas, Investigador principal, Operaciones, Anexos).
- `tab05_acciones.mmd`: pestaña "Acciones" con controles de sonido y tema, grupo "Catálogos de detalle" (estado, Cargar catálogos, Iniciar sin catálogos, barra de progreso) y grupo "Importar datos masivos (CSV)" (botones para clientes, colaboradores, productos, combinado, riesgos, normas, reclamos, estado y barra de progreso).
- `tab06_resumen.mmd`: pestaña "Resumen" con tablas compactas para Clientes, Colaboradores, Asignaciones por colaborador, Productos, Riesgos, Reclamos y Normas.
- `generate_wireframes.py`: script para producir las imágenes PNG, el PDF `wireframes.pdf`, tablas CSV auxiliares y un registro de ejecución basado en los archivos `.mmd`.

## Generación de artefactos
Para cumplir con la restricción de no versionar binarios, las imágenes y el PDF se generan bajo demanda. Requiere `Pillow` (instalar con `pip install pillow`) y la CLI de Mermaid (`npm install -g @mermaid-js/mermaid-cli` para obtener el comando `mmdc` en el `PATH`). Ejecute desde este directorio:

```bash
python generate_wireframes.py
```

El script realiza las siguientes acciones:

1. Renderiza cada archivo `.mmd` usando la CLI de Mermaid con escala aumentada (`-s 2.0`) para obtener PNGs nítidos del diagrama real.
2. Genera bocetos en blanco y negro (`*_sketch.png`) que simulan la distribución visual básica de cada pestaña según los frames de `ui/` y los constructores en `app.py`.
3. Construye `wireframes.pdf` respetando el orden real de pestañas configurado en `app.py` (incluye los PNG de Mermaid y los bocetos secuenciales).
4. Escribe `wireframe_architecture.csv` con el orden de pestañas/archivos procesados.
5. Genera `wireframes_manifest.csv` con los artefactos construidos y el conteo de líneas de entrada.
6. Registra los eventos de ejecución en `wireframes_generation.log` para facilitar depuración sin depender de la salida estándar.

Si prefiere evitar dependencias externas en pruebas automatizadas, `generate_assets` acepta un parámetro `renderer` para inyectar una función de renderizado personalizada que reciba `(source_path, png_target)`. El valor por defecto usa `mmdc` y fallará con un mensaje claro si la CLI no está instalada.

## Exportar wireframes a Excel
El script `tools/export_wireframes_to_excel.py` construye la interfaz real de `FraudCaseApp` y toma las posiciones de los widgets (labels, entradas, combobox, badges de validación, tablas y botones) para generar un wireframe interactivo en Excel. Cada pestaña del `Notebook` se escribe en una hoja con colores y comentarios que describen el tipo de control, estado (`readonly`, autocompletar), posición de `grid` y jerarquía de secciones.

Además del wireframe de UI, el Excel incluye tres hojas de trazabilidad de exportación:
- **Reportes_DOCX_MD**: esquema de nombres generados por `build_report_filename` y las cabeceras reales de `build_llave_tecnica_rows`, `build_event_rows` y las narrativas definidas en `build_analysis_tab`, con filas de ejemplo que ilustran formatos de fechas, montos e identificadores.
- **Exports_CSV**: orden de columnas usado por `FraudCaseApp._perform_save_exports` y los CSV masivos (`*_masivos.csv`) consumidos por `iter_massive_csv_rows`, con notas de origen y ejemplos de valores válidos.
- **Logs_normalizados**: columnas de `validators.LOG_FIELDNAMES` tal como se exportan mediante `normalize_log_row`, para alinear auditorías con los CSV.

Requisitos adicionales:
- `openpyxl` (incluido en `requirements.txt`).
- Un entorno con soporte para Tkinter; si no hay display, ejecute bajo `xvfb-run`.

Ejecución:

```bash
export APP_START_CHOICE=new
python tools/export_wireframes_to_excel.py --output wireframes/Formulario_UI_wireframe.xlsx
```

El comando anterior usa el modo de arranque silencioso que ya empleamos en pruebas (`APP_START_CHOICE=new` y `PYTEST_CURRENT_TEST` se fijan automáticamente) para evitar diálogos. El archivo resultante se guarda bajo `wireframes/Formulario_UI_wireframe.xlsx` sin modificar la generación de los diagramas Mermaid existente.
