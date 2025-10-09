import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# --- Configuration ---
app = Flask(__name__)
CORS(app) 

# --- SambaNova Specific Settings ---
# You MUST replace this with a model ID that is available in your SambaNova account.
SAMBANOVA_MODEL_NAME = "Meta-Llama-3.1-8B-Instruct" 

# **FIX: Define a clear maximum token limit (or a very high number to simulate no limit)**
MAX_TOKENS = 2048 

# Load credentials and endpoint URL from environment variables first
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY") 
SAMBANOVA_BASE_ENDPOINT = os.getenv("SAMBANOVA_ENDPOINT") 

# Check for required credentials and use fallbacks
if not SAMBANOVA_API_KEY or not SAMBANOVA_BASE_ENDPOINT:
    print("WARNING: Using hardcoded fallback credentials. Set environment variables for security.")
    SAMBANOVA_API_KEY = "7ebdda92-a86d-4949-b373-2eee9fe1617c"
    SAMBANOVA_BASE_ENDPOINT = "https://api.sambanova.ai/v1" 

FINAL_API_URL = "https://api.sambanova.ai/v1/chat/completions"


# --- Routes ---

@app.route('/')
def index():
    # NOTE: The client-side template name needs to match. 
    # Your HTML file was named 'chatindex.html' in the initial prompt, 
    # but the Python code calls for 'index.html'. I will use 'index.html' 
    # as per this file, assuming you renamed or moved the client file.
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({"response": "Please send a message."}), 400

    headers = {
        "Authorization": f"Bearer {SAMBANOVA_API_KEY}",
        "Content-Type": "application/json",
    }

    request_data = {
        "model": SAMBANOVA_MODEL_NAME, 
        "messages": [
            {"role": "user", "content": user_message}
        ],
        # **FIX: Use the new, higher MAX_TOKENS variable**
        "max_tokens": MAX_TOKENS, 
        "temperature": 0.7 
    }

    try:
        response = requests.post(FINAL_API_URL, json=request_data, headers=headers)
        response.raise_for_status() 
        api_data = response.json()
        
        # --- Extract the AI Response ---
        if 'choices' in api_data and api_data['choices']:
            bot_response = api_data['choices'][0]['message']['content'].strip()
        else:
            bot_response = f"The AI returned an unexpected response format: {api_data}"

        return jsonify({"response": bot_response})

    except requests.exceptions.HTTPError as errh:
        error_detail = response.json().get('detail', str(errh)) if 'response' in locals() and response.content else str(errh)
        return jsonify({"response": f"API Error ({response.status_code}): {error_detail}. Check your API Key and Model ID ({SAMBANOVA_MODEL_NAME})."}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"response": f"Connection Error: {e}"}), 500
    except Exception as e:
        return jsonify({"response": f"An unexpected error occurred: {e}"}), 500

# --- Main Run Block ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
