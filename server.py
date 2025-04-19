import os
import sqlite3
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_NAME = 'checklists.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_id INTEGER,
            name TEXT,
            FOREIGN KEY(checklist_id) REFERENCES checklists(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            filename TEXT,
            content BLOB,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
    ''')

    conn.commit()
    conn.close()

init_db()

@app.route('/save_checklist', methods=['POST'])
def save_checklist():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute('INSERT INTO checklists DEFAULT VALUES')
    checklist_id = c.lastrowid

    form = request.form
    files = request.files

    categories = {}
    for key in form:
        if key.startswith("categories[") and key.endswith("][name]"):
            index = key.split("[")[1].split("]")[0]
            name = form[key]
            c.execute('INSERT INTO categories (checklist_id, name) VALUES (?, ?)', (checklist_id, name))
            categories[index] = c.lastrowid

    for key in files:
        parts = key.split("[")
        cat_idx = parts[1].split("]")[0]
        if cat_idx in categories:
            file = files[key]
            content = file.read()
            c.execute(
                'INSERT INTO files (category_id, filename, content) VALUES (?, ?, ?)',
                (categories[cat_idx], file.filename, content)
            )

    conn.commit()
    conn.close()
    return jsonify({"status": "success", "checklist_id": checklist_id})


@app.route('/clone_checklist/<int:checklist_id>', methods=['GET'])
def clone_checklist(checklist_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute('SELECT id, name FROM categories WHERE checklist_id = ?', (checklist_id,))
    categories = c.fetchall()

    result = []
    for cat_id, cat_name in categories:
        c.execute('SELECT filename, content FROM files WHERE category_id = ?', (cat_id,))
        files = c.fetchall()
        encoded_files = [
            {
                "filename": f[0],
                "base64": base64.b64encode(f[1]).decode('utf-8')
            } for f in files
        ]
        result.append({
            "name": cat_name,
            "files": encoded_files
        })

    return jsonify(result)

app.run(port=5000)