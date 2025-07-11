from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# Initialize embedding model locally (free)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Chat completion client (used for generating natural language responses)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)
from flask import send_file
from PIL import Image, ImageDraw, ImageFont
import os


def draw_multiline_text(draw_obj, position, text, font, max_width):
    lines = []
    words = text.split()
    line = ""
    for word in words:
        test_line = line + word + " "
        if draw_obj.textlength(test_line, font=font) <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word + " "
    lines.append(line)

    x, y = position
    for line in lines:
        draw_obj.text((x, y), line.strip(), fill="black", font=font)
        y += 20

# Get text embedding using local model
def get_embedding(text):
    embedding = embedding_model.encode([text])[0]
    return np.array(embedding)

# Load data from SQLite
def load_rows():
    conn = sqlite3.connect("test_prestations.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, prestation, partie_ouvrage, libelle_critere, valeur_critere FROM prestations")
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "prestation": r[1],
            "partie_ouvrage": r[2],
            "libelle_critere": r[3],
            "valeur_critere": r[4],
            "text": f"{r[1]} | {r[2]} | {r[3]} | {r[4]}"
        })
    return result


# Find the best match between input and database
def find_best_match(user_input, rows):
    input_vector = get_embedding(user_input)
    best_score = -1
    best_row = None

    for row in rows:
        vec = get_embedding(row["text"])
        score = np.dot(input_vector, vec) / (np.linalg.norm(input_vector) * np.linalg.norm(vec))
        if score > best_score:
            best_score = score
            best_row = row
    return best_row

# Generate AI solution
def generate_response(user_input, matched_text):
    # Reformulate the problem
    prompt_reformulated = f"""
Un problème a été signalé : "{user_input}"
Cela semble être lié à cette exigence : "{matched_text}"

Réécris ce problème de façon claire, professionnelle et concise.
"""
    reformulated = client.chat.completions.create(
        model="meta-llama/llama-3-70b-instruct",
        messages=[{"role": "user", "content": prompt_reformulated}],
        temperature=0.3
    ).choices[0].message.content.strip()

    # Suggest a corrective action
    prompt_corrective = f"""
Voici un problème signalé : "{reformulated}"

Propose une seule action corrective technique pour résoudre ce problème.
"""
    corrective = client.chat.completions.create(
        model="meta-llama/llama-3-70b-instruct",
        messages=[{"role": "user", "content": prompt_corrective}],
        temperature=0.3
    ).choices[0].message.content.strip()

    # Suggest a preventive action
    prompt_preventive = f"""
Voici un problème signalé : "{reformulated}"

Propose une seule action préventive technique pour éviter que ce problème ne se reproduise.
"""
    preventive = client.chat.completions.create(
        model="meta-llama/llama-3-70b-instruct",
        messages=[{"role": "user", "content": prompt_preventive}],
        temperature=0.3
    ).choices[0].message.content.strip()

    return {
        "corrected_problem": reformulated,
        "corrective_action": corrective,
        "preventive_action": preventive
    }

# Initial problem analysis
@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    user_input = data.get("text")

    if not user_input:
        return jsonify({"error": "Missing 'text' field"}), 400

    rows = load_rows()
    best = find_best_match(user_input, rows)
    result = generate_response(user_input, best["text"])

    return jsonify({
    "matched_critere": {
        "prestation": best["prestation"],
        "partie_ouvrage": best["partie_ouvrage"],
        "libelle_critere": best["libelle_critere"],
        "valeur_critere": best["valeur_critere"]
    },
    "corrected_problem": result["corrected_problem"],
    "corrective_action": result["corrective_action"],
    "preventive_action": result["preventive_action"]
})



# User validates the AI response
@app.route("/validate", methods=["POST"])
def validate():
    data = request.get_json()
    problem = data.get("problem")
    solution = data.get("solution")

    if not problem or not solution:
        return jsonify({"error": "Missing fields"}), 400

    with open("validated_responses.txt", "a", encoding="utf-8") as f:
        f.write(f"Problem: {problem}\nValidated Solution:\n{solution}\n\n")

    return jsonify({"message": "Response validated and saved successfully."})

# User suggests a better solution, AI refines it
@app.route("/revise", methods=["POST"])
def revise():
    data = request.get_json()
    user_feedback = data.get("suggestion")
    original_problem = data.get("original")

    if not user_feedback or not original_problem:
        return jsonify({"error": "Missing fields"}), 400

    prompt = f"""
Un utilisateur a signalé un problème : "{original_problem}".

L'IA a proposé une solution, mais l'utilisateur a suggéré une autre approche :
"{user_feedback}"

Corrige la solution en prenant en compte cette nouvelle suggestion, tout en gardant un ton professionnel, et propose :
1. Une nouvelle action corrective technique
2. Une nouvelle action préventive technique
"""
    response = client.chat.completions.create(
        model="meta-llama/llama-3-70b-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )

    return jsonify({
        "revised_response": response.choices[0].message.content.strip()
    })
@app.route("/add-prestation", methods=["POST"])
def add_prestation():
    data = request.get_json()
    prestation = data.get("prestation")
    partie_ouvrage = data.get("partie_ouvrage")
    libelle_critere = data.get("libelle_critere")
    valeur_critere = data.get("valeur_critere")

    if not all([prestation, partie_ouvrage, libelle_critere, valeur_critere]):
        return jsonify({"error": "Tous les champs sont requis"}), 400

    conn = sqlite3.connect("test_prestations.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO prestations (prestation, partie_ouvrage, libelle_critere, valeur_critere)
        VALUES (?, ?, ?, ?)
    """, (prestation, partie_ouvrage, libelle_critere, valeur_critere))
    conn.commit()
    conn.close()

    return jsonify({"message": "✅ Enregistrement ajouté avec succès"}), 200

# Root endpoint (can serve frontend if needed)
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


from docx import Document
from io import BytesIO
from flask import send_file

@app.route("/download-fiche", methods=["POST"])
def download_fiche_docx():
    data = request.get_json()
    description = data.get("description", "")
    corrective = data.get("corrective_action", "")
    preventive = data.get("preventive_action", "")

    doc = Document("fiche_empty.docx")

    def insert_below_heading_in_table(doc, heading, content):
        for table in doc.tables:
            for i, row in enumerate(table.rows):
                for cell in row.cells:
                    if heading.lower() in cell.text.lower():
                        # Insert content into the row immediately after
                        try:
                            next_row = table.rows[i + 1]
                            next_row.cells[0].text = content
                            return True
                        except IndexError:
                            pass
        return False

    insert_below_heading_in_table(doc, "1.3. Description", description)
    insert_below_heading_in_table(doc, "2 - Action corrective proposée", corrective)
    insert_below_heading_in_table(doc, "4- Actions Préventives", preventive)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="fiche_remplie.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )



if __name__ == "__main__":
    app.run(debug=True, port=5000)
