# Configuración LLM local (checkpoint en `external drive`) y guía operativa

## 1) Dónde está conectado el LLM en el proyecto

- **Auto-redacción en la pestaña “Análisis y narrativas”**: `utils/auto_redaccion.py` y `app.py`.
- **Generación de Alerta Temprana (.pptx)**: `report/alerta_temprana.py` vía `build_alerta_temprana_ppt(...)`.
- **Generación de Resumen Ejecutivo (.md)**: `report/resumen_ejecutivo.py` vía `build_resumen_ejecutivo_md(...)`.

El helper central es `SpanishSummaryHelper`, que ahora:
1. Prioriza modelo local por variable de entorno `LOCAL_SUMMARY_MODEL_DIR`.
2. Si no está definida, busca el checkpoint en `external drive`.
3. Carga tokenizer y modelo con `local_files_only=True` (sin descargar del Hub).

---

## 2) Paso a paso para descargar y dejar el checkpoint operativo

### Paso 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### Paso 2. Descargar el checkpoint de Hugging Face en local

Modelo objetivo:
- `mrm8488/bert2bert_shared-spanish-finetuned-summarization`

Ejemplo con `huggingface_hub` (en tu máquina local):

```bash
python - <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="mrm8488/bert2bert_shared-spanish-finetuned-summarization",
    local_dir="external drive/mrm8488/bert2bert_shared-spanish-finetuned-summarization",
    local_dir_use_symlinks=False,
)
print("Checkpoint descargado.")
PY
```

### Paso 3. Validar estructura mínima esperada

En la carpeta del modelo debe haber archivos como:
- `config.json`
- `tokenizer_config.json`
- `special_tokens_map.json`
- pesos del modelo (`pytorch_model.bin` o `model.safetensors`)

### Paso 4. (Opcional recomendado) Fijar ruta explícita

```bash
export LOCAL_SUMMARY_MODEL_DIR="/ruta/absoluta/a/external drive/mrm8488/bert2bert_shared-spanish-finetuned-summarization"
```

### Paso 5. Probar el script CLI local

```bash
python tools/local_spanish_summarizer.py --input_file docs/sample_eventos.csv --max_len 120 --min_len 40
```

> Nota: para prueba real, usa un `.txt` con narrativa; el comando anterior ilustra solo la ejecución.

### Paso 6. Probar flujo en UI

1. Abrir app.
2. Ir a **Análisis y narrativas**.
3. Completar antecedentes/hallazgos/conclusiones.
4. Pulsar **Auto-redactar** en comentario breve/amplio.
5. Ir a **Acciones**:
   - **Generar alerta temprana (.pptx)**
   - **Generar resumen ejecutivo**

---

## 3) Robustez y reintentos implementados

Para reducir salidas erráticas (repeticiones, loops, texto sin sentido):

- El helper LLM usa **múltiples intentos** con parámetros anti-repetición (`repetition_penalty`, `no_repeat_ngram_size`, `num_beams`).
- Se detecta salida degenerada (n-gramas repetidos o texto demasiado pobre) y se reintenta.
- Si todos los intentos fallan, se retorna fallback seguro en cada flujo.

Esto aplica tanto para:
- secciones de Alerta Temprana,
- refinamiento opcional de secciones en Resumen Ejecutivo,
- y el CLI local `tools/local_spanish_summarizer.py`.

---

## 4) Checklist de diagnóstico rápido

1. ¿Existe `external drive`?
2. ¿Existe el subdirectorio del modelo?
3. ¿El modelo contiene tokenizer + pesos?
4. ¿`transformers` y `torch` instalados?
5. ¿`LOCAL_SUMMARY_MODEL_DIR` apunta a una carpeta válida?
6. ¿El log muestra fallback por salida degenerada o error de runtime?

---

## 5) Relación con validaciones del formulario (Design document CM.pdf)

Las reglas de validación de negocio (fechas, montos, IDs, duplicados) se mantienen en el pipeline de validación y **no dependen del LLM**. El LLM sólo asiste redacción narrativa y exportes textuales; no sustituye controles de datos ni reglas de consistencia.
