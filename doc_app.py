import os
import json # NEW: To load our doctor data
import requests
from flask import Flask, request, jsonify, render_template, session # NEW: Import session
from flask_cors import CORS
from datetime import timedelta # NEW: To manage session lifetime

# --- Configuration ---
app = Flask(__name__)
CORS(app) 
# ⚠️ NEW: A SECRET_KEY is MANDATORY for using sessions. Change this!
app.config['SECRET_KEY'] = 'a-super-secret-key-that-you-must-change'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30) # Sessions will expire

# --- SambaNova Specific Settings ---
SAMBANOVA_MODEL_NAME = "Meta-Llama-3.1-8B-Instruct" 
MAX_TOKENS = 2048 

# --- ⚠️ SECURITY: NO HARDCODED KEYS. EVER. ---
# Your app will FAIL to start if these are not set. This is intentional.
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY") 
SAMBANOVA_BASE_ENDPOINT = os.getenv("SAMBANOVA_ENDPOINT", "https://api.sambanova.ai/v1")

if not SAMBANOVA_API_KEY:
    raise ValueError("FATAL: SAMBANOVA_API_KEY environment variable not set.")
FINAL_API_URL = f"{SAMBANOVA_BASE_ENDPOINT}/chat/completions"

# --- ⚙️ NEW: Load Doctor Database on Startup ---
try:
    with open('doctors.json', 'r') as f:
        doctors_db = json.load(f)
    print(f"✅ Successfully loaded {len(doctors_db)} doctors from database.")
except FileNotFoundError:
    raise RuntimeError("FATAL: doctors.json not found. Create it before running the app.")

# --- ⚙️ NEW: The "Retrieval" Function (The 'R' in RAG) ---
def find_doctors(query):
    """
    A simple search function to find doctors based on a query.
    This is the core of our retrieval system.
    """
    query_lower = query.lower()
    matches = []
    for doctor in doctors_db:
        # Create a searchable text block for each doctor
        search_haystack = f"{doctor['name']} {doctor['specialty']} {doctor['city']} {' '.join(doctor['keywords'])}".lower()
        if any(word in search_haystack for word in query_lower.split()):
            matches.append(doctor)
    return matches


# --- System Persona ---
CONVERSATION_SYSTEM_MESSAGE = {"role": "system", "content": "You are Baymax, a friendly and helpful healthcare companion. Answer questions based *only* on the context provided. If the context doesn't contain the answer, say you cannot find the information. Always be concise and provide links when available."}


# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # MODIFIED: Use Flask's session, not a global variable
    if 'history' not in session:
        session['history'] = [CONVERSATION_SYSTEM_MESSAGE]
    
    data = request.get_json()
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({"response": "Please send a message."}), 400

    # --- ⚙️ STEP 1: RETRIEVE ---
    retrieved_doctors = find_doctors(user_message)
    context_str = "No specific doctor information found in the database."
    if retrieved_doctors:
        # Convert found doctors to a string to inject into the prompt
        context_str = json.dumps(retrieved_doctors)

    # --- ⚙️ STEP 2: AUGMENT ---
    # Create the prompt for the LLM, including the retrieved context
    augmented_prompt = f"""
    Context from our database:
    ---
    {context_str}
    ---
    Based on the context above, answer the user's request: "{user_message}"
    """
    
    # MODIFIED: Append the REAL user message for history, but we send the augmented one to the AI
    session['history'].append({"role": "user", "content": user_message})

    # The messages list sent to the API is now built dynamically
    messages_for_api = [
        CONVERSATION_SYSTEM_MESSAGE,
        {"role": "user", "content": augmented_prompt} # We send the special prompt
    ]

    headers = {"Authorization": f"Bearer {SAMBANOVA_API_KEY}", "Content-Type": "application/json"}
    request_data = {
        "model": SAMBANOVA_MODEL_NAME, 
        "messages": messages_for_api, 
        "max_tokens": MAX_TOKENS, 
        "temperature": 0.5 
    }

    try:
        response = requests.post(FINAL_API_URL, json=request_data, headers=headers)
        response.raise_for_status() 
        api_data = response.json()
        
        bot_response = api_data['choices'][0]['message']['content'].strip()
        # MODIFIED: Add the bot's response to the session history
        session['history'].append({"role": "assistant", "content": bot_response})
        session.modified = True # Tell Flask the session has changed

        return jsonify({"response": bot_response})

    except Exception as e:
        # A simpler, more robust error handler
        return jsonify({"response": f"An error occurred: {e}"}), 500

@app.route('/reset', methods=['POST'])
def reset_chat():
    """Endpoint to clear the conversation history for the current user."""
    # MODIFIED: Clear the session, not the global variable
    session.pop('history', None) 
    return jsonify({"status": "ok", "message": "Your conversation has been reset."})

# --- Main Run Block ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
