from pypdf import PdfReader

r = PdfReader("fw8ben limpio.pdf")
p = r.pages[0]
out = []

def vis(text, cm, tm, font_dict, font_size):
    if text and text.strip():
        out.append((round(tm[5]), round(tm[4]), text.strip()[:70]))

p.extract_text(visitor_text=vis)
lines = [f"{y} {x} | {t}" for y, x, t in sorted(out, reverse=True)]
open("_docs-strata/_w8_texto.txt", "w", encoding="utf8").write("\n".join(lines))
print("ok", len(lines))
