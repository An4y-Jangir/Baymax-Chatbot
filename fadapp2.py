import json
import requests
import urllib3

# --- WARNING ---
# Disabling SSL warnings because we are disabling SSL verification.
# This is insecure and should ONLY be used for local testing on a trusted network.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# --- Configuration ---
app = Flask(__name__, template_folder='.', static_folder='.')
CORS(app)

# --- Gemini API Specific Settings ---
GEMINI_MODEL_NAME = 'gemini-2.5-flash-preview-05-20'
GEMINI_API_KEY = "AIzaSyCXq_bTBP9qgYnAgipdnZJtY9G4nIqPMNA"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
MAX_TOKENS = 2048

# --- System Persona ---
# UPDATED: The system message now explicitly instructs the AI to include the details_link.
SYSTEM_MESSAGE_CONTENT = "You are TARS, a logical and efficient AI assistant. Answer questions based *only* on the context provided about doctors. If the information isn't in the context, say you cannot find it. Be concise and professional. Crucially, for every single doctor you mention, you MUST include their full `details_link` in the response."

# --- Database ---
doctors_db = [
  {
    "id": 1, "name": "Dr. Aarav Sharma", "specialty": "Cardiologist", "city": "Mumbai", "experience_years": 22, "hospital": "Apex Heart Institute", "details_link": "https://example.com/doctors/aarav-sharma", "keywords": ["heart", "blood pressure", "chest pain", "cardiology", "Mumbai"]
  },
  {
    "id": 2, "name": "Dr. Priya Singh", "specialty": "Dermatologist", "city": "Delhi", "experience_years": 15, "hospital": "Capital Skin Clinic", "details_link": "https://example.com/doctors/priya-singh", "keywords": ["skin", "rash", "acne", "dermatology", "Delhi"]
  },
  {
    "id": 3, "name": "Dr. Rohan Joshi", "specialty": "Orthopedic Surgeon", "city": "Bengaluru", "experience_years": 18, "hospital": "Garden City Orthopedics", "details_link": "https://example.com/doctors/rohan-joshi", "keywords": ["bones", "joint pain", "fracture", "orthopedics", "Bengaluru"]
  },
  {
    "id": 4, "name": "Dr. Ananya Reddy", "specialty": "Pediatrician", "city": "Chennai", "experience_years": 25, "hospital": "Marina Children's Hospital", "details_link": "https://example.com/doctors/ananya-reddy", "keywords": ["child", "baby", "pediatrics", "infant", "Chennai"]
  },
  {
    "id": 5, "name": "Dr. Vikram Kumar", "specialty": "Neurologist", "city": "Mumbai", "experience_years": 20, "hospital": "NeuroHealth Center Mumbai", "details_link": "https://example.com/doctors/vikram-kumar", "keywords": ["brain", "spine", "headache", "neurology", "Mumbai"]
  },
  {
    "id": 6, "name": "Dr. Sameera Khan", "specialty": "Oncologist", "city": "Delhi", "experience_years": 28, "hospital": "National Cancer Institute", "details_link": "https://example.com/doctors/sameera-khan", "keywords": ["cancer", "chemotherapy", "oncology", "tumor", "Delhi"]
  },
  {
    "id": 7, "name": "Dr. Arjun Mehta", "specialty": "Gastroenterologist", "city": "Kolkata", "experience_years": 19, "hospital": "Eastern Digestive Health", "details_link": "https://example.com/doctors/arjun-mehta", "keywords": ["stomach", "gut", "digestion", "gastroenterology", "Kolkata"]
  },
  {
    "id": 8, "name": "Dr. Isha Nair", "specialty": "ENT Specialist", "city": "Hyderabad", "experience_years": 14, "hospital": "Deccan ENT Clinic", "details_link": "https://example.com/doctors/isha-nair", "keywords": ["ear", "nose", "throat", "ent", "Hyderabad"]
  },
  {
    "id": 9, "name": "Dr. Siddharth Rao", "specialty": "Pulmonologist", "city": "Pune", "experience_years": 21, "hospital": "Pune Chest & Lung Center", "details_link": "https://example.com/doctors/siddharth-rao", "keywords": ["lungs", "breathing", "asthma", "pulmonology", "Pune"]
  },
  {
    "id": 10, "name": "Dr. Divya Patel", "specialty": "Psychiatrist", "city": "Ahmedabad", "experience_years": 16, "hospital": "Mindful Wellness Clinic", "details_link": "https://example.com/doctors/divya-patel", "keywords": ["mental health", "psychiatry", "depression", "anxiety", "Ahmedabad"]
  },
  {
    "id": 11, "name": "Dr. Kabir Das", "specialty": "Cardiologist", "city": "Delhi", "experience_years": 30, "hospital": "Metro Heart Foundation", "details_link": "https://example.com/doctors/kabir-das", "keywords": ["heart", "cardiology", "hypertension", "Delhi"]
  },
  {
    "id": 12, "name": "Dr. Meera Desai", "specialty": "Endocrinologist", "city": "Bengaluru", "experience_years": 17, "hospital": "Silicon Valley Diabetes Center", "details_link": "https://example.com/doctors/meera-desai", "keywords": ["diabetes", "hormones", "thyroid", "endocrinology", "Bengaluru"]
  },
  {
    "id": 13, "name": "Dr. Neil Gupta", "specialty": "Urologist", "city": "Mumbai", "experience_years": 24, "hospital": "Mumbai Kidney & Urology Clinic", "details_link": "https://example.com/doctors/neil-gupta", "keywords": ["kidney", "urology", "bladder", "Mumbai"]
  },
  {
    "id": 14, "name": "Dr. Fatima Ali", "specialty": "Gynecologist", "city": "Hyderabad", "experience_years": 26, "hospital": "Pearl City Women's Health", "details_link": "https://example.com/doctors/fatima-ali", "keywords": ["women's health", "gynecology", "pregnancy", "Hyderabad"]
  },
  {
    "id": 15, "name": "Dr. Raj Verma", "specialty": "General Physician", "city": "Pune", "experience_years": 12, "hospital": "Pune Community Clinic", "details_link": "https://example.com/doctors/raj-verma", "keywords": ["general", "family doctor", "physician", "Pune"]
  },
  {
    "id": 16, "name": "Dr. Sunita Agarwal", "specialty": "Rheumatologist", "city": "Kolkata", "experience_years": 23, "hospital": "Kolkata Arthritis & Rheuma Care", "details_link": "https://example.com/doctors/sunita-agarwal", "keywords": ["arthritis", "rheumatology", "autoimmune", "Kolkata"]
  },
  {
    "id": 17, "name": "Dr. Imran Baig", "specialty": "Ophthalmologist", "city": "Chennai", "experience_years": 18, "hospital": "Coromandel Eye Institute", "details_link": "https://example.com/doctors/imran-baig", "keywords": ["eyes", "vision", "ophthalmology", "cataract", "Chennai"]
  },
  {
    "id": 18, "name": "Dr. Lavanya Murthy", "specialty": "Dentist", "city": "Bengaluru", "experience_years": 10, "hospital": "Bengaluru Smile Dental", "details_link": "https://example.com/doctors/lavanya-murthy", "keywords": ["teeth", "dentist", "dental", "gums", "Bengaluru"]
  },
  {
    "id": 19, "name": "Dr. Farhan Akhtar", "specialty": "Nephrologist", "city": "Delhi", "experience_years": 27, "hospital": "Indus Kidney Center", "details_link": "https://example.com/doctors/farhan-akhtar", "keywords": ["kidney", "dialysis", "nephrology", "Delhi"]
  },
  {
    "id": 20, "name": "Dr. Preeti Chavan", "specialty": "Allergist", "city": "Mumbai", "experience_years": 16, "hospital": "Mumbai Allergy & Asthma Clinic", "details_link": "https://example.com/doctors/preeti-chavan", "keywords": ["allergy", "immunology", "asthma", "Mumbai"]
  }
]

