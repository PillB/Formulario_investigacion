# Wireframes y jerarquía de layout

Estos artefactos documentan la estructura y los rótulos visibles de la aplicación Tkinter según el orden real de pestañas configurado en `app.py`. Todas las etiquetas y nombres de campo provienen de los módulos de UI (por ejemplo `ui/frames/case.py`, `ui/frames/clients.py`, `ui/frames/products.py`, `ui/frames/team.py`, `ui/frames/risk.py`, `ui/frames/norm.py`, y las funciones `build_analysis_tab`, `build_actions_tab`, `build_summary_tab` en `app.py`). Para extraer los textos se usaron búsquedas dirigidas con `rg` sobre `ui/` y la lectura manual de las funciones de construcción de pestañas.

## Contenido
- `layout_hierarchy.mmd`: diagrama de alto nivel con el orden del `Notebook` ("Caso y participantes", "Riesgos", "Normas", "Análisis y narrativas", "Acciones", "Resumen") y los bloques principales de cada pestaña.
- `tab01_caso_participantes.mmd`: wireframe en blanco y negro de la pestaña principal con sus cuatro secciones (Datos generales del caso, Clientes implicados, Productos investigados, Colaboradores involucrados) y campos clave como "Número de caso (AAAA-XXXX)", "Tipo de informe", taxonomía, investigador, fechas, centro de costos, datos de clientes, productos (montos y reclamos) y colaboradores.
- `tab02_riesgos.mmd`: vista de la pestaña "Riesgos" con tabla encabezado y acordeones por riesgo (ID riesgo, Criticidad, Líder, Exposición residual, Descripción, Planes de acción).
- `tab03_normas.mmd`: vista de la pestaña "Normas" con tabla de resumen y acordeones (ID de norma, Fecha de vigencia, Descripción).
- `tab04_analisis.mmd`: pestaña "Análisis y narrativas" con textos enriquecidos (Antecedentes, Modus operandi, Hallazgos principales, Descargos del colaborador, Conclusiones, Recomendaciones y mejoras) y las secciones extendidas activables (Encabezado extendido, Recomendaciones categorizadas, Investigador principal, Operaciones, Anexos).
- `tab05_acciones.mmd`: pestaña "Acciones" con controles de sonido y tema, grupo "Catálogos de detalle" (estado, Cargar catálogos, Iniciar sin catálogos, barra de progreso) y grupo "Importar datos masivos (CSV)" (botones para clientes, colaboradores, productos, normas, riesgos, estado y barra de progreso).
- `tab06_resumen.mmd`: pestaña "Resumen" con tablas compactas para Clientes, Colaboradores, Asignaciones por colaborador, Productos, Riesgos, Reclamos y Normas.
- `generate_wireframes.py`: script para producir las imágenes PNG, el PDF `wireframes.pdf`, tablas CSV auxiliares y un registro de ejecución basado en los archivos `.mmd`.

## Generación de artefactos
Para cumplir con la restricción de no versionar binarios, las imágenes y el PDF se generan bajo demanda. Requiere `Pillow` (instalar con `pip install pillow`). Ejecute desde este directorio:

```bash
python generate_wireframes.py
```

El script realiza las siguientes acciones:

1. Renderiza el contenido de cada `.mmd` como texto monoespaciado en PNGs en blanco y negro.
2. Construye `wireframes.pdf` respetando el orden real de pestañas configurado en `app.py`.
3. Escribe `wireframe_architecture.csv` con el orden de pestañas/archivos procesados.
4. Genera `wireframes_manifest.csv` con los artefactos construidos y el conteo de líneas de entrada.
5. Registra los eventos de ejecución en `wireframes_generation.log` para facilitar depuración sin depender de la salida estándar.
