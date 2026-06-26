[Español](README.md) · **English**

# acta-pipeline-local

Automatic generation of **homeowners' association meeting minutes** ("actas") from the
**audio** of the meeting, running **100% locally** (no cloud). Built for sensitive
resident data that must not leave the machine for an external API.

From the recordings (`.m4a`/`.mp3`/`.wav`) and the scanned attendance sheet (`.pdf`),
it produces a **draft of the minutes in `.docx`** following the format of a reference
document, flagging the data that requires human validation.

## Pipeline

```
Audio .m4a ──┐
             ├─> [WhisperX] transcription + diarization ──┐
Attendance PDF ─> [OCR + ink] roster + attendance ────────┼─> [Local LLM] drafting ─> Minutes .docx
Minutes data (JSON, provided by a human) ─────────────────┘            (human review)
```

- **Transcription + speakers:** WhisperX (faster-whisper `large-v3` int8 + pyannote).
- **Drafting:** Ollama + a local model (e.g. Qwen 2.5 7B), *pluggable* architecture.
- **Attendance roster:** EasyOCR + PyMuPDF; attendance is inferred from ink density.
- **Export:** python-docx.
- **Base:** PyTorch + CUDA, ffmpeg.

## Engineering decisions (real problems solved)

- **VRAM constraint (6 GB):** the pipeline runs in **sequential stages**; each model frees
  its memory before the next one loads. Two models are never on the GPU at the same time.
- **Hallucination in a legal document:** the LLM **does not write the header** (date, place,
  tax id, etc.) — the human provides that in `datos_acta.json`. Strict prompt rules prevent
  inventing figures and forbid "unanimously" when there were votes against.
- **Long transcript vs. small context window:** **map-reduce** generation by chunks.
- **Traceability over identity:** instead of guessing speaker names, every paragraph is
  anchored to `[session, timestamp]` via deterministic post-processing, so human review can
  verify the real speaker against the audio.
- **Attendance is not text:** a handwritten signature can't be "read"; the **ink** of each
  row's handwritten region is measured to infer attended (1/0), with a confidence level.

## Requirements

- Python 3.11, NVIDIA GPU (tested on RTX 4050, 6 GB) — also works on CPU, slower.
- [ffmpeg](https://ffmpeg.org/) on `PATH` (or in `tools/ffmpeg/bin`).
- [Ollama](https://ollama.com/) with a downloaded model (`ollama pull qwen2.5:7b-instruct`).
- A Hugging Face token for diarization (see `.env.example`).

## Installation

```bash
python -m venv venv && source venv/Scripts/activate   # Windows: venv\Scripts\activate
# PyTorch with CUDA (match the index to your CUDA version):
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt

cp .env.example .env                          # paste your HF_TOKEN
cp datos_acta.example.json datos_acta.json    # fill in the minutes data
```

Place your input files in `data/` and reference their names in `datos_acta.json`
(the `entrada` block).

## Usage

```bash
# 1. Transcribe + diarize each audio (creates output/transcripciones/*.txt)
python src/transcribe.py "data/sesion1.m4a"

# 2. OCR the attendance sheet + attendance detection (output/padron.csv)
python src/ocr_asistencia.py

# 3. Generate the minutes draft (output/acta_borrador.txt)
python src/pipeline.py

# 4. Export to Word (output/Acta.docx)
python src/exportar_docx.py
```

## Layout

```
acta-pipeline-local/
  src/
    config.py          paths, models, loads datos_acta.json and .env
    transcribe.py      WhisperX: audio -> transcription + diarization
    ocr_asistencia.py  EasyOCR + ink detection -> padron.csv
    generar_acta.py    "secretary" prompt + single-chunk test
    pipeline.py        map-reduce -> minutes draft with traceability
    exportar_docx.py   assembles the final .docx
    encabezado.py      builds the opening block from datos_acta.json
    llm.py             Ollama client (pluggable)
  datos_acta.example.json   minutes-data template (copy to datos_acta.json)
  .env.example              env-vars template (HF_TOKEN)
  requirements.txt
```

## Privacy

This repository **contains no real data**: audio, PDFs, reference documents, the real
`datos_acta.json` and the whole `output/` folder are excluded via `.gitignore`. The code is
a starting point; sensitive data always stays local.

## Dependency licenses

The code in this repo is permissively licensed (see below), but dependencies carry their own
licenses — mostly permissive (BSD/MIT/Apache-2.0). Note: **PyMuPDF is AGPL-3.0** (copyleft).
That is fine for an open-source project; if you build a closed commercial product, consider
swapping PyMuPDF for `pypdfium2` (permissive) for PDF rendering. Diarization models
(pyannote) are gated and have their own terms — review them for your use case.

## Status

End-to-end functional (audio → `.docx` minutes). Pending: API/UI (FastAPI), better table
segmentation for heavily-marked PDFs, and packaging.

## License

MIT — see [LICENSE](LICENSE).
