import os
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS # Ensure this is installed: pip install flask-cors

# --- Configuration for the Data Search Feature ---
app = Flask(__name__)
CORS(app) 

# FIX: Use os.path functions to construct an absolute path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_FILE_NAME = 'medical_data.json'
DATA_FILE_PATH = os.path.join(BASE_DIR, DATA_FILE_NAME)

def load_data():
    """Loads the medical data from the JSON file using the absolute path."""
    try:
        # Use the fixed absolute path
        with open(DATA_FILE_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {DATA_FILE_PATH} not found. Please ensure it is in the same directory as fadapp1.py.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {DATA_FILE_PATH}. Check JSON structure.")
        return []

# --- API Endpoint ---
@app.route('/search_data', methods=['POST'])
def search_data():
    """
    Accepts a 'keyword' and returns matching medical conditions.
    """
    # 1. Get the keyword from the incoming JSON request
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip().lower()
    except Exception:
        return jsonify({'error': 'Invalid JSON format.'}), 400

    if not keyword:
        return jsonify({'results': [], 'message': 'Please provide a keyword to search.'})

    # 2. Load the data
    medical_records = load_data()
    
    # 3. Perform the keyword search (simple matching)
    matching_results = []
    
    # Check if the keyword is present in the name, symptoms, or treatment
    for record in medical_records:
        # Create a single searchable string from the record's values
        searchable_text = f"{record.get('name', '')} {record.get('symptoms', '')} {record.get('treatment', '')}".lower()
        
        if keyword in searchable_text:
            matching_results.append(record)

    # 4. Return the results
    if matching_results:
        return jsonify({
            'results': matching_results,
            'message': f"Found {len(matching_results)} result(s) for '{keyword}'."
        })
    else:
        return jsonify({
            'results': [],
            'message': f"No results found for '{keyword}'. Help update our database at mkure@gmail.com"
        })

# --- Web Route for the new Search Page ---
@app.route('/fadindex1.html')
def doc_page():
    # Renders the HTML file for the data search interface
    return render_template('fadindex1.html')

# --- Main Run Block ---
if __name__ == '__main__':
    # Flask will run on http://0.0.0.0:5001/
    # NOTE: It's common to run this on a different port (e.g., 5001) if app.py is already on 5000.
    app.run(host='0.0.0.0', port=5001, debug=True)
