import os
import requests
import sqlite3
from flask import Flask, request, jsonify, session, g
from flask_cors import CORS
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuration ---
app = Flask(__name__)
CORS(app) 

# --- FLASK CONFIGURATION ---
# Use an absolute path for the SQLite database
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'users.db')
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a_very_secret_key_for_mkure_app")
app.permanent_session_lifetime = timedelta(minutes=30) 
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
ADMIN_EMAIL = "admin@mkure.com" # Define the admin email address

# --- DATABASE SETUP (SQLite) ---

def get_db():
    """Connects to the specific database."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # Allows accessing columns by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database and creates the user table."""
    with app.app_context():
        db = get_db()
        # Create the users table if it doesn't exist
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0
            );
        ''')
        db.commit()

def create_admin_if_not_exists():
    """Ensures the designated admin user exists."""
    with app.app_context():
        db = get_db()
        cursor = db.execute("SELECT * FROM users WHERE email = ?", (ADMIN_EMAIL,))
        user = cursor.fetchone()

        if user is None:
            # Create the default admin user with a strong, temporary password
            admin_password = os.environ.get("ADMIN_PASSWORD", "AdminPass123") 
            hashed_password = generate_password_hash(admin_password)
            
            db.execute(
                "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
                ("Admin", ADMIN_EMAIL, hashed_password, 1)
            )
            db.commit()
            print(f"--- IMPORTANT: Admin user created/verified: {ADMIN_EMAIL} (Password: {admin_password}) ---")
        else:
            print(f"Admin user ({ADMIN_EMAIL}) already exists.")

# Initial setup when the app starts
init_db()
create_admin_if_not_exists()


# --- AUTHENTICATION ROUTES ---

@app.route('/register', methods=['POST'])
def register():
    """Handles user registration and stores hashed password in DB."""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({"success": False, "message": "Missing fields."}), 400

    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400
    
    db = get_db()
    try:
        hashed_password = generate_password_hash(password)
        is_admin = 1 if email == ADMIN_EMAIL else 0
        
        db.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            (username, email, hashed_password, is_admin)
        )
        db.commit()
        return jsonify({"success": True, "message": "Registration successful. Please log in."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Email already registered."}), 409
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({"success": False, "message": "An unexpected error occurred."}), 500


@app.route('/login', methods=['POST'])
def login():
    """Handles user login and sets a session."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not all([email, password]):
        return jsonify({"success": False, "message": "Missing email or password."}), 400

    db = get_db()
    cursor = db.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if user and check_password_hash(user['password_hash'], password):
        # Set session variables
        session.permanent = True
        session['user_id'] = user['id']
        session['email'] = user['email']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']
        
        return jsonify({
            "success": True, 
            "message": "Login successful.", 
            "username": user['username'],
            "isAdmin": user['is_admin'] == 1
        }), 200
    else:
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

@app.route('/logout', methods=['POST'])
def logout():
    """Clears the user session."""
    session.pop('user_id', None)
    session.pop('email', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    return jsonify({"success": True, "message": "Logged out successfully."}), 200

def login_required(f):
    """A decorator to ensure a user is logged in before accessing certain endpoints."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"response": "Authorization required. Please log in."}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- GEMINI API Settings (Remains the same) ---
GEMINI_MODEL_NAME = "gemini-2.5-flash-preview-05-20" 
MAX_TOKENS = 2048 
TEMPERATURE = 0.7
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCYOUsVToqKD61Ln2gSjQva05nX4d2_AtA") # Using fallback key
FINAL_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent"
CONVERSATION_SYSTEM_MESSAGE = "You are Baymax, a friendly, compassionate, and helpful healthcare companion from the movie 'Big Hero 6'. You provide health and first-aid advice, but always remind the user that you are an AI and not a substitute for a human doctor. Keep your tone gentle, supportive, and informative."
conversation_history = []

# --- Chat Route (Protected) ---

@app.route('/')
def home():
    return "Backend is running. Access the chat interface via chatindex.html or login.html."

@app.route('/chat', methods=['POST'])
@login_required # Ensure user is logged in to use the chat API
def chat():
    """Endpoint for handling user messages and calling the Gemini API."""
    global conversation_history
    
    try:
        data = request.get_json()
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({"response": "Please enter a message."}), 400

        # 1. Prepare and append the new user message to history
        new_user_message = {"role": "user", "parts": [{"text": user_message}]}
        conversation_history.append(new_user_message)

        # 2. Construct the Gemini API Payload
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': GEMINI_API_KEY
        }

        # The payload includes the entire history and the system instruction separately
        payload = {
            "contents": conversation_history,
            "generationConfig": {
                "maxOutputTokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
            },
            "systemInstruction": {
                "parts": [
                    {"text": CONVERSATION_SYSTEM_MESSAGE}
                ]
            }
        }
        
        # 3. Make the API Call
        response = requests.post(FINAL_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        # 4. Extract and process the response
        json_response = response.json()
        candidates = json_response.get('candidates', [])

        if not candidates or not candidates[0].get('content', {}).get('parts', [{}])[0].get('text'):
            block_reason = json_response.get('promptFeedback', {}).get('blockReason', 'Unknown reason')
            error_msg = f"API returned no response. Block Reason: {block_reason}"
            print(error_msg)
            raise Exception(error_msg)
            
        bot_response_text = candidates[0]['content']['parts'][0]['text']
        
        # 5. Append the model's response to the conversation history
        new_model_message = {"role": "model", "parts": [{"text": bot_response_text}]}
        conversation_history.append(new_model_message)
        
        return jsonify({"response": bot_response_text})

    except requests.exceptions.RequestException as e:
        if conversation_history and conversation_history[-1]['role'] == 'user':
            conversation_history.pop()
        error_detail = str(e)
        if response is not None and response.status_code != 200:
             try:
                error_detail = response.json().get('error', {}).get('message', str(e))
             except:
                pass
        return jsonify({"response": f"Connection Error: Could not reach the Gemini API endpoint. Details: {error_detail}"}), 500
        
    except Exception as e:
        if conversation_history and conversation_history[-1]['role'] == 'user':
            conversation_history.pop()
        return jsonify({"response": f"An unexpected internal error occurred: {e}"}), 500


@app.route('/reset', methods=['POST'])
@login_required
def reset_chat():
    """Endpoint to clear the conversation history."""
    global conversation_history
    conversation_history = []
    return jsonify({"status": "ok", "message": "Conversation history reset."})

# --- Main Run Block ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
