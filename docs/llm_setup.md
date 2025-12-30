# LLM implementation overview and local Hugging Face checkpoint setup

## Scope and intent
This document walks through how large language models (LLMs) are wired in this codebase and provides a step-by-step manual for using a **local, pretrained Hugging Face checkpoint** when running the app from a cloned repository. It also references the **Design document CM.pdf** to confirm that LLM usage is separate from the validation rules described there (see “Validation context”).

## Where LLMs are implemented
### 1) Report summarization for the “Alerta temprana” PPT
**File:** `report/alerta_temprana.py`

**Key class:** `SpanishSummaryHelper`
- Uses `transformers` to build a `text2text-generation` pipeline.
- Loads the model and tokenizer via `AutoModelForSeq2SeqLM.from_pretrained()` and `AutoTokenizer.from_pretrained()`.
- Caches generated summaries by `(section, prompt, max_new_tokens)` to avoid repeated calls.

**Default model:**
- `DEFAULT_MODEL = "PlanTL-GOB-ES/flan-t5-base-spanish"`

**How it is used:**
- `_synthesize_section_text(...)` builds a prompt and tries to call `SpanishSummaryHelper.summarize(...)`.
- If the LLM is unavailable or fails, it falls back to deterministic, data-driven summaries.
- `build_alerta_temprana_ppt(...)` instantiates `SpanishSummaryHelper()` by default and uses it to generate multiple sections: Resumen, Cronología, Análisis, etc.

### 2) Auto-redacción in the UI
**File:** `utils/auto_redaccion.py`

**Key function:** `auto_redact_comment(...)`
- Builds a prompt from case data and the narrative sections.
- Uses a shared `SpanishSummaryHelper` instance (lazy-loaded) to generate a summary.
- Sanitizes PII with regex patterns and enforces maximum length.

**Where it is triggered:**
**File:** `app.py`
- `FraudCaseApp._auto_redact_commentary(...)` collects narrative fields and calls `auto_redact_comment(...)`.
- The result is placed into the rich-text widget for “Comentario breve” or “Comentario amplio”.

## Local Hugging Face checkpoint setup (step-by-step)
### Step 1: Install dependencies
Ensure `transformers` and a compatible PyTorch build are available.

```bash
pip install -r requirements.txt
# If torch is missing, install a CPU or CUDA build:
# pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**Why:** `SpanishSummaryHelper` checks for `transformers` at runtime. Without it, LLM features fall back to placeholders.

### Step 2: Download a pretrained Hugging Face checkpoint locally
Choose a model compatible with `text2text-generation` (e.g., a T5/FLAN-based model).

**Recommended approach (Python):**
```bash
python - <<'PY'
from huggingface_hub import snapshot_download

model_id = "PlanTL-GOB-ES/flan-t5-base-spanish"  # replace with your chosen model
local_dir = "models/hf/flan-t5-base-spanish"      # pick any local folder
snapshot_download(repo_id=model_id, local_dir=local_dir, local_dir_use_symlinks=False)
print(f"Downloaded to: {local_dir}")
PY
```

**Result:** A local folder with `config.json`, `tokenizer.json`, model weights, etc.

### Step 3: Store the checkpoint in a predictable location
Place the model under the repository (example path):

```
/workspace/Formulario_investigacion/models/hf/flan-t5-base-spanish
```

Any location is fine as long as you provide the **absolute or relative path** to `from_pretrained(...)`.

### Step 4: Point the app to the local checkpoint
There are two main options:

#### Option A — Update the default model path (applies to all LLM usage)
**Edit:** `report/alerta_temprana.py`

Change:
```python
DEFAULT_MODEL = "PlanTL-GOB-ES/flan-t5-base-spanish"
```

To:
```python
DEFAULT_MODEL = "models/hf/flan-t5-base-spanish"
```

This will make **both**:
- `build_alerta_temprana_ppt(...)`
- `auto_redact_comment(...)`

load from the local checkpoint (because they use `SpanishSummaryHelper()` with defaults).

#### Option B — Instantiate `SpanishSummaryHelper` with a custom path
If you prefer not to change `DEFAULT_MODEL`, instantiate the helper with a path and pass it explicitly.

**Example usage (PPT builder):**
```python
from report.alerta_temprana import SpanishSummaryHelper, build_alerta_temprana_ppt

llm = SpanishSummaryHelper(model_name="models/hf/flan-t5-base-spanish")
build_alerta_temprana_ppt(data, output_path, llm_helper=llm)
```

**Example usage (auto-redacción):**
```python
from utils.auto_redaccion import auto_redact_comment
from report.alerta_temprana import SpanishSummaryHelper

llm = SpanishSummaryHelper(model_name="models/hf/flan-t5-base-spanish")
result = auto_redact_comment(case_data, narrative, target_chars=400, label="breve", helper=llm)
```

> Note: The UI currently calls `auto_redact_comment(...)` without a helper, so to use Option B inside the app you would wire a custom helper in `FraudCaseApp._auto_redact_commentary(...)`.

### Step 5: Run the app and verify LLM behavior
- Generate “Auto-redacción” in the UI (Comentario breve/amplio).
- Export the “Alerta temprana” PPT and check that sections are summarized.

If `transformers` is missing or a model fails to load, the app falls back to placeholders and deterministic summaries.

## Model selection guidance
- The code expects a **Seq2Seq** model compatible with `text2text-generation`.
- For Spanish summarization, consider T5/FLAN models trained or tuned for Spanish.
- Keep prompts under reasonable length; `SpanishSummaryHelper.max_new_tokens` defaults to `144` and can be adjusted.

## Validation context (Design document CM.pdf)
Per **Design document CM.pdf**, the app enforces strict validation rules (dates, IDs, amounts, and duplicate prevention). The LLM features described above **do not bypass** those validations:
- Validation utilities are centralized (e.g., `validators.py` and related tests).
- LLM output is used for narrative/summary fields only and is cleaned to remove PII.

This separation ensures that the required format validations remain in place while enabling optional AI-assisted summaries.

## Quick checklist
- [ ] `transformers` installed
- [ ] Local model checkpoint downloaded
- [ ] `DEFAULT_MODEL` updated **or** `SpanishSummaryHelper(model_name=...)` passed explicitly
- [ ] App successfully generates auto-redacción and/or PPT summaries