def find_doctors(query):
    query_lower = query.lower()
    matches = []
    stop_words = {'a', 'for', 'is', 'in', 'of', 'the', 'my', 'i'}
    query_words = [word for word in query_lower.split() if word not in stop_words]
    cleaned_query = " ".join(query_words)

    if not cleaned_query:
        return []

    for doctor in doctors_db:
        if any(keyword in cleaned_query for keyword in doctor['keywords']):
            matches.append(doctor)
            continue
        if doctor['name'].lower() in cleaned_query or doctor['specialty'].lower() in cleaned_query:
            if doctor not in matches:
                matches.append(doctor)
    return matches

# --- Routes ---
@app.route('/')
def index():
    return render_template('fadindex2.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({"response": "Please send a message."}), 400

    # NEW: Handle simple greetings without an API call.
    user_message_lower = user_message.strip().lower()
    if user_message_lower in ['hi', 'hello', 'hey', 'yo']:
        return jsonify({"response": "Hello. How can I help you find a doctor?"})

    retrieved_doctors = find_doctors(user_message)
    context_str = "No relevant doctor information was found in the database."
    if retrieved_doctors:
        context_str = json.dumps(retrieved_doctors)

    augmented_prompt = f"""
    Context from our database:
    ---
    {context_str}
    ---
    Based ONLY on the context above, answer the user's request: "{user_message}"
    """
    
    request_data = {
      "contents": [{"parts": [{"text": augmented_prompt}]}],
      "systemInstruction": {"parts": [{"text": SYSTEM_MESSAGE_CONTENT}]},
      "generationConfig": {"temperature": 0.5, "maxOutputTokens": MAX_TOKENS}
    }

    try:
        # NOTE: verify=False is insecure and for local testing only.
        response = requests.post(API_URL, json=request_data, verify=False)
        response.raise_for_status()
        api_data = response.json()
        
        bot_response = "Sorry, I couldn't generate a response."
        # Safely parse the response from Gemini
        if 'candidates' in api_data and api_data['candidates']:
            first_candidate = api_data['candidates'][0]
            if 'content' in first_candidate and 'parts' in first_candidate['content'] and first_candidate['content']['parts']:
                bot_response = first_candidate['content']['parts'][0].get('text', bot_response).strip()

        return jsonify({"response": bot_response})
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request to Gemini API failed: {e}")
        return jsonify({"response": "An error occurred while contacting the AI service."}), 500
    except (KeyError, IndexError) as e:
        print(f"ERROR: Unexpected API response format: {e}\nResponse: {api_data}")
        return jsonify({"response": "The AI service returned an unexpected response."}), 500
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        return jsonify({"response": "An unexpected server error occurred."}), 500

# --- Main Run Block ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=False)

