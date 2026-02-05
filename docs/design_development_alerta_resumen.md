# Design Development: Alerta Temprana y Resumen Ejecutivo

## 1) Contexto y objetivo

Este documento aterriza el feedback de la entrevista de usuarios para la generación de dos láminas:

1. **Resumen ejecutivo**
2. **Alerta temprana**

El objetivo funcional es que el contenido deje de ser solo un “jale de texto” y pase a ser una síntesis orientada a:

- qué pasó,
- cuál fue el hallazgo principal,
- qué **falla de control/proceso** explica el caso,
- cuál es el impacto (montos, productos, clientes),
- qué acciones/recomendaciones inmediatas deben ejecutarse,
- quiénes son responsables del seguimiento.

## 2) Hallazgos de entrevista (síntesis operativa)

A partir de la conversación grabada, se consolidan requerimientos de contenido:

- El mensaje debe priorizar **fallas de control/proceso** y no centrarse en personas.
- En resumen y mensaje clave se espera visibilidad de:
  - modalidad/modus operandi,
  - impacto monetario,
  - cantidad de productos/clientes afectados.
- En análisis se espera presentar el **hallazgo principal** que dispara la alerta.
- “Acciones inmediatas” debe converger a **recomendaciones** (sugerencias accionables).
- Responsables deben mapearse a unidades/dueños de producto/proceso cuando exista información.
- Cada sección debe poder rastrearse a campos del formulario.

## 3) Especificación de contenido por sección

## 3.1 Resumen ejecutivo (lámina 1)

### Encabezado
- Título: “Resumen ejecutivo · Alerta temprana”
- Identificación del caso: `id_caso`
- Emisor: `investigador_nombre`

### Mensaje clave
- Fuente principal: `analisis.comentario_breve`
- Fallback: `analisis.hallazgos`
- Enfoque: síntesis ejecutiva del caso + falla principal de control/proceso
- Extensión recomendada para IA: **35–60 palabras** si se modela como sección puntual, o 80–120 en versión narrativa general.

### Puntos de soporte
- Montos agregados desde productos:
  - `monto_investigado`
  - `monto_perdida_fraude`
  - `monto_falla_procesos`
  - `monto_contingencia`
  - `monto_recuperado`
- Conteos:
  - total productos
  - total clientes
- Debe evitar duplicar literal del mensaje clave.

### Evidencia / trazabilidad
- Fechas del caso:
  - `fecha_de_ocurrencia`
  - `fecha_de_descubrimiento`
- Metadatos de encabezado:
  - `encabezado.dirigido_a`
  - `encabezado.area_reporte`
- Recomendación: mantener referencias de origen en formato `[Tabla/Campo]`.

## 3.2 Alerta temprana (lámina 2)

### Resumen
- Fuente: síntesis breve de `comentario_breve`, `hallazgos`, y contexto del caso.
- Debe responder “qué pasó” + impacto.
- Extensión recomendada IA: **80–120 palabras**.

### Cronología
- Prioridad 1: bullets derivados de `analisis.hallazgos`/`comentario_breve`/`conclusiones`.
- Prioridad 2: `operaciones` ordenadas por fecha.
- Prioridad 3: fechas mínimas de ocurrencia/descubrimiento y fechas de producto.
- Extensión recomendada IA: **90–130 palabras**.

### Análisis
- Debe iniciar con hallazgo principal y explicitar falla de control/proceso.
- Fuentes:
  - `hallazgos`
  - `conclusiones`
  - `antecedentes`
  - `modus_operandi`
  - `comentario_amplio`
- Extensión recomendada IA: **110–170 palabras**.

### Riesgos identificados
- Fuente: registros en `riesgos` (`id_riesgo`, `descripcion`, `criticidad`, `planes_accion`).
- Enfoque: impacto y exposición operacional.
- Extensión recomendada IA: **70–110 palabras**.

### Recomendaciones (renombrado sugerido)
- Mantener título como **Recomendaciones** (en lugar de “Acciones inmediatas”) según feedback.
- Fuente primaria: `analisis.recomendaciones`.
- Fallback: `analisis.acciones` o tabla `operaciones`.
- Extensión recomendada IA: **70–110 palabras**.

### Responsables
- Fuentes:
  - responsables explícitos, si existen,
  - `colaboradores` como fallback contextual,
  - investigador como último fallback.
- Enfoque: dueño de producto/proceso o unidad responsable, no juicio personal.
- Extensión recomendada IA: **55–90 palabras**.

## 4) Cambios funcionales propuestos (prompting)

1. Incluir instrucción explícita en el prompt: **“Enfócate en fallas de control/proceso”**.
2. Incluir marco de la entrevista en la instrucción base del LLM (qué pasó, hallazgo principal, control fallido, impacto y recomendaciones).
3. Definir límites de palabras por sección para reducir sobrelongitud y mejorar consistencia.
4. Definir presupuesto de `max_new_tokens` por sección (mensaje corto vs análisis largo).

## 5) Validaciones de implementación

- Pruebas unitarias de prompt:
  - verificar presencia literal del enfoque control/proceso,
  - verificar presencia de objetivos de entrevista,
  - verificar rango de palabras por sección.
- Pruebas de síntesis:
  - verificar que se usa presupuesto de tokens distinto por sección.

## 6) Riesgos y mitigaciones

- **Riesgo:** prompt demasiado largo y verboso.
  - **Mitigación:** límites por sección + fallback determinístico existente.
- **Riesgo:** sobreajuste a una redacción fija.
  - **Mitigación:** mantener contexto factual dinámico por caso.
- **Riesgo:** inconsistencias entre secciones.
  - **Mitigación:** instrucción explícita para evitar repeticiones + cobertura de tests.

## 7) Próximos pasos recomendados

1. Incorporar guía de “renombre de secciones” a nivel de plantillas/UX con validación de negocio.
2. Añadir snapshots de prompts por sección para detectar regresiones semánticas.
3. Medir longitud promedio real de salida y ajustar `max_new_tokens` por distribución observada.
