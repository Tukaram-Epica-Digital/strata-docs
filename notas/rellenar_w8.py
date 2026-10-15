"""Rellena el W-8BEN (fw8ben limpio.pdf).

Caso: pago de Corsair (EE.UU.) por un video de YouTube grabado desde Espana.
El servicio se realiza FUERA de EE.UU., asi que el ingreso no es de fuente
estadounidense y no procede retencion: la linea 10 se deja en blanco.

Uso:    python _docs-strata\rellenar_w8.py
Salida:  fw8ben Arturo Alonso (borrador).pdf
"""
from pypdf import PdfReader, PdfWriter

SRC = "fw8ben limpio.pdf"
DST = "fw8ben Arturo Alonso (borrador).pdf"

FECHA_NACIMIENTO = ""   # MM-DD-YYYY  -> pendiente
REFERENCIA = ""         # Linea 7: opcional (num. de factura / referencia del contrato)

# IDs verificados contra las coordenadas de los campos del PDF
CAMPOS = {
    "topmostSubform[0].Page1[0].f_1[0]":  "Arturo Alonso Alonso",   # 1 Nombre
    "topmostSubform[0].Page1[0].f_2[0]":  "Spain",                  # 2 Ciudadania
    "topmostSubform[0].Page1[0].f_3[0]":  "Calle Teruel 30, 2D",    # 3 Calle
    "topmostSubform[0].Page1[0].f_4[0]":  "Huesca, Huesca 22005",   # 3 Ciudad / prov. / CP
    "topmostSubform[0].Page1[0].f_5[0]":  "Spain",                  # 3 Pais
    "topmostSubform[0].Page1[0].f_10[0]": "72990166B",              # 6a Foreign TIN (DNI)
    "topmostSubform[0].Page1[0].f_13[0]": "Spain",                  # 9 Residente en (tratado)
    "topmostSubform[0].Page1[0].f_21[0]": "Arturo Alonso Alonso",   # Print name of signer
}

if FECHA_NACIMIENTO:
    CAMPOS["topmostSubform[0].Page1[0].f_12[0]"] = FECHA_NACIMIENTO   # 8 Fecha de nacimiento
if REFERENCIA:
    CAMPOS["topmostSubform[0].Page1[0].f_11[0]"] = REFERENCIA          # 7 Reference number(s)

# --- Si Corsair exigiera rellenar la linea 10, descomenta (en orden de lectura:
#     articulo, parrafo, %, tipo de ingreso, explicacion) ---
# CAMPOS.update({
#     "topmostSubform[0].Page1[0].f_14[0]": "14",
#     "topmostSubform[0].Page1[0].f_15[0]": "1",
#     "topmostSubform[0].Page1[0].f_17[0]": "0",
#     "topmostSubform[0].Page1[0].f_16[0]": "Independent personal services",
#     "topmostSubform[0].Page1[0].f_18[0]": ("Services are performed outside the United "
#                                            "States; the beneficial owner has no fixed base "
#                                            "in the United States."),
# })

reader = PdfReader(SRC)
writer = PdfWriter()
writer.append(reader)
writer.update_page_form_field_values(writer.pages[0], CAMPOS, auto_regenerate=False)
writer.set_need_appearances_writer(True)   # el PDF no trae fuentes embebidas

with open(DST, "wb") as f:
    writer.write(f)

print("OK ->", DST, "| campos:", len(CAMPOS))
