pip install pdfplumber
import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
import tempfile

st.set_page_config(page_title="PDF → WFM", layout="centered")
st.title("📄➡️📊 Générateur WFM depuis PDF")

st.markdown("""
Déposez votre **PDF planning**, l’outil génère automatiquement  
un fichier **Excel compatible WFM**.
""")

uploaded_file = st.file_uploader("📤 Déposer le fichier PDF", type=["pdf"])

TIME_PATTERN = r"\d{2}:\d{2}"

def get_duration(a, b):
    try:
        t1 = datetime.strptime(a, "%H:%M")
        t2 = datetime.strptime(b, "%H:%M")
        return (t2 - t1).seconds // 60
    except:
        return 0

def is_continuation_line(line, times):
    return len(times) == 2 and len(line.split()) <= 3

if uploaded_file:
    with st.spinner("⏳ Traitement du PDF en cours..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            pdf_path = tmp.name

        rows = []
        last_index = -1

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                for line in text.split("\n"):
                    line = line.strip()
                    times = re.findall(TIME_PATTERN, line)

                    if line.lower().startswith(("cré", "le ")):
                        continue

                    if last_index >= 0 and is_continuation_line(line, times):
                        a, b = times
                        dur = get_duration(a, b)
                        if dur <= 15 and rows[last_index][5] == "":
                            rows[last_index][5] = f"{a} - {b}"
                        elif dur >= 30:
                            rows[last_index][4] = f"{a} - {b}"
                        continue

                    if len(times) < 2:
                        continue

                    parts = line.split()
                    matricule = parts[0]
                    if matricule.lower().startswith("cré"):
                        continue

                    name = line.split(matricule)[1].split(times[0])[0].strip()

                    pause1 = pause2 = repas = ""

                    blocks = [(times[i], times[i+1]) for i in range(1, len(times)-1, 2)]
                    pauses = []

                    for a, b in blocks:
                        dur = get_duration(a, b)
                        if dur <= 15:
                            pauses.append(f"{a} - {b}")
                        elif dur >= 30:
                            repas = f"{a} - {b}"

                    if pauses: pause1 = pauses[0]
                    if len(pauses) > 1: pause2 = pauses[1]

                    rows.append([
                        matricule, name, times[0],
                        pause1, repas, pause2, times[-1]
                    ])
                    last_index += 1

        df = pd.DataFrame(rows, columns=[
            "Matricule","Nom","Heure de début",
            "Pause courte 1","Repas","Pause courte 2","Heure de fin"
        ])

        df = df[df["Nom"].astype(str).str.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ]")]
        df.drop(columns=["Nom"], inplace=True)

        df.rename(columns={
            "Heure de début": "Heure de départ",
            "Heure de fin": "Horaire de fin",
            "Pause courte 1": "Break 1_D",
            "Pause courte 2": "Break 2_D",
            "Repas": "Lunch D"
        }, inplace=True)

        def insert_after(col, new):
            i = df.columns.get_loc(col) + 1
            df.insert(i, new, "")

        insert_after("Break 1_D", "Break 1_F")
        insert_after("Lunch D", "Lunch F")
        insert_after("Break 2_D", "Break 2_F")

        def split_range(v):
            if pd.isna(v) or v == "": return "", ""
            a, b = re.split(r"\s*-\s*", v)
            return a, b

        for c in ["Break 1_D","Lunch D","Break 2_D"]:
            df[c], df[c.replace("_D","_F")] = zip(*df[c].map(split_range))

        st.success("✅ Fichier prêt")

        output = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        df.to_excel(output.name, index=False)

    with open(output.name, "rb") as f:
        st.download_button(
            "📥 Télécharger le fichier Excel WFM",
            f,
            file_name="Horaires_Final_WFM_READY.xlsx"
        )
streamlit
pdfplumber
pandas
openpyxl
