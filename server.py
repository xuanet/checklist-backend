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

    form = request.form
    files = request.files

    checklistId = int(form['checklistId'])
    c.execute("SELECT 1 FROM checklists WHERE id = ?", (checklistId,))
    exists = c.fetchone() is not None

    if exists:
        # Delete files
        c.execute("SELECT id FROM categories WHERE checklist_id = ?", (checklistId,))
        category_ids = [row[0] for row in c.fetchall()]
        if category_ids:
            placeholders = ','.join(['?'] * len(category_ids))
            c.execute(f"DELETE FROM files WHERE category_id IN ({placeholders})", category_ids)
        # Delete categories
        c.execute("DELETE FROM categories WHERE checklist_id = ?", (checklistId,))
    else:
        # Create new checklist
        c.execute("INSERT INTO checklists DEFAULT VALUES")
        checklistId = c.lastrowid

    # Add categories
    categories = {}
    for key in form:
        if key.startswith("categories[") and key.endswith("][name]"):
            index = key.split("[")[1].split("]")[0]
            name = form[key]
            c.execute('INSERT INTO categories (checklist_id, name) VALUES (?, ?)', (checklistId, name))
            categories[index] = c.lastrowid

    # Add files
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

    return jsonify({"status": "success", "checklist_id": checklistId})



@app.route('/clone_checklist/<int:checklist_id>', methods=['GET'])
def clone_checklist(checklist_id):
    print("here")
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

@app.route('/get_all_checklists', methods=['GET'])
def get_all_checklists():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute('SELECT id FROM checklists')
    rows = c.fetchall()

    checklist_ids = [row[0] for row in rows]

    conn.close()
    return jsonify(checklist_ids)

@app.route('/get_next_available_id', methods=['GET'])
def get_next_checklist_id():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT MAX(id) FROM checklists")
    row = c.fetchone()
    print(row)
    if row[0] is None:
        return jsonify(1)
    else:
        return jsonify(row[0]+1)
    
@app.route('/append_files', methods=['POST'])
def append_files():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    form = request.form
    files = request.files
    checklistId = int(form['checklistId'])

    c.execute("SELECT 1 FROM checklists WHERE id = ?", (checklistId,))
    if not c.fetchone():
        return jsonify({"error": "Checklist not found"}), 404

    for key in files:
        if key.startswith("categories["):
            parts = key.split("[")
            cat_idx = parts[1].split("]")[0]
            file = files[key]
            filename_key = f"categories[{cat_idx}][files_rename][{key.split('[')[3].split(']')[0]}]"
            new_filename = form.get(filename_key, file.filename)

            c.execute(
                "SELECT id FROM categories WHERE checklist_id = ? LIMIT 1 OFFSET ?",
                (checklistId, cat_idx)
            )
            row = c.fetchone()
            if row:
                cat_id = row[0]
                content = file.read()
                c.execute(
                    'INSERT INTO files (category_id, filename, content) VALUES (?, ?, ?)',
                    (cat_id, new_filename, content)
                )

    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


app.run(debug=True, port=5000)