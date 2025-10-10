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

# **FIX: Define a clear maximum token limit**
MAX_TOKENS = 2048 

# Load credentials and endpoint URL from environment variables first
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY") 
SAMBANOVA_BASE_ENDPOINT = os.getenv("SAMBANOVA_ENDPOINT") 

# Check for required credentials and use fallbacks
if not SAMBANOVA_API_KEY or not SAMBANOVA_BASE_ENDPOINT:
    print("WARNING: Using hardcoded fallback credentials. Set environment variables for security.")
    SAMBANOVA_API_KEY = "5f4a6ce6-40b5-4db8-b485-e5f1a3392af3"
    SAMBANOVA_BASE_ENDPOINT = "https://api.sambanova.ai/v1" 

FINAL_API_URL = "https://api.sambanova.ai/v1/chat/completions"

# --- Conversation Memory Storage ---
# Stores the list of message dicts (role and content) for context
# Start with a system message to set the AI's persona
CONVERSATION_SYSTEM_MESSAGE = {"role": "system", "content": "You are Baymax, a friendly, compassionate, and helpful healthcare companion. Keep your answers concise and supportive."}
conversation_history = [CONVERSATION_SYSTEM_MESSAGE]


# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # Use the global history variable
    global conversation_history

    data = request.get_json()
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({"response": "Please send a message."}), 400

    headers = {
        "Authorization": f"Bearer {SAMBANOVA_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # 1. Add the new user message to the history
    conversation_history.append({"role": "user", "content": user_message})

    request_data = {
        "model": SAMBANOVA_MODEL_NAME, 
        # 2. Send the entire conversation history to the API
        "messages": conversation_history, 
        "max_tokens": MAX_TOKENS, 
        "temperature": 0.7 
    }

    try:
        response = requests.post(FINAL_API_URL, json=request_data, headers=headers)
        # Check if the response status is 4xx or 5xx
        response.raise_for_status() 
        api_data = response.json()
        
        # --- Extract the AI Response ---
        if 'choices' in api_data and api_data['choices']:
            bot_response = api_data['choices'][0]['message']['content'].strip()
            # 3. Add the bot's response to the history for the next turn
            conversation_history.append({"role": "assistant", "content": bot_response})
        else:
            bot_response = f"The AI returned an unexpected response format: {api_data}"
            # If the API fails to respond correctly, remove the last user message to prevent sending it without context
            if conversation_history and conversation_history[-1]['role'] == 'user':
                conversation_history.pop() 

        return jsonify({"response": bot_response})

    # --- ENHANCED EXCEPTION HANDLING ---
    
    except requests.exceptions.HTTPError as errh:
        # On API error, remove the last user message
        if conversation_history and conversation_history[-1]['role'] == 'user':
            conversation_history.pop()
            
        error_status_code = response.status_code if 'response' in locals() else 500
        
        # Try to parse the API's detailed error message
        error_detail = "Unknown API Error"
        if 'response' in locals() and response.content:
            try:
                error_detail = response.json().get('detail', str(errh))
            except requests.exceptions.JSONDecodeError:
                error_detail = response.text # Use raw text if JSON parsing fails
        
        # Explicitly handle the 429 error
        if error_status_code == 429:
            return jsonify({"response": f"API Error ({error_status_code} TOO MANY REQUESTS): You have exceeded the rate limit. Please wait a moment before trying again."}), 429

        # Handle all other HTTP errors (4xx/5xx)
        return jsonify({"response": f"API Error ({error_status_code}): {error_detail}. Check your API Key and Model ID ({SAMBANOVA_MODEL_NAME})."}), error_status_code
        
    except requests.exceptions.ConnectionError as errc:
        # Catch connection failures (e.g., DNS error, connection refused)
        if conversation_history and conversation_history[-1]['role'] == 'user':
            conversation_history.pop()
        return jsonify({"response": f"Connection Error: Could not connect to the SambaNova API: {errc}"}), 503
        
    except requests.exceptions.Timeout as errt:
        # Catch timeout errors
        if conversation_history and conversation_history[-1]['role'] == 'user':
            conversation_history.pop()
        return jsonify({"response": f"Timeout Error: The request to the SambaNova API timed out: {errt}"}), 504
        
    except requests.exceptions.RequestException as e:
        # Catch any other requests-related exception (e.g., invalid URL)
        if conversation_history and conversation_history[-1]['role'] == 'user':
            conversation_history.pop()
        return jsonify({"response": f"A general Request Error occurred: {e}"}), 500
        
    except Exception as e:
        # Catch unexpected Python errors
        if conversation_history and conversation_history[-1]['role'] == 'user':
            conversation_history.pop()
        return jsonify({"response": f"An unexpected internal error occurred: {e}"}), 500

@app.route('/reset', methods=['POST'])
def reset_chat():
    """Endpoint to clear the conversation history."""
    global conversation_history
    # Reset history back to just the system message
    conversation_history = [CONVERSATION_SYSTEM_MESSAGE]
    return jsonify({"status": "ok", "message": "Conversation history reset."})

# --- Main Run Block ---
if __name__ == '__main__':
    # Setting debug to True allows for immediate feedback during development
    app.run(host='0.0.0.0', port=5000, debug=True)
