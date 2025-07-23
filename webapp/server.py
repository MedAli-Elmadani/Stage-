

# Chat completion client (used for generating natural language responses)

from flask import Flask, request, jsonify
import sqlite3
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI
from flask_cors import CORS
import traceback

from openai import AzureOpenAI
app = Flask(__name__)
CORS(app)
client = AzureOpenAI(
    
)

import os

# Automatically resolves the correct path regardless of where Flask is run from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'test.db')


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/projects', methods=['GET'])
def get_projects():
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, latitude, longitude FROM projects")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([
        {'id': row[0], 'name': row[1], 'latitude': row[2], 'longitude': row[3]}
        for row in rows
    ])


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files or 'project_id' not in request.form:
        return jsonify({'error': 'Missing image or project_id'}), 400

    project_id = request.form['project_id']
    image_file = request.files['image']

    try:
        # Convert image to base64
        img = Image.open(image_file.stream)
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()

        # Fetch prestations from DB
        conn = sqlite3.connect('test.db')
        conn.row_factory = sqlite3.Row
        prestations = conn.execute("""
            SELECT prestation, partie_ouvrage, libelle_critere, valeur_critere
            FROM prestations WHERE project_id=?
        """, (project_id,)).fetchall()
        conn.close()

        # Format prestations as text
        prestations_text = "\n".join(
            f"- Prestation: {p['prestation']}, Partie: {p['partie_ouvrage']}, Critère: {p['libelle_critere']}, Valeur attendue: {p['valeur_critere']}"
            for p in prestations
        ) if prestations else "Aucun critère enregistré pour ce projet."

        # Build prompt
        prompt = f"""Voici les critères de conformité actuellement enregistrés pour ce projet :

{prestations_text}

Analyse l’image suivante pour détecter toute non-conformité visible.

Si elle correspond à un critère ci-dessus, mentionne-le.

Si aucun critère ne correspond, propose un critère possible (même s’il est absent de la liste) et justifie ton choix.

Puis propose :
1. Une reformulation claire de la non-conformité
2. Une action corrective adaptée
3. Une action préventive possible"""

        # Send to Azure OpenAI
        response = client.chat.completions.create(
            model="gpt-4",  # Replace with your Azure deployment name
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un ingénieur de contrôle qualité en BTP."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/jpeg;base64," + img_b64
                            }
                        }
                    ]
                }
            ],
            temperature=0,
             max_tokens=1000,
        )

        result_text = response.choices[0].message.content
        return jsonify({'result': result_text})

    except Exception as e:
        traceback.print_exc()  # 👈 Shows full error in terminal
        return jsonify({'error': 'Internal error', 'details': str(e)}), 500

@app.route('/save_result', methods=['POST'])
def save_result():
    data = request.get_json()
    project_id = data.get('project_id')
    result_text = data.get('result')
    image_base64 = data.get('image_base64')  # Expect base64 string from frontend

    if not project_id or not result_text:
        return jsonify({'error': 'project_id et result sont requis'}), 400

    try:
        conn = sqlite3.connect("test.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO analysis_results (project_id, result, image_base64)
            VALUES (?, ?, ?)
        """, (project_id, result_text, image_base64))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Résultat sauvegardé avec succès'}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Erreur interne', 'details': str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
