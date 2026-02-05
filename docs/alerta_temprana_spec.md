# Especificación de contenido: Alerta Temprana y Resumen Ejecutivo

Este documento describe el mapeo **campo → narrativa → texto de slides** para la presentación de Alerta Temprana y el nuevo **Resumen Ejecutivo**. Todas las secciones se construyen con plantillas determinísticas; si un campo no está disponible se muestra **N/A**.

## Fuentes de datos (tabs)
| Fuente | Campos clave | Uso |
| --- | --- | --- |
| Caso | `id_caso`, `tipo_informe`, `categoria1`, `modalidad`, `canal`, `proceso`, `fecha_de_ocurrencia`, `fecha_de_descubrimiento`, `investigador_nombre` | Carátula y contexto |
| Encabezado (Informe de Gerencia) | `referencia`, `dirigido_a`, `area_reporte` | Título/caso y trazabilidad |
| Análisis y narrativa | `antecedentes`, `modus_operandi`, `hallazgos`, `conclusiones`, `recomendaciones`, `comentario_breve`, `comentario_amplio` | Resumen, cronología y análisis |
| Productos | `monto_*`, `fecha_ocurrencia` | Impacto y fechas |
| Riesgos | `id_riesgo`, `descripcion`, `criticidad`, `planes_accion` | Riesgos identificados |
| Operaciones | `accion`, `estado`, `fecha`, `cliente` | Cronología/recomendaciones (fallback) |
| Colaboradores | `nombres`, `flag`, `area` | Responsables |
| Clientes | `id_cliente` | Evidencia (conteo) |
| Reclamos | `id_reclamo` | Evidencia (conteo) |

## Reglas de fallback (globales)
1. Si un campo está vacío → **N/A**.
2. Texto largo → truncar con “…” (máx. 600 caracteres por sección).
3. Secciones con bullets → máx. 5 viñetas (máx. 180–200 caracteres por viñeta).

## Alerta Temprana (PPT)
### Slide 1: Resumen Ejecutivo
**Título estándar:** “Resumen ejecutivo · Alerta temprana”  
**Secciones:**
1. **Mensaje clave**  
   - **Plantilla:** `Caso <id_caso> - <referencia/categoría-modalidad-proceso-canal>. Monto investigado <total>…`  
   - **Campos:** `caso.id_caso`, `encabezado.referencia`, `caso.categoria1`, `caso.modalidad`, `caso.proceso`, `caso.canal`, montos agregados de productos.
2. **Puntos de soporte (3–5)**  
   - **Plantilla:**  
     - “Hallazgos clave: <hallazgos>”  
     - “Riesgos identificados: <riesgos>”  
     - “Recomendaciones en curso: <recomendaciones/operaciones>”  
     - “Responsables asignados: <investigador + colaboradores>”  
   - **Campos:** `analisis.hallazgos`, `riesgos`, `analisis.recomendaciones`, `operaciones`, `caso.investigador_nombre`, `colaboradores`.
3. **Evidencia / trazabilidad**  
   - **Plantilla:** Conteos + fechas clave + dirigido a/área de reporte.  
   - **Campos:** `len(productos/clientes/colaboradores/riesgos/reclamos)`, `fecha_de_ocurrencia`, `fecha_de_descubrimiento`, `encabezado.dirigido_a`, `encabezado.area_reporte`.

### Slide 2: Alerta Temprana (layout 2 columnas)
**Masthead (banner):**
| Campo | Plantilla |
| --- | --- |
| Título | “Reporte de Alertas Tempranas por Casos de Fraude” |
| Código | `Código: <id_caso>` |
| Caso | `Caso: <referencia/categoría-modalidad-proceso-canal>` |
| Emitido por | `Emitido por: <investigador_nombre>` |

**Resumen:**  
Plantilla: `<referencia/categoría…>. <comentario_breve/conclusiones/antecedentes>. Montos agregados investigado, pérdida, contingencia, recuperado.`  
Campos: `encabezado.referencia`, `analisis.comentario_breve`, `analisis.conclusiones`, `analisis.antecedentes`, montos en `productos`.

**Cronología:**  
Plantilla: bullets desde `analisis.hallazgos` (si existe).  
Fallback: bullets desde `operaciones` (`fecha - acción - estado`) o fechas de caso/productos.  

**Análisis:**  
Plantilla: bullets “Antecedentes: …”, “Modus operandi: …”, “Conclusiones: …”.  
Fallback: `comentario_amplio`.

**Riesgos identificados:**  
Plantilla: `id_riesgo - descripcion - criticidad - Plan: planes_accion` (si existe).  

**Recomendaciones:**  
Plantilla: `analisis.recomendaciones` (bullets).  
Fallback: `operaciones` (acción/cliente/estado).

**Responsables:**  
Plantilla: Investigador + colaboradores (flag/área).

## Resumen Ejecutivo (Markdown export)
**Estructura (piramidal):**
1. **Mensaje clave:** síntesis única del caso (ID + referencia + impacto).  
2. **Puntos de soporte (3–5):** hallazgos, riesgos, acciones, responsables, resumen ejecutivo.  
3. **Evidencia / trazabilidad:** métricas (conteos, fechas, dirigido a, área reporte).  

**Reglas de armado:**
- Máx. 5 bullets por sección; truncar con “…” si excede 260 caracteres.
- No inventar datos: si un bloque no tiene origen, se muestra **N/A**.
