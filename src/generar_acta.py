"""
Generacion del acta a partir de transcripciones, con LLM local (Ollama/Qwen).

Modo de prueba (un tramo de la transcripcion):
    python src/generar_acta.py --lineas 1 60

Esto sirve para medir velocidad/calidad del modelo antes de armar el pipeline completo.
"""
import argparse
from pathlib import Path

import config
import llm

TRANSCRIPT_1 = config.transcript_path(config.audios()[0])
TRANSCRIPT_2 = config.transcript_path(config.audios()[1])

SYSTEM = (
    "Eres el secretario de una asamblea general de copropietarios de propiedad "
    "horizontal en Colombia. Redactas el ACTA formal a partir de la "
    "transcripcion de la grabacion de la reunion.\n"
    "ESTILO: espanol formal y notarial, tercera persona, tiempo pasado. Usa formulas "
    "como 'Toma la palabra un copropietario/una copropietaria ...', 'se somete a "
    "consideracion', 'queda aprobado con X votos a favor y Y en contra'.\n"
    "REGLAS ESTRICTAS (un acta tiene valor legal):\n"
    "- NO escribas el bloque de encabezado (numero de acta, fecha, hora, lugar, NIT, "
    "quien convoca, base legal): eso se rellena aparte desde datos verificados. PERO SI "
    "debes narrar todo el desarrollo, incluyendo el resultado de la verificacion del "
    "quorum (porcentaje), la aprobacion del orden del dia y cada punto tratado.\n"
    "- PROHIBIDO inventar fechas, horas, cifras, porcentajes, nombres o conteos de "
    "votos. Usa SOLO lo que aparece en la transcripcion.\n"
    "- VOTACIONES: NUNCA escribas 'por unanimidad' ni 'se aprueba por unanimidad' si "
    "hubo votos en contra o abstenciones. Si hay un conteo (p.ej. '47 a favor y 3 en "
    "contra'), reportalo TAL CUAL y NO agregues 'por unanimidad'. Usa 'aprobado por "
    "unanimidad' solo cuando no hubo NINGUNA oposicion. No inventes numeros de votos.\n"
    "- Si un dato es ambiguo, ilegible o falta, escribe [verificar] en su lugar.\n"
    "- Corrige terminos tecnicos mal transcritos (p.ej. 'coro' -> 'quorum').\n"
    "- HABLANTES: vienen como [SPEAKER_XX]; no escribas esas etiquetas. NUNCA inventes "
    "el nombre de quien interviene ni le asignes el nombre de otra persona (jamas "
    "escribas un nombre con el genero equivocado). Usa 'la administradora' / 'el "
    "administrador' SOLO para quien administra, y 'el presidente' SOLO para quien "
    "preside; para los demas intervinientes usa 'un copropietario' o 'una "
    "copropietaria'. Escribe un nombre propio solo si aparece explicito e inequivoco.\n"
    "- TRAZABILIDAD: al final de CADA parrafo agrega entre corchetes la cita y la marca "
    "de tiempo de la transcripcion de donde proviene, p.ej. [2.ª cita, 0:12:30], para "
    "que la revision humana valide al hablante real. Copia la marca de tiempo de la "
    "linea correspondiente. El marcador va PEGADO al final del parrafo; NUNCA pongas "
    "marcadores en una linea aparte ni los agrupes todos juntos al final.\n"
    "- No incluyas la tabla de asistencia (esa va aparte).\n"
    "- No repitas el orden del dia como lista al final; redacta en parrafos.\n"
    "- Redacta de forma concisa y fiel; resume divagaciones sin perder decisiones."
)

PROMPT_TMPL = (
    "A continuacion esta un fragmento de la transcripcion de la asamblea "
    "(con marcas de tiempo y etiquetas de hablante).\n\n"
    "Redacta la seccion correspondiente del acta (desarrollo del orden del dia) "
    "para lo que ocurre en este fragmento, siguiendo el estilo indicado.\n\n"
    "=== TRANSCRIPCION ===\n{chunk}\n=== FIN TRANSCRIPCION ===\n\n"
    "ACTA (seccion correspondiente):"
)


def load_chunk(path: Path, start: int, end: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[start - 1:end])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivo", default=str(TRANSCRIPT_1), help="transcripcion .txt")
    ap.add_argument("--lineas", nargs=2, type=int, default=[1, 60],
                    metavar=("INICIO", "FIN"))
    ap.add_argument("--modelo", default=llm.DEFAULT_MODEL)
    ap.add_argument("--num-ctx", type=int, default=4096)
    ap.add_argument("--temp", type=float, default=0.1)
    args = ap.parse_args()

    chunk = load_chunk(Path(args.archivo), args.lineas[0], args.lineas[1])
    prompt = PROMPT_TMPL.format(chunk=chunk)

    print(f"Modelo: {args.modelo} | num_ctx: {args.num_ctx} | "
          f"lineas {args.lineas[0]}-{args.lineas[1]}")
    print("Generando...\n")
    texto, stats = llm.generate(prompt, system=SYSTEM, model=args.modelo,
                                num_ctx=args.num_ctx, temperature=args.temp)
    print("=" * 60)
    print(texto.strip())
    print("=" * 60)
    print(f"\n[STATS] tiempo={stats['elapsed_s']}s | "
          f"prompt_tokens={stats['prompt_tokens']} | "
          f"output_tokens={stats['output_tokens']} | "
          f"velocidad={stats['tokens_per_s']} tok/s")


if __name__ == "__main__":
    main()
