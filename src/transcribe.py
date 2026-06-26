"""
Transcripcion + diarizacion de audios de asamblea con WhisperX.

Uso:
    # Prueba rapida: primeros 5 min del audio 1
    python src/transcribe.py "data/sesion1.m4a" --sample 300

    # Completo (con diarizacion, requiere HF_TOKEN en el entorno)
    python src/transcribe.py "data/sesion1.m4a"

Salida: JSON + TXT legible en output/transcripciones/
"""
import argparse
import gc
import json
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import config


def _hms(seconds: float) -> str:
    return str(timedelta(seconds=int(seconds)))


def make_sample(src: Path, seconds: int) -> Path:
    """Recorta los primeros N segundos a un wav 16kHz mono para pruebas rapidas."""
    out = config.TRANSCRIPT_DIR / f"_sample_{seconds}s_{src.stem}.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(src), "-t", str(seconds),
        "-ac", "1", "-ar", "16000", str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def transcribe(audio_path: Path, diarize: bool, sample: int | None):
    import torch
    import whisperx

    config.ensure_ffmpeg_on_path()

    src = audio_path
    if sample:
        print(f"[1/5] Recortando muestra de {sample}s con ffmpeg...")
        src = make_sample(audio_path, sample)

    device = config.DEVICE if torch.cuda.is_available() else "cpu"
    compute = config.COMPUTE_TYPE if device == "cuda" else "int8"
    print(f"[2/5] Cargando modelo Whisper {config.WHISPER_MODEL} ({compute}) en {device}...")
    model = whisperx.load_model(
        config.WHISPER_MODEL, device, compute_type=compute, language=config.LANGUAGE,
        asr_options={"initial_prompt": config.INITIAL_PROMPT},
    )

    audio = whisperx.load_audio(str(src))
    print(f"[3/5] Transcribiendo ({_hms(len(audio)/16000)} de audio)...")
    result = model.transcribe(audio, batch_size=config.BATCH_SIZE, language=config.LANGUAGE)
    del model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    print("[4/5] Alineando palabras con tiempos...")
    model_a, metadata = whisperx.load_align_model(language_code=config.LANGUAGE, device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device,
                            return_char_alignments=False)
    del model_a
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    if diarize:
        if not config.HF_TOKEN:
            print("  ! HF_TOKEN no configurado: se omite diarizacion. "
                  "Define $env:HF_TOKEN para identificar hablantes.")
        else:
            print("[5/5] Diarizando (identificando hablantes)...")
            try:
                from whisperx.diarize import DiarizationPipeline
            except ImportError:
                from whisperx import DiarizationPipeline
            diarizer = DiarizationPipeline(token=config.HF_TOKEN, device=device)
            diarize_segments = diarizer(audio)
            result = whisperx.assign_word_speakers(diarize_segments, result)

    return result, src


def save(result, audio_path: Path, src: Path):
    config.TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    stem = src.stem
    json_path = config.TRANSCRIPT_DIR / f"{stem}.json"
    txt_path = config.TRANSCRIPT_DIR / f"{stem}.txt"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    with open(txt_path, "w", encoding="utf-8") as f:
        for seg in result["segments"]:
            ts = _hms(seg.get("start", 0))
            spk = seg.get("speaker", "")
            spk = f"[{spk}] " if spk else ""
            f.write(f"({ts}) {spk}{seg['text'].strip()}\n")

    print(f"\n  JSON -> {json_path}")
    print(f"  TXT  -> {txt_path}")
    return txt_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", help="ruta del audio (.m4a)")
    ap.add_argument("--sample", type=int, default=None,
                    help="solo transcribir los primeros N segundos (prueba rapida)")
    ap.add_argument("--no-diarize", action="store_true", help="omitir identificacion de hablantes")
    args = ap.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.is_absolute():
        audio_path = config.BASE_DIR / audio_path
    if not audio_path.exists():
        sys.exit(f"No existe el audio: {audio_path}")

    result, src = transcribe(audio_path, diarize=not args.no_diarize, sample=args.sample)
    txt = save(result, audio_path, src)

    print("\n--- Primeras lineas ---")
    print("\n".join(Path(txt).read_text(encoding="utf-8").splitlines()[:12]))


if __name__ == "__main__":
    main()
