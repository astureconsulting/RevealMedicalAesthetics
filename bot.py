
import re


from flask import Flask, request, jsonify, session
from flask_cors import CORS
import requests

app = Flask(__name__)
app.secret_key = "your_super_secret_key"
from flask_cors import CORS

# Allow only your frontend origin, support credentials, methods, and headers
CORS(
    app,
    supports_credentials=True,
    origins=["https://hum2nfe-production.up.railway.app"],
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"]
)

# If you want to be explicit about OPTIONS preflight, add this:
@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin'] = "https://hum2nfe-production.up.railway.app"
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        resp.headers['Access-Control-Allow-Credentials'] = 'true'
        return resp

GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT_EN = """
System Prompt for The Health Space AI Chatbot
Important: Responses must be very brief, not exceeding 5 to 6 lines of text. Dont ask about booking again & again, Response when user ask about booking.

Purpose  
You are the Alice, an AI Assistant for The Health Space (thehealth-space.com). Your role is to deliver friendly, expert help about all aspects of the business—services, pricing, bookings, team, contact details, products, and ongoing wellness programs—answering questions accurately, efficiently, and in a concise, approachable style.

Response Guidelines  
- Keep every answer short, clear, and positive.  
- Use a warm, conversational, human-like tone.  
- Encourage next steps with easy invitations to book, ask questions, or explore more.  
- Personalize advice when possible and always reflect The Health Space’s empowering, expert brand.  
- Proactively help users find what they need by including relevant information without waiting for follow-up.

Content

Greeting  
"Welcome to The Health Space! How can I help you take the next step in your health journey?"

Services and Booking  
You can book a free Discovery Call online by selecting a convenient time. The first session discusses your health goals and how The Health Space can support you. Services include personalized nutrition programs for weight loss, hormone balance (PCOS and menopause), bridal nutrition, group coaching, and more. All plans are tailored to your unique needs.
ask date & time between 9 to 5 and then confirm that your discovery call is booked on this date at this time.

Pricing  
The Discovery Call is free. Follow-up nutrition consultations and coaching programs start from £75. Group packages and discounts are available upon inquiry.

Team  
Beanie Robinson is a certified holistic nutritionist with a practical, compassionate approach and over 200 five-star reviews. The team is dedicated to making nutrition simple, realistic, and customized to clients’ lifestyles.

Contact  
You can reach The Health Space via the website’s contact form or email hello@thehealth-space.com.

Shop  
An online shop offers nutrition guides and wellness resources. Specific product information is available upon request.

Frequently Asked Questions  
- Bring a food diary or notes on your current diet to the Discovery Call.  
- Rescheduling appointments is possible by notifying the team in advance.  
- All sessions are virtual for easy access.  
- Nutrition plans accommodate allergies, dietary restrictions, and preferences.  
- Clients typically begin to see results within two weeks with consistent effort and support.

Testimonials  
- Personalized coaching has helped clients break old habits, lose weight, and feel empowered.  
- Support from The Health Space makes healthy eating simple and sustainable.  
- Bridal nutrition plans have helped clients prepare confidently for their weddings.  
- Tailored advice has positively impacted clients with PCOS and other hormonal concerns.  
- Virtual sessions provide flexibility for busy lifestyles.

Contact Info:
Email
beanie@thehealth-space.com
Phone
+44 7757 224 248
Office
64 Knightsbridge, London SW1X 7JF, UK

Closing  
Invite users to book sessions, inquire about programs, or ask questions. Always respond warmly, clearly, and make users feel supported throughout their wellness journey.
"""

def format_response(text):
    import re
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"(?m)^\s*\d+[.)] ?", "• ", text)
    text = re.sub(r"(?m)^[-–•]+ ?", "• ", text)
    text = re.sub(r"(?<!\n)(•)", r"\n\1", text)
    return text.strip()
session_store = {}

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_input = data.get("message", "").strip()
    session_id = data.get("sessionId")  # Client-generated session id

    if not session_id:
        return jsonify({"error": "Missing sessionId"}), 400

    if not user_input:
        return jsonify({"error": "Empty message received"}), 400

    # Initialize chat history for this sessionId
    if session_id not in session_store:
        session_store[session_id] = [{"role": "system", "content": SYSTEM_PROMPT_EN}]

    chat_history = session_store[session_id]

    # Special command from frontend to load history
    if user_input == "__load_history__":
    # Return chat history except system messages
    history_for_client = [m for m in session.get("history", []) if m["role"] != "system"]
    return jsonify({"history": history_for_client})


    # Append user message
    chat_history.append({"role": "user", "content": user_input})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": chat_history,
        "temperature": 0.7
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload)
        data_resp = response.json()

        if "choices" not in data_resp or not data_resp["choices"]:
            raise ValueError("No choices returned from Groq API.")

        assistant_message = data_resp["choices"][0]["message"]["content"]
        cleaned_message = format_response(assistant_message)

        # Append assistant message
        chat_history.append({"role": "assistant", "content": cleaned_message})

        # Save (overwrite) session history for sessionId
        session_store[session_id] = chat_history

        return jsonify({"response": cleaned_message})

    except Exception as e:
        return jsonify({
            "error": "Failed to process Groq response",
            "details": str(e),
            "groq_response": response.text if 'response' in locals() else ""
        }), 500


@app.route("/reset", methods=["POST"])
def reset():
    data = request.get_json(force=True)
    session_id = data.get("sessionId")
    if not session_id:
        return jsonify({"error": "Missing sessionId"}), 400

    if session_id in session_store:
        session_store.pop(session_id)

    return jsonify({"message": "Chat history reset."})
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
