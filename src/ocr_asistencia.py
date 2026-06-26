"""
OCR del padron de asistencia (PDF escaneado) + deteccion de asistencia.

- Apto + Propietario: OCR de las columnas IMPRESAS (EasyOCR, local/GPU).
- ASISTIO (1/0): se detecta por TINTA en la celda de FIRMA de cada fila
  (firma manuscrita = asistio). No se "lee" la firma; se mide densidad de tinta.
- COEFICIENTE / PODER / COEF_QUORUM: vacios (revision humana).

Salida: output/padron.csv   (incluye columna _INK para calibrar/validar)
"""
import csv
import re

import numpy as np
import fitz
import easyocr

import config

PDF = config.pdf_asistencia()
OUT = config.OUTPUT_DIR / "padron.csv"
LEFT_FRAC = 0.42          # columnas impresas (Apto + Propietario)
# Region manuscrita (Correo + Cedula + Firma). Si esta diligenciada a mano = asistio.
MANO_X = (0.42, 0.985)
INK_THRESHOLD = 0.020     # fraccion de pixeles oscuros para considerar "diligenciado"
DPI = 200

APTO_RE = re.compile(r"\d{3}")


def limpiar_nombre(s: str) -> str:
    """Nombres impresos van en MAYUSCULAS; cola en minusculas = tinta manuscrita."""
    toks = s.split()
    while toks and re.search(r"[a-z]", toks[-1]):
        toks.pop()
    return " ".join(toks).strip(" .-")


def page_rgb(page):
    pix = page.get_pixmap(dpi=DPI)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return np.ascontiguousarray(img[:, :, :3])


def rows_from_page(reader, img):
    h, w = img.shape[:2]
    crop = img[:, : int(LEFT_FRAC * w)]
    res = reader.readtext(crop, detail=1, paragraph=False)
    boxes = []
    for bbox, text, _ in res:
        ys = [p[1] for p in bbox]
        xs = [p[0] for p in bbox]
        boxes.append({"yc": sum(ys) / 4, "xl": min(xs), "text": text.strip()})
    if not boxes:
        return []
    boxes.sort(key=lambda b: b["yc"])
    tol = max(12, int(0.012 * h))
    grupos, cur, last = [], [], None
    for b in boxes:
        if last is not None and abs(b["yc"] - last) > tol:
            grupos.append(cur); cur = []
        cur.append(b); last = b["yc"]
    if cur:
        grupos.append(cur)

    out = []
    for r in grupos:
        r.sort(key=lambda b: b["xl"])
        txt = " ".join(b["text"] for b in r)
        m = APTO_RE.search(txt)
        if not m:
            continue
        apto = txt[: m.end()].strip(" .-")
        prop = limpiar_nombre(txt[m.end():].strip(" .-"))
        if prop:
            out.append({"apto": apto, "prop": prop,
                        "yc": sum(b["yc"] for b in r) / len(r)})
    return out


def detectar_firmas(img, rows):
    """Mide tinta en la region manuscrita (Correo+Cedula+Firma) de cada fila."""
    h, w = img.shape[:2]
    ycs = sorted(r["yc"] for r in rows)
    diffs = [b - a for a, b in zip(ycs, ycs[1:])]
    spacing = sorted(diffs)[len(diffs) // 2] if diffs else 0.05 * h
    band = spacing * 0.8
    x0, x1 = int(MANO_X[0] * w), int(MANO_X[1] * w)
    for r in rows:
        y0 = max(0, int(r["yc"] - band / 2))
        y1 = min(h, int(r["yc"] + band / 2))
        cell = img[y0:y1, x0:x1]
        if cell.size == 0:
            r["ink"] = 0.0
            continue
        mh = int(0.12 * cell.shape[0]); mw = int(0.05 * cell.shape[1])
        inner = cell[mh:cell.shape[0] - mh, mw:cell.shape[1] - mw]
        gray = inner.mean(axis=2)
        r["ink"] = float((gray < 110).mean()) if gray.size else 0.0
    return rows


def main():
    reader = easyocr.Reader(["es"], gpu=True, verbose=False)
    doc = fitz.open(PDF)
    filas = []
    for i, page in enumerate(doc, 1):
        img = page_rgb(page)
        rows = detectar_firmas(img, rows_from_page(reader, img))
        firmados = sum(r["ink"] >= INK_THRESHOLD for r in rows)
        print(f"pag {i}: {len(rows)} filas | {firmados} con firma detectada")
        filas.extend(rows)

    inks = sorted(r["ink"] for r in filas)
    if inks:
        q = lambda p: inks[min(len(inks) - 1, int(p * len(inks)))]
        print(f"\nINK fraccion -> min={inks[0]:.3f} p25={q(.25):.3f} "
              f"mediana={q(.5):.3f} p75={q(.75):.3f} max={inks[-1]:.3f}")
    total_asist = sum(r["ink"] >= INK_THRESHOLD for r in filas)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.writer(f)
        wr.writerow(["APTO", "PROPIETARIO", "COEFICIENTE", "PODER",
                     "ASISTIO", "COEF_QUORUM", "_INK"])
        for r in filas:
            asist = 1 if r["ink"] >= INK_THRESHOLD else 0
            wr.writerow([r["apto"], r["prop"], "", "", asist, "", f"{r['ink']:.3f}"])

    print(f"\nTOTAL: {len(filas)} apartamentos | {total_asist} asistencias "
          f"(umbral={INK_THRESHOLD}) -> {OUT}")


if __name__ == "__main__":
    main()
