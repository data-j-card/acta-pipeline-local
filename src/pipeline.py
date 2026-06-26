"""
Pipeline del borrador del acta (caso de 2 sesiones / citas) — OPCION C.

El acta principal es la 2da sesion (donde se tomaron las decisiones). La 1ra sesion
se incluye como ANTECEDENTE condensado.

- Encabezado: datos_acta.json (provisto por el usuario, NO inventado).
- Antecedente (1ra sesion): map (notas por trozo) -> reduce (parrafo de antecedente).
- Desarrollo (2da sesion): narrado por trozos en estilo de acta.

Salida: output/acta_borrador.txt
"""
import re
from pathlib import Path

import config
import encabezado
import llm
from generar_acta import SYSTEM

# Marcador de trazabilidad [.. cita ..] y marca de tiempo (H:MM:SS) al inicio de linea.
MARKER_RE = re.compile(r"\[[^\]]*cita[^\]]*\]", re.IGNORECASE)
TS_RE = re.compile(r"^\((\d+:\d+:\d+)\)")


def chunk_time_range(lines):
    """Rango de tiempo (inicio-fin) cubierto por las lineas del trozo."""
    ts = [m.group(1) for ln in lines if (m := TS_RE.match(ln))]
    if not ts:
        return None
    return ts[0] if ts[0] == ts[-1] else f"{ts[0]}–{ts[-1]}"


def limpiar_trazas(texto, cita, rango):
    """Quita marcadores huerfanos y garantiza un marcador por parrafo (fallback)."""
    # 1) descartar lineas que son SOLO marcadores (huerfanos)
    keep = [ln for ln in texto.splitlines()
            if not (MARKER_RE.search(ln) and not MARKER_RE.sub("", ln).strip())]
    texto = "\n".join(keep).strip()
    # 2) todo parrafo sin marcador recibe el rango del trozo como respaldo
    out = []
    for par in re.split(r"\n\s*\n", texto):
        par = par.strip()
        if not par:
            continue
        if not MARKER_RE.search(par) and rango:
            par = f"{par} [{cita}, {rango}]"
        out.append(par)
    return "\n\n".join(out)

ORDEN_DEL_DIA = [
    "Verificación del quórum y llamado a lista.",
    "Lectura y aprobación del orden del día.",
    "Aprobación del reglamento de debate.",
    "Elección del presidente y secretario de la asamblea.",
    "Elección de la comisión verificadora del acta.",
    "Elección del consejo de administración.",
    "Elección de la administración.",
    "Cierre de la reunión.",
]

CITA1 = config.transcript_path(config.audios()[0])
CITA2 = config.transcript_path(config.audios()[1])

CHUNK_LINES = 110
NUM_CTX = 8192

CONTEXTO_ORDEN = "Orden del día de la asamblea:\n" + "\n".join(
    f"{i}. {p}" for i, p in enumerate(ORDEN_DEL_DIA, 1))

# --- MAP: extraer notas factuales de un trozo ---
NOTES_SYSTEM = (
    "Extraes notas factuales de la transcripcion de una asamblea de copropietarios. "
    "SOLO hechos presentes en el texto; nunca inventes cifras, nombres ni votaciones."
)
NOTES_PROMPT = (
    "Extrae notas concisas (viñetas) de este fragmento: temas tratados, propuestas, "
    "decisiones, votaciones (con cifras solo si aparecen), nombres y cargos. "
    "Si el fragmento no aporta nada relevante, responde solo: NADA.\n\n"
    "=== FRAGMENTO ===\n{chunk}\n=== FIN ===\nNOTAS:"
)

# --- REDUCE: antecedente de la 1ra cita ---
ANTECEDENTE_PROMPT = (
    "Las siguientes notas corresponden a la PRIMERA CITA de la asamblea "
    "(28 de abril de 2026), que no logró sesionar válidamente para decidir porque el "
    "quórum fue interrumpido. Redacta UNO O DOS párrafos breves de ANTECEDENTE para el "
    "acta, en estilo notarial formal y tercera persona. Indica que se realizó una "
    "primera cita, los aspectos que se alcanzaron a tratar y que el quórum fue "
    "interrumpido, por lo cual se convocó a segunda cita. NO inventes cifras ni nombres "
    "que no estén en las notas; usa [verificar] si falta un dato. No escribas la palabra "
    "'ANTECEDENTE' como título ni agregues marcadores de cita/minuto; redacta "
    "directamente los párrafos.\n\n"
    "=== NOTAS PRIMERA CITA ===\n{notas}\n=== FIN ===\nPárrafos del antecedente:"
)

