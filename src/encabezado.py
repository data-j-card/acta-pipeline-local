"""
Datos del encabezado del acta: provistos por el usuario (NO inventados por el LLM).

Se cargan desde un JSON que el usuario rellena/confirma. Con ellos se arma el
bloque de apertura del acta, identico en estructura al del acta de referencia.
"""
import json
from pathlib import Path

# Campos del encabezado. 'valor' se rellena/confirma con el usuario.
# 'origen' indica de donde salio la sugerencia (audio/referencia) o si hay que pedirlo.
CAMPOS = [
    ("numero_acta",        "Numero de acta",                 "PEDIR"),
    ("tipo_asamblea",      "Tipo (General Extraordinaria)",  "referencia"),
    ("ciudad",             "Ciudad",                         "referencia"),
    ("fecha_reunion",      "Fecha de la reunion",            "audio (verificar)"),
    ("hora_inicio",        "Hora de inicio",                 "audio (verificar)"),
    ("lugar",              "Lugar de la reunion",            "referencia (confirmar)"),
    ("conjunto",           "Nombre del conjunto",            "referencia"),
    ("nit",                "NIT de la copropiedad",          "PEDIR"),
    ("convoca",            "Quien convoca (administrador/a)","PEDIR"),
    ("base_legal",         "Base legal",                     "referencia"),
    ("articulo_legal",     "Articulo / numeral",             "referencia (confirmar)"),
    ("fecha_convocatoria", "Fecha de la convocatoria",       "PEDIR"),
]


def render_encabezado(d: dict) -> str:
    """Arma titulo + parrafo de apertura del acta a partir de los datos."""
    titulo = (
        f"ACTA N° {d.get('numero_acta','[verificar]')} "
        f"ASAMBLEA {d.get('tipo_asamblea','GENERAL EXTRAORDINARIA').upper()} "
        f"DE COPROPIETARIOS\n{d.get('conjunto','')}"
    )
    apertura = (
        f"En {d.get('ciudad','[verificar]')} a las {d.get('hora_inicio','[verificar]')} "
        f"del día {d.get('fecha_reunion','[verificar]')}, se reunieron en "
        f"{d.get('lugar','[verificar]')} de {d.get('conjunto','')} "
        f"NIT: {d.get('nit','[verificar]')} los propietarios y/o representantes del "
        f"mismo para realizar la asamblea {d.get('tipo_asamblea','general extraordinaria').lower()}, "
        f"convocados por {d.get('convoca','[verificar]')}, en uso de las facultades "
        f"legales que confiere la {d.get('base_legal','Ley 675 de 2001')}, "
        f"{d.get('articulo_legal','')}, hecha mediante la convocatoria del "
        f"{d.get('fecha_convocatoria','[verificar]')}, con el siguiente orden del día:"
    )
    return titulo + "\n\n" + apertura


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    import sys
    print(render_encabezado(load(Path(sys.argv[1]))))
