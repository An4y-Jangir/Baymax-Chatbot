import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# --- Configuration ---
app = Flask(__name__)
CORS(app) 

# --- SambaNova Specific Settings ---
# You MUST replace this with a model ID that is available in your SambaNova account.
# Common example:
SAMBANOVA_MODEL_NAME = "Meta-Llama-3.1-8B-Instruct" 

# Load credentials and endpoint URL from environment variables first
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY") 
SAMBANOVA_BASE_ENDPOINT = os.getenv("SAMBANOVA_ENDPOINT") 

# Check for required credentials and use fallbacks
if not SAMBANOVA_API_KEY or not SAMBANOVA_BASE_ENDPOINT:
    print("WARNING: Using hardcoded fallback credentials. Set environment variables for security.")
    SAMBANOVA_API_KEY = "7ebdda92-a86d-4949-b373-2eee9fe1617c"
    SAMBANOVA_BASE_ENDPOINT = "https://api.sambanova.ai/v1" # Use the base URL here

# **THE FIX:** Construct the final API URL by appending the model path
# The final endpoint often looks like: https://api.sambanova.ai/v1/predict/model_name
# NOTE: The exact structure might vary; check your SambaNova documentation, 
# but this is a common structure for dedicated prediction endpoints.
# If using the base '/v1/chat/completions' from the previous step, you may need a different URL structure.
# Let's try the common '/predict/' structure.
# If the '/v1/chat/completions' approach truly doesn't work, this is a strong alternative.

# Let's stick closer to the error message structure and assume the model ID is the issue:
# For true OpenAI compatibility (which uses /chat/completions), the model ID SHOULD be in the body.
# If the 404 persists, we will try the '/predict' structure below.

# --- The /chat/completions endpoint (Assuming the base works and the model body is key) ---
# Use the endpoint you previously set.
FINAL_API_URL = "https://api.sambanova.ai/v1/chat/completions"


# --- Routes ---

@app.route('/')
def index():
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

    # **THE FIX:** The Model Name is NOW CORRECTLY POPULATED.
    request_data = {
        "model": SAMBANOVA_MODEL_NAME, # <--- **FIXED: This is now a variable with a real ID**
        "messages": [
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 100,
        "temperature": 0.7 
    }

    try:
        # Use the finalized endpoint URL
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
        # Include more error detail if available
        error_detail = response.json().get('detail', str(errh)) if 'response' in locals() and response.content else str(errh)
        return jsonify({"response": f"API Error ({response.status_code}): {error_detail}. Check your API Key and Model ID ({SAMBANOVA_MODEL_NAME})."}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"response": f"Connection Error: {e}"}), 500
    except Exception as e:
        return jsonify({"response": f"An unexpected error occurred: {e}"}), 500

# --- Main Run Block ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