# --- Narracion del desarrollo (2da cita) ---
CHUNK_PROMPT = (
    "{contexto}\n\n"
    "Estás redactando el ACTA de la {cita}. A continuación, un FRAGMENTO de la "
    "transcripción (cada línea trae su marca de tiempo entre paréntesis). Redacta SOLO "
    "el desarrollo correspondiente a este fragmento (narrativa del acta). No repitas el "
    "encabezado ni el orden del día como lista. Agrega al final de cada intervención la "
    "trazabilidad [{cita}, marca de tiempo] tomada de la línea de la transcripción.\n\n"
    "=== TRANSCRIPCIÓN (fragmento) ===\n{chunk}\n=== FIN FRAGMENTO ===\n\n"
    "ACTA (desarrollo de este fragmento):"
)


def chunks_of(path, size):
    lines = path.read_text(encoding="utf-8").splitlines()
    return [lines[i:i + size] for i in range(0, len(lines), size)]


def map_notas(path):
    notas = []
    chs = chunks_of(path, CHUNK_LINES)
    print(f"[MAP antecedente] {len(chs)} trozos de la 1ra cita")
    for j, ch in enumerate(chs, 1):
        txt, st = llm.generate(NOTES_PROMPT.format(chunk="\n".join(ch)),
                               system=NOTES_SYSTEM, num_ctx=NUM_CTX, temperature=0.1)
        txt = txt.strip()
        print(f"  notas {j}/{len(chs)}: {st['output_tokens']} tok ({st['elapsed_s']}s)")
        if txt and txt.upper() != "NADA":
            notas.append(txt)
    return "\n".join(notas)


def reduce_antecedente(notas):
    print("[REDUCE antecedente] componiendo parrafo...")
    txt, st = llm.generate(ANTECEDENTE_PROMPT.format(notas=notas),
                           system=SYSTEM, num_ctx=NUM_CTX, temperature=0.1)
    print(f"  antecedente: {st['output_tokens']} tok ({st['elapsed_s']}s)")
    txt = txt.strip()
    # defensa: quitar etiqueta 'ANTECEDENTE' si el modelo la repite al inicio
    for lead in ("ANTECEDENTE:", "ANTECEDENTE"):
        if txt.upper().startswith(lead):
            txt = txt[len(lead):].strip()
    # el antecedente NO lleva marcadores de trazabilidad por linea
    txt = MARKER_RE.sub("", txt)
    txt = re.sub(r"[ ]{2,}", " ", txt).strip()
    return txt


def narrar_sesion(path, cita):
    chs = chunks_of(path, CHUNK_LINES)
    print(f"[DESARROLLO {cita}] {len(chs)} trozos")
    partes = []
    for j, ch in enumerate(chs, 1):
        rango = chunk_time_range(ch)
        prompt = CHUNK_PROMPT.format(contexto=CONTEXTO_ORDEN, cita=cita,
                                     chunk="\n".join(ch))
        txt, st = llm.generate(prompt, system=SYSTEM, num_ctx=NUM_CTX, temperature=0.1)
        print(f"  trozo {j}/{len(chs)}: {st['output_tokens']} tok @ "
              f"{st['tokens_per_s']} tok/s ({st['elapsed_s']}s)")
        partes.append(limpiar_trazas(txt.strip(), cita, rango))
    return "\n\n".join(partes)


def main():
    datos = encabezado.load(config.DATOS_FILE)
    header = encabezado.render_encabezado(datos)

    notas1 = map_notas(CITA1)
    antecedente = reduce_antecedente(notas1)
    desarrollo = narrar_sesion(CITA2, "2.ª cita")

    out_parts = [
        header, "",
        "\n".join(f"{i}. {p}" for i, p in enumerate(ORDEN_DEL_DIA, 1)),
        "\nANTECEDENTE\n", antecedente,
        "\nDESARROLLO DEL ORDEN DEL DÍA (segunda cita)\n", desarrollo,
        "\n[CIERRE — VERIFICAR: hora de finalización, firmas del presidente y "
        "secretaria, y constancia de la comisión verificadora del acta.]",
        "\n[TABLA DE QUÓRUM Y ASISTENCIA — pendiente del PDF de asistencia (OCR).]",
    ]
    out = config.OUTPUT_DIR / "acta_borrador.txt"
    out.write_text("\n".join(out_parts), encoding="utf-8")
    print(f"\nLISTO. Borrador -> {out}")


if __name__ == "__main__":
    main()
