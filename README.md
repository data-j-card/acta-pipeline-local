**Español** · [English](README.en.md)

# acta-pipeline-local

Generación automática de **actas de asamblea de propiedad horizontal** a partir de los
**audios** de la reunión, ejecutándose **100 % en local** (sin nube). Pensado para datos
sensibles de copropietarios que no deben salir a una API externa.

A partir de las grabaciones (`.m4a`/`.mp3`/`.wav`) y del listado de asistencia escaneado
(`.pdf`), produce un **borrador de acta en `.docx`** con el mismo formato de un acta de
referencia, dejando marcados los datos que requieren validación humana.

## Pipeline

```
Audios .m4a ─┐
             ├─> [WhisperX] transcripción + diarización ─┐
PDF asistencia ─> [OCR + tinta] padrón + asistencia ─────┼─> [LLM Ollama] redacción ─> Acta .docx
Datos del acta (JSON, provistos por el humano) ──────────┘            (revisión humana)
```

- **Transcripción + hablantes:** WhisperX (faster-whisper `large-v3` int8 + pyannote).
- **Redacción del acta:** Ollama + un modelo local (p. ej. Qwen 2.5 7B), arquitectura *pluggable*.
- **Padrón de asistencia:** EasyOCR + PyMuPDF; la asistencia se infiere por densidad de tinta.
- **Exportación:** python-docx.
- **Base:** PyTorch + CUDA, ffmpeg.

## Decisiones de ingeniería (problemas reales resueltos)

- **Restricción de VRAM (6 GB):** el pipeline corre por **etapas secuenciales**; cada modelo
  libera la memoria antes de que cargue el siguiente. Nunca hay dos modelos en GPU a la vez.
- **Alucinación en un documento legal:** el LLM **no escribe el encabezado** (fecha, lugar,
  NIT, etc.) — eso lo provee el humano en `datos_acta.json`. Reglas estrictas en el prompt
  evitan inventar cifras y prohíben "por unanimidad" cuando hubo votos en contra.
- **Transcripción larga vs. ventana de contexto pequeña:** generación **map-reduce** por trozos.
- **Trazabilidad sobre identidad:** en vez de adivinar nombres de hablantes, cada párrafo del
  acta queda anclado a `[sesión, marca de tiempo]` mediante post-proceso determinístico, para
  que la revisión humana valide al hablante real contra el audio.
- **Asistencia no es texto:** una firma manuscrita no se "lee"; se mide la **tinta** de la
  región manuscrita de cada fila para inferir asistió (1/0), con un nivel de confianza.

## Requisitos

- Python 3.11, GPU NVIDIA (probado en RTX 4050, 6 GB) — funciona en CPU, más lento.
- [ffmpeg](https://ffmpeg.org/) en el `PATH` (o en `tools/ffmpeg/bin`).
- [Ollama](https://ollama.com/) con un modelo descargado (`ollama pull qwen2.5:7b-instruct`).
- Token de Hugging Face para la diarización (ver `.env.example`).

## Instalación

```bash
python -m venv venv && source venv/Scripts/activate   # Windows: venv\Scripts\activate
# PyTorch con CUDA (ajusta el indice a tu version de CUDA):
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt

cp .env.example .env                  # y pega tu HF_TOKEN
cp datos_acta.example.json datos_acta.json   # y completa los datos del acta
```

Coloca tus archivos de entrada en `data/` y referencia sus nombres en `datos_acta.json`
(bloque `entrada`).

## Uso

```bash
# 1. Transcribir + diarizar cada audio (genera output/transcripciones/*.txt)
python src/transcribe.py "data/sesion1.m4a"

# 2. OCR del padron de asistencia + deteccion de asistencia (output/padron.csv)
python src/ocr_asistencia.py

# 3. Generar el borrador del acta (output/acta_borrador.txt)
python src/pipeline.py

# 4. Exportar a Word (output/Acta.docx)
python src/exportar_docx.py
```

## Estructura

```
acta-pipeline-local/
  src/
    config.py          rutas, modelos, carga de datos_acta.json y .env
    transcribe.py      WhisperX: audio -> transcripcion + diarizacion
    ocr_asistencia.py  EasyOCR + deteccion de tinta -> padron.csv
    generar_acta.py    prompt del "secretario" + prueba de un fragmento
    pipeline.py        map-reduce -> borrador del acta con trazabilidad
    exportar_docx.py   ensambla el .docx final
    encabezado.py      arma el bloque de apertura desde datos_acta.json
    llm.py             cliente de Ollama (pluggable)
  datos_acta.example.json   plantilla de datos del acta (copiar a datos_acta.json)
  .env.example              plantilla de variables (HF_TOKEN)
  requirements.txt
```

## Privacidad

Este repositorio **no incluye datos reales**: audios, PDFs, actas de referencia, el
`datos_acta.json` real y todo `output/` están excluidos por `.gitignore`. El código es un
punto de partida; los datos sensibles permanecen siempre en local.

## Licencias de dependencias

El código de este repo lleva licencia permisiva (ver abajo), pero cada dependencia tiene la
suya — en su mayoría permisivas (BSD/MIT/Apache-2.0). Nota: **PyMuPDF es AGPL-3.0** (copyleft).
Para un proyecto open-source no hay problema; si construyes un producto comercial cerrado,
considera cambiar PyMuPDF por `pypdfium2` (permisiva) para el render del PDF. Los modelos de
diarización (pyannote) son "gated" y tienen sus propios términos — revísalos para tu caso.

## Estado

Funcional de extremo a extremo (audio → acta `.docx`). Pendiente: API/UI (FastAPI),
mejor segmentación de la tabla en PDFs muy marcados, y empaquetado.

## Licencia

MIT — ver [LICENSE](LICENSE).
