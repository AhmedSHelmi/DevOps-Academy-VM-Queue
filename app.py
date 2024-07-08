from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import uuid
import threading
import time
import sqlite3
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
CORS(app)

DATABASE = 'jobs.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    return conn

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-tokens')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 403
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['username']
        except:
            return jsonify({'message': 'Token is invalid!'}), 403
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password are required!'}), 400
    
    username = data['username']
    password = data['password']
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Username already exists!'}), 400
    finally:
        conn.close()
    
    return jsonify({'message': 'Registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password are required!'}), 400
    
    username = data['username']
    password = data['password']
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'message': 'Login failed!'}), 401
    
    token = jwt.encode({'username': username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
    
    return jsonify({'token': token})

@app.route('/request-vm', methods=['POST'])
@token_required
def request_vm(current_user):
    # Generate a random key
    key = str(uuid.uuid4())
    
    # Get user ID
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (current_user,))
    user_id = cursor.fetchone()[0]
    
    # Store initial job status as 'REQUESTED' in the database
    cursor.execute('INSERT INTO jobs (key, user_id, status, message) VALUES (?, ?, ?, ?)', (key, user_id, 'REQUESTED', ''))
    conn.commit()
    conn.close()
    
    # Create response with the key in the headers
    response = make_response(jsonify({'message': 'VM request received'}))
    response.headers['Automation-Key'] = key
    return response

@app.route('/create-job', methods=['POST'])
@token_required
def create_job(current_user):
    key = request.headers.get('Automation-Key')
    if not key:
        return jsonify({'error': 'Missing Automation-Key'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT jobs.key, users.username FROM jobs JOIN users ON jobs.user_id = users.id WHERE jobs.key = ? AND users.username = ?', (key, current_user))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        return jsonify({'error': 'Invalid Automation-Key or unauthorized access'}), 400
    
    # Start the job with status 'IN_PROGRESS'
    cursor.execute('UPDATE jobs SET status = ? WHERE key = ?', ('IN_PROGRESS', key))
    conn.commit()
    
    # Simulate job processing in a separate thread
    def process_job(key, username):
        time.sleep(2)  # Simulate job processing delay
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        vm_name = f"{username}_vm_{timestamp}"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE jobs SET status = ?, message = ? WHERE key = ?', ('DONE', f'VM created: {vm_name}', key))
        conn.commit()
        conn.close()
    
    threading.Thread(target=process_job, args=(key, current_user)).start()
    conn.close()
    
    return jsonify({'status': 'IN_PROGRESS'})

@app.route('/job-status', methods=['GET'])
@token_required
def job_status(current_user):
    key = request.headers.get('Automation-Key')
    if not key:
        return jsonify({'error': 'Missing Automation-Key'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT jobs.status, jobs.message FROM jobs JOIN users ON jobs.user_id = users.id WHERE jobs.key = ? AND users.username = ?', (key, current_user))
    job = cursor.fetchone()
    conn.close()
    
    if not job:
        return jsonify({'error': 'Invalid Automation-Key or unauthorized access'}), 400
    
    return jsonify({'status': job[0], 'message': job[1]})

if __name__ == '__main__':
    app.run(debug=True)
