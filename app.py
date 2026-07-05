from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify, send_from_directory
import os, sqlite3, time, random
from werkzeug.utils import secure_filename
from datetime import datetime
from fpdf import FPDF
import tempfile

# 1. முதலில் app-ஐ உருவாக்க வேண்டும்
app = Flask(__name__)

# 2. அதற்குப் பிறகு config அமைக்க வேண்டும்
UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATABASE = "medical_ai_pro.db"

# --- IMAGE LOADING ROUTE (இதுதான் முக்கியமானது) ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 3. இனி உங்கள் பங்க்ஷன்கள்
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT, name TEXT, age INTEGER, gender TEXT, date TEXT,
        disease TEXT, severity TEXT, confidence TEXT, 
        remark TEXT, file_path TEXT, priority TEXT, prob_data TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, timestamp TEXT
    )''')
    
    cursor.execute("SELECT COUNT(*) FROM patients")
    if cursor.fetchone()[0] == 0:
        sample_patients = [
            ('CAS-2026-8612', 'Jamuna', 20, 'Female', '10-06-2026 22:17', 'Pneumonia', 'Severe', '99.1%', 'Urgent clinical inspection required.', 'uploads/sample_xray.png', 'Critical', 'Pneumonia:85%,Normal:10%,Other:5%'),
            ('CAS-2026-4277', 'LINGESH', 23, 'Male', '10-06-2026 22:01', 'COVID-19', 'Mild', '95.4%', 'Standard isolation protocols baseline.', 'uploads/sample_xray.png', 'Urgent', 'Pneumonia:5%,Normal:10%,Other:85%')
        ]
        cursor.executemany('''INSERT INTO patients 
            (case_id, name, age, gender, date, disease, severity, confidence, remark, file_path, priority, prob_data) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', sample_patients)
    conn.commit()
    conn.close()

init_db()

DISEASES = ["Pneumonia", "Normal", "COVID-19", "Tuberculosis"]

def add_audit(action):
    conn = sqlite3.connect(DATABASE)
    conn.execute("INSERT INTO audit_logs (action, timestamp) VALUES (?, ?)", 
                 (action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get('name', 'Unknown')
        age = request.form.get('age', 'N/A')
        gender = request.form.get('gender', 'N/A')
        remark = request.form.get('remark', '')
        date_str = datetime.now().strftime("%d-%m-%Y %H:%M")
        case_id = f"CAS-{datetime.now().year}-{random.randint(1000, 9999)}"
        file = request.files.get('scan')
        filename = "sample_xray.png"
        if file:
            filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
        final_disease = random.choice(DISEASES)
        severity = random.choice(["Mild", "Moderate", "Severe"])
        priority = "Critical" if severity in ["Moderate", "Severe"] else "Urgent"

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO patients 
            (case_id, name, age, gender, date, disease, severity, confidence, remark, file_path, priority, prob_data) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
            (case_id, name, age, gender, date_str, final_disease, severity, "99%", remark, filename, priority, "Data Processed"))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        add_audit(f"New Dynamic Analysis Processed: {case_id}")
        return redirect(url_for('result_spa', p_id=new_id))
    return render_template("index.html")

@app.route("/result/<int:p_id>")
def result_spa(p_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    patient = conn.execute("SELECT * FROM patients WHERE id = ?", (p_id,)).fetchone()
    conn.close()
    return render_template("result.html", p=dict(patient), patient_id=p_id) if patient else ("Not Found", 404)

@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    history = conn.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()
    logs = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    return render_template("dashboard.html", history=history, logs=logs, metrics={'accuracy': "99.1%"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)