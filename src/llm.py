"""
Cliente LLM pluggable del proyecto.

Por defecto usa Ollama local (http://localhost:11434). Disenado para que cambiar
a otro backend (p.ej. una API en la nube) sea trivial mas adelante.
"""
import time
import requests

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b-instruct"


def generate(prompt: str, system: str | None = None, model: str = DEFAULT_MODEL,
             num_ctx: int = 8192, temperature: float = 0.2, timeout: int = 1800):
    """
    Llama al modelo y devuelve (texto, stats).

    stats incluye velocidad (tokens/seg) y conteos para medir desempeno en la GPU.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": num_ctx, "temperature": temperature},
    }
    if system:
        payload["system"] = system

    t0 = time.time()
    r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    elapsed = time.time() - t0

    eval_count = data.get("eval_count") or 0
    eval_dur_ns = data.get("eval_duration") or 0
    tok_per_s = (eval_count / (eval_dur_ns / 1e9)) if eval_dur_ns else None

    stats = {
        "elapsed_s": round(elapsed, 1),
        "prompt_tokens": data.get("prompt_eval_count"),
        "output_tokens": eval_count,
        "tokens_per_s": round(tok_per_s, 1) if tok_per_s else None,
    }
    return data.get("response", ""), stats


def list_models(timeout: int = 5):
    r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=timeout)
    r.raise_for_status()
    return [m["name"] for m in r.json().get("models", [])]
