# Gestión de Casos de Fraude (Tkinter)

Aplicación de escritorio en Python/Tkinter para registrar, validar y exportar expedientes de fraude. Incluye pestañas para caso, clientes, colaboradores, productos, riesgos, normas, análisis y acciones; soporta validación en línea, importaciones masivas desde CSV, autoguardado y exportación a CSV/JSON/Markdown/Word.

## Contenido rápido
- [Prerrequisitos](#prerrequisitos)
- [Instalación](#instalación)
- [Ejecución rápida](#ejecución-rápida)
- [Arquitectura y estructura](#arquitectura-y-estructura)
- [Flujos principales](#flujos-principales)
- [Guía por pestaña](#guía-por-pestaña)
- [Validaciones clave](#validaciones-clave)
- [Importación y exportación](#importación-y-exportación)
- [Solución de problemas](#solución-de-problemas)
- [FAQ](#faq)
- [Pruebas](#pruebas)
- [Contribución y licencia](#contribución-y-licencia)

## Prerrequisitos
- Python 3.7 o superior.
- Dependencia requerida para el selector de fechas: `tkcalendar` (incluida en `requirements.txt`).
- Dependencia opcional: `python-docx` para generar el informe Word.
- Archivos CSV de referencia en la raíz del proyecto:
  - `client_details.csv`, `team_details.csv` para autopoblado.
  - `clientes_masivos.csv`, `colaboradores_masivos.csv`, `productos_masivos.csv`, `datos_combinados_masivos.csv` para importaciones de ejemplo.
  - `riesgos_masivos.csv`, `normas_masivas.csv`, `reclamos_masivos.csv` para cargas masivas de riesgos/normas/reclamos.
- Carpeta `external drive/` (se crea automáticamente) con permisos de escritura para respaldos.

## Instalación
1. Clona o descarga este repositorio.
2. (Opcional) habilita la exportación a Word:
   ```bash
   pip install python-docx
   ```
3. (Opcional) para regenerar el informe de arquitectura en PDF instala Mermaid CLI y ReportLab:
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   pip install -r requirements.txt
   ```

## Ejecución rápida
Desde la raíz del proyecto:
```bash
python -m main
```
La aplicación intenta cargar el último `autosave.json`. Para comenzar de cero, usa **Acciones → Borrar todos los datos**.

## Arquitectura y estructura
- **`main.py`**: punto de entrada; instancia la aplicación Tk.
- **`app.py`**: orquesta el `ttk.Notebook`, autoguardado, validaciones y exportaciones.
- **`ui/`**: widgets y pestañas (caso/participantes, riesgos, normas, análisis, acciones, resumen).
- **`models/`**: modelos y helpers de persistencia.
- **`validators.py`**: reglas de formato, montos y fechas.
- **`exports/`** (generado): CSV, JSON, Markdown y Word creados por **Guardar y enviar**.
- **`external drive/<id_caso>/`** (generado): espejo automático de los artefactos exportados, autosaves y logs.

### Diagrama de alto nivel
```mermaid
graph TD
    A[main.py] -->|Lanza| B[App (Tk)]
    B --> C[ttk.Notebook (Pestañas)]
    C --> C1[Caso y participantes]
    C --> C2[Riesgos]
    C --> C3[Normas]
    C --> C4[Análisis]
    C --> C5[Acciones]
    C --> C6[Resumen]
    B --> D[Autosave + Versionado]
    B --> E[Validaciones por campo]
    B --> F[Importadores CSV]
    B --> G[Exportadores CSV/JSON/MD/DOCX]
    G --> H[exports/]
    G --> I[external drive/<id_caso>/]
    D --> I
    E -->|Errores| B
```

### Generar el PDF de arquitectura
El PDF `Formulario_Investigacion_Architecture_and_Data_Flow.pdf` no se versiona. Para crearlo de forma local:

```bash
python build_architecture_report.py --output Formulario_Investigacion_Architecture_and_Data_Flow.pdf
```

El script recompila los diagramas Mermaid (`docs/architecture.mmd`, `docs/sequence_diagram.mmd`) usando `mermaid-cli` y ensambla
el informe con ReportLab, aplicando portada, tabla de contenidos y anexos con las imágenes generadas.

## Flujos principales
### Crear un nuevo expediente
1. Abre la app y ve a **Caso y participantes**.
2. Completa **Datos generales** (número de caso `AAAA-NNNN`, tipo de informe, taxonomía, canal y proceso).
3. Agrega **clientes** (IDs según tipo, teléfonos/correos/direcciones separados por `;`, rol/flag).
4. Agrega **colaboradores** (ID letra+5 dígitos; división, área, servicio, puesto, agencia/código si aplica; flag, tipo de falta y sanción).
5. Agrega **productos** vinculados a un cliente y colaborador: fechas, montos, tipo de producto, reclamo, analítica y accionados.
6. Completa **Riesgos** y **Normas**.
7. En **Análisis**, redacta las narrativas.
8. En **Acciones**, pulsa **Guardar y enviar** para validar y exportar.

### Importación masiva
1. Abre **Acciones**.
2. Usa los botones de **Importar** (clientes, colaboradores, productos, combinados, riesgos, normas, reclamos) y selecciona el CSV.
3. La app hidrata y valida; al terminar, las pestañas muestran los registros listos para revisión.

### Guardar, exportar y respaldar
- **Guardar y enviar** valida todo, genera CSV por entidad, un JSON completo, Markdown y Word; además espeja los artefactos en `external drive/<id_caso>/`.
- **Cargar formulario** permite restaurar cualquier respaldo JSON (versión enviada, checkpoint manual o autosave guardado).
- **Autosave** crea `autosave.json` y versiones temporales `<id_caso>_temp_<timestamp>.json` sin interrumpir el flujo.

### Pegado rápido en Resumen
- En **Resumen**, pega datos tabulares (Ctrl+V). Las tablas sincronizan con las secciones principales.
- Orden único para **Colaboradores** (Resumen y CSV): `id_colaborador`, `nombres`, `apellidos`, `flag`, `division`, `area`, `servicio`, `puesto`, `fecha_carta_inmediatez`, `fecha_carta_renuncia`, `nombre_agencia`, `codigo_agencia`, `tipo_falta`, `tipo_sancion`. Incluye ambas fechas para evitar ambigüedad al pegar desde Excel.
- Orden único para **Productos** y CSV combinado: `id_producto`, `id_cliente`, `tipo_producto`, `categoria1`, `categoria2`, `modalidad`, `canal`, `proceso`, `fecha_ocurrencia`, `fecha_descubrimiento`, `monto_investigado`, `tipo_moneda`, `monto_perdida_fraude`, `monto_falla_procesos`, `monto_contingencia`, `monto_recuperado`, `monto_pago_deuda`, `id_reclamo`, `nombre_analitica`, `codigo_analitica` (y, para `datos_combinados_masivos.csv`, `tipo_involucrado`, `id_colaborador`, `id_cliente_involucrado`, `monto_asignado`). Las tres columnas de reclamos siempre van al final en el mismo orden que los encabezados esperados.

## Guía por pestaña
| Pestaña / sección | Propósito | Entradas clave | Validaciones destacadas |
| --- | --- | --- | --- |
| Caso (Datos generales) | Identificar el expediente y su taxonomía | Número de caso, tipo de informe, categorías, canal, proceso | Formato `AAAA-NNNN`; selección obligatoria de tipo de informe y taxonomía. |
| Clientes | Registrar personas/empresas | Tipo/ID, teléfonos, correos, dirección, flag | Formato de ID según tipo; listas separadas por `;`; campos requeridos según catálogos. |
| Colaboradores | Registrar miembros del equipo | ID letra+5 dígitos, división, área, servicio, puesto, agencia/código, flag, tipo de falta/sanción | Formato de ID; agencia/código obligatorios si división = DCA o Canales de atención y área contiene "area comercial". |
| Productos | Asociar cuentas/contratos | ID de producto, cliente, fechas, montos, reclamo, analítica, tipo de producto, moneda, accionados | Fechas `YYYY-MM-DD` en orden; montos no negativos con 2 decimales; montos parciales deben sumar al investigado; reclamo/analítica obligatorios si hay pérdida/falla/contingencia > 0; contingencia = investigado para créditos/tarjetas. |
| Riesgos | Registrar riesgos | ID `RSK-XXXXXX`, líder, descripción, criticidad, exposición, planes | IDs únicos; criticidad de catálogo; planes separados por `;`. |
| Normas | Registrar normas violadas | Código `XXXX.XXX.XX.XX` (o autogenerado), descripción, fecha de vigencia | Fecha no futura; código deduplicado o autogenerado. |
| Análisis | Narrativas | Antecedentes, modus operandi, hallazgos, descargos, conclusiones, recomendaciones | Texto libre almacenado y exportado tal cual. |
| Acciones | Gestión de archivos | Importar CSV, guardar/exportar, cargar formulario, borrar datos | Ejecuta validaciones globales y sincroniza vistas tras importar. |
| Resumen | Tablas consolidadas | Vista rápida y pegado masivo | Mantiene consistencia con las secciones principales. |

## Validaciones clave
- **Fechas**: formato `YYYY-MM-DD`; ocurrencia < descubrimiento; ninguna fecha futura.
- **Montos**:
  - No negativos, máximo 12 dígitos y 2 decimales.
  - Investigado = Pérdida + Falla + Contingencia + Recuperado.
  - Pago de deuda ≤ Investigado.
  - Si el producto es crédito o tarjeta, Contingencia = Investigado.
- **IDs y formatos**:
  - Caso `AAAA-NNNN`.
  - Cliente según tipo seleccionado.
  - Colaborador letra + 5 dígitos.
  - Reclamo `C` + 8 dígitos.
  - Analítica contable: 10 dígitos iniciando con 43/45/46/56.
  - Agencia (si aplica): 6 dígitos.
- **Obligatoriedad condicional**:
  - Si Pérdida/Falla/Contingencia > 0 ⇒ Reclamo, Nombre analítica y Código analítica son obligatorios.
  - Si División = DCA o Canales de atención **y** Área contiene "area comercial" ⇒ Nombre y Código de agencia requeridos.
- **Duplicados**: Se bloquea la combinación repetida de `[Número de caso, Id producto, Id cliente, Id team member, Fecha de ocurrencia, Id de reclamo]`. Para validar basta con cliente o con colaborador (o ambos). Si un componente de la clave se deja vacío de forma intencional, se muestra como `-` en la vista y en los mensajes para que quede claro que ese segmento está ausente.

## Importación y exportación
- **Importar CSV**: desde **Acciones**, selecciona el archivo adecuado; la app valida, omite duplicados y sincroniza combobox/listados.
- **Exportar**: **Guardar y enviar** genera CSV por entidad, JSON completo, Markdown y Word (`python-docx` necesario) en `exports/`; luego duplica a `external drive/<id_caso>/`. Mensajes claros aparecen si hay problemas de escritura.

### Registro de eventos
- Los eventos se guardan en `logs.csv` con columnas `timestamp`, `tipo`, `subtipo`, `widget_id`, `coords` y `mensaje`.
- Usa IDs legibles y estables para `widget_id` (por ejemplo, `btn_guardar_enviar`, `btn_importar_clientes`, `tab_riesgos`).
- Para `subtipo`, detalla la acción (`click`, `cambio_tab`, `paste`, etc.).
- `coords` es opcional; cuando apliquen, registra la posición como `x,y` proveniente del evento Tkinter.

## Analíticas y visualización de uso
- El módulo `analytics.usage_visualizer` permite cargar `logs.csv` y generar heatmaps por pantalla con insights automáticos. Ejemplo rápido:
  ```python
  from analytics.usage_visualizer import visualize_usage

  report = visualize_usage('logs.csv', output_path='heatmaps.png')
  print(report.interpretations)
  ```
- Requiere `matplotlib` (instalar con `pip install matplotlib`). Las interpretaciones resaltan pantallas dominantes, widgets más usados, proporción de validaciones y tiempo aproximado por pestaña.

## Solución de problemas
- **Errores de validación**: se muestran debajo de los campos o mediante diálogos; corrige el formato indicado y repite la acción.
- **Permisos**: verifica acceso a `exports/` y `external drive/` si fallan los respaldos.
- **CSV inválidos**: confirma encabezados/separadores; la app indicará filas omitidas.
- **Autopoblado**: si un ID existe en `client_details.csv` o `team_details.csv`, se rellenan datos; de lo contrario, se registra advertencia.

### Análisis de causa raíz (clave técnica)
- **Síntoma observado**: se interpretó que faltaba una validación porque algunas combinaciones carecían de colaborador o cliente.
- **Causa**: el texto del tooltip y el marcador interno para valores vacíos no dejaban claro que la regla de negocio permite validar con solo cliente o solo colaborador; el marcador `"<FALTA_ASOCIACION>"` generaba ruido al depurar la clave.
- **Corrección**: se alineó la visualización y la generación de claves para mostrar `-` cuando un componente está vacío y se aclaró en la documentación que basta con una de las dos asociaciones.
- **Cómo validar/fiscalizar**: edita cualquiera de los campos de la clave (caso, producto, cliente, colaborador, fecha de ocurrencia o reclamo) para lanzar la validación; verifica que el resumen de clave muestre `-` en componentes omitidos y que los duplicados se reporten aun cuando falte uno de los dos identificadores.

## FAQ
- **¿Cómo reinicio el formulario?** Usa **Acciones → Borrar todos los datos**.
- **¿Puedo pegar datos desde Excel?** Sí, en la pestaña **Resumen**.
- **¿Qué pasa si no instalo `python-docx`?** El flujo sigue; sólo se omite el informe Word.
- **¿Se guardan versiones temporales?** Sí, cada edición genera JSON temporales en la raíz y en `external drive/<id_caso>/`.

## Pruebas
Para verificar rutas críticas de guardado/exportación/logs con cobertura focalizada:
```bash
pytest --cov=app --cov=ui --cov=models --cov-report=term-missing
```
Asegúrate de contar con `python-docx`, `pytest` y `pytest-cov`, y con la carpeta `external drive/` accesible.

Para probar la restauración completa del formulario y la generación de reportes con datos válidos según las reglas del design doc, carga el fixture `tests/fixtures/test-save.json` desde **Acciones → Cargar formulario**; luego usa **Guardar y enviar** para producir los CSV/JSON/Markdown/Word de ejemplo.

## Contribución y licencia
Las contribuciones son bienvenidas mediante issues o PRs. No hay licencia declarada; úsese bajo su propio criterio.
