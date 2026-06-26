"""Configuracion central del proyecto."""
from pathlib import Path
import json
import os

try:  # carga opcional de un archivo .env (ver .env.example)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

# --- Rutas del proyecto ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"                # audios + pdf + acta de referencia (no versionado)
OUTPUT_DIR = BASE_DIR / "output"
TRANSCRIPT_DIR = OUTPUT_DIR / "transcripciones"
TOOLS_DIR = BASE_DIR / "tools"

# Datos del acta y archivos de entrada (NO versionado, ver datos_acta.example.json)
DATOS_FILE = BASE_DIR / "datos_acta.json"

# ffmpeg portatil (se agrega al PATH en runtime si existe)
FFMPEG_DIR = TOOLS_DIR / "ffmpeg" / "bin"

# --- Modelos (ajustados a RTX 4050, 6 GB VRAM) ---
WHISPER_MODEL = "large-v3"      # baja a "medium" si falta VRAM
COMPUTE_TYPE = "int8"           # int8 cabe en 6 GB; "float16" si sobra memoria
DEVICE = "cuda"
BATCH_SIZE = 4                  # bajo para no desbordar 6 GB
LANGUAGE = "es"

# Prompt de vocabulario del dominio: orienta a Whisper hacia los terminos
# correctos de una asamblea de propiedad horizontal (evita "coro" -> "quorum", etc.)
INITIAL_PROMPT = (
    "Asamblea general de copropietarios de propiedad horizontal. Terminos frecuentes: "
    "quorum, coeficiente de copropiedad, copropietarios, condominos, poderes, "
    "Ley 675 de 2001, consejo de administracion, comite de convivencia, administradora, "
    "presidente y secretario de la asamblea, comision verificadora del acta, "
    "reglamento de debate, orden del dia, votacion, aprobado por unanimidad, "
    "expensas comunes, fondo de imprevistos."
)

# Token de Hugging Face para diarizacion (pyannote). Definir en .env o variable de
# entorno HF_TOKEN. Crear en https://huggingface.co/settings/tokens y aceptar la
# licencia del modelo de diarizacion que use tu version de WhisperX.
HF_TOKEN = os.environ.get("HF_TOKEN", "")


def datos() -> dict:
    """Carga datos_acta.json (encabezado + archivos de entrada). {} si no existe."""
    if DATOS_FILE.exists():
        return json.loads(DATOS_FILE.read_text(encoding="utf-8"))
    return {}


def _entrada() -> dict:
    return datos().get("entrada", {})


def audios() -> list[str]:
    """Nombres de los audios (en DATA_DIR), en orden cronologico de sesiones."""
    return _entrada().get("audios", ["sesion1.m4a", "sesion2.m4a"])


def pdf_asistencia() -> Path:
    return DATA_DIR / _entrada().get("pdf_asistencia", "listado_asistencia.pdf")


def acta_referencia() -> Path:
    return DATA_DIR / _entrada().get("acta_referencia", "acta_referencia.docx")


def transcript_path(audio_name: str) -> Path:
    return TRANSCRIPT_DIR / (Path(audio_name).stem + ".txt")


def ensure_ffmpeg_on_path():
    """Agrega el ffmpeg portatil al PATH del proceso si esta presente."""
    if FFMPEG_DIR.exists():
        os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ.get("PATH", "")
