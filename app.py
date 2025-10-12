import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# --- Configuration ---
app = Flask(__name__)
CORS(app) 

# --- Gemini API Settings ---
# We will use a standard, fast chat model for this companion
GEMINI_MODEL_NAME = "gemini-2.5-flash-preview-05-20" 

# Define a clear maximum token limit for the bot's response
MAX_TOKENS = 2048 
# Set a creative temperature for the model
TEMPERATURE = 0.7

# Load credentials from environment variables first
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

# Check for required credentials and use the provided hardcoded key as fallback
if not GEMINI_API_KEY:
    print("WARNING: Using hardcoded fallback API key. Set environment variable GEMINI_API_KEY for security.")
    # Using the key provided by the user
    GEMINI_API_KEY = "AIzaSyCYOUsVToqKD61Ln2gSjQva05nX4d2_AtA"

# Construct the final API URL
FINAL_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent"

# --- Conversation Memory Storage ---
# The system message sets the AI's persona and is sent separately in the Gemini API payload
CONVERSATION_SYSTEM_MESSAGE = "You are Baymax, a friendly, compassionate, and helpful healthcare companion from the movie 'Big Hero 6'. You provide health and first-aid advice, but always remind the user that you are an AI and not a substitute for a human doctor. Keep your tone gentle, supportive, and informative."

# Stores the list of message dicts (role and content) for conversation context
# Starts empty, system instruction is passed in the request body
conversation_history = []

# --- Routes ---

@app.route('/')
def home():
    """Renders a simple HTML page, though the front-end seems to use separate files."""
    return "Backend is running. Access the chat interface via chatindex.html."

@app.route('/chat', methods=['POST'])
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
            # API key is sent in the header for the Generative Language API
            'x-goog-api-key': GEMINI_API_KEY
        }

        # The payload includes the entire history and the system instruction separately
        payload = {
            "contents": conversation_history,
            # FIX: Renamed 'config' to 'generationConfig' as required by the API
            "generationConfig": {
                "maxOutputTokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
            },
            # System instruction is used to define the model's persona
            "systemInstruction": {
                "parts": [
                    {"text": CONVERSATION_SYSTEM_MESSAGE}
                ]
            }
        }
        
        # 3. Make the API Call
        response = requests.post(FINAL_API_URL, headers=headers, json=payload)
        response.raise_for_status() # Will raise an exception for bad HTTP status codes (4xx or 5xx)

        # 4. Extract and process the response
        json_response = response.json()
        
        # Check if we got a valid response candidate
        candidates = json_response.get('candidates', [])
        if not candidates:
            # Check for block reason if no candidates are present
            prompt_feedback = json_response.get('promptFeedback', {})
            safety_ratings = prompt_feedback.get('safetyRatings', [])
            block_reason = prompt_feedback.get('blockReason', 'Unknown reason')
            
            if safety_ratings:
                # Format safety ratings for a useful error message
                rating_details = ", ".join([
                    f"{r['category'].split('_')[-1]}: {r['probability']}" 
                    for r in safety_ratings
                ])
                raise Exception(f"Request blocked. Reason: {block_reason}. Safety scores: {rating_details}")
            
            raise Exception("Gemini API returned no response candidates.")
            
        candidate = candidates[0]
        parts = candidate.get('content', {}).get('parts', [])
        
        if not parts or not parts[0].get('text'):
            raise Exception("Gemini API returned an empty text response.")
            
        bot_response_text = parts[0].get('text')
        
        # 5. Append the model's response to the conversation history
        new_model_message = {"role": "model", "parts": [{"text": bot_response_text}]}
        conversation_history.append(new_model_message)
        
        return jsonify({"response": bot_response_text})

    except requests.exceptions.HTTPError as errh:
        # On API error, remove the last user message so it can be retried or not pollute the history
        if conversation_history and conversation_history[-1]['role'] == 'user':
            conversation_history.pop()
        
        # Try to extract the error message from the response body if available
        error_detail = "Unknown error"
        try:
            error_detail = response.json().get('error', {}).get('message', str(errh))
        except:
            error_detail = str(errh)
            
        return jsonify({"response": f"API Error ({response.status_code}): {error_detail}. Check your API Key or model name ({GEMINI_MODEL_NAME})."}), 500
        
    except requests.exceptions.RequestException as e:
        # Connection error, DNS failure, etc.
        if conversation_history and conversation_history[-1]['role'] == 'user':
            conversation_history.pop()
        return jsonify({"response": f"Connection Error: Could not reach the Gemini API endpoint. Details: {e}"}), 500
        
    except Exception as e:
        # General unexpected errors
        if conversation_history and conversation_history[-1]['role'] == 'user':
            conversation_history.pop()
        return jsonify({"response": f"An unexpected internal error occurred: {e}"}), 500


@app.route('/reset', methods=['POST'])
def reset_chat():
    """Endpoint to clear the conversation history."""
    global conversation_history
    # Reset history to an empty list
    conversation_history = []
    return jsonify({"status": "ok", "message": "Conversation history reset."})

# --- Main Run Block ---
if __name__ == '__main__':
    # Flask will run on http://0.0.0.0:5000/
    app.run(host='0.0.0.0', port=5000, debug=True)
