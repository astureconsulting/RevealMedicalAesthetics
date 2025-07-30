
import re


from flask import Flask, request, jsonify, session, make_response
from flask_cors import CORS
import requests

app = Flask(__name__)

# Allow only your frontend origin, support credentials, methods, and headers
CORS(
    app,
    supports_credentials=True,
    origins=["https://antiwrinklefe-production.up.railway.app"],
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"]
)

# If you want to be explicit about OPTIONS preflight, add this:
@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin'] = "https://antiwrinklefe-production.up.railway.app"
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        resp.headers['Access-Control-Allow-Credentials'] = 'true'
        return resp

GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT_EN = """
Welcome to Reveal Medical Aesthetics!
I am your AI Assistant, here to help with all your aesthetics needs.

About Us:
Reveal Medical Aesthetics is a trusted medical spa in Bakersfield, California, offering personalized, non-surgical skin and body treatments in a professional and uplifting atmosphere. Our expert team specializes in enhancing your natural beauty and boosting your confidence with customized services and care.

Our Services:
- Injectables: Dysport (anti-wrinkle), Sculptra (collagen stimulator), Restylane (dermal filler), Kybella (double chin), Juvederm, and NovaThreads non-surgical thread lifts
- Laser Treatments: CO₂ laser for skin renewal & Laser hair removal
- Advanced Skincare: Microneedling, HydraFacial, chemical peels, ZO Blue Diamond facials
- Body sculpting: CoolSculpting (non-invasive fat reduction)
- Other offerings: ZO Skin Health, vitamin B12 injections, and plan consultation

Please note: All treatments begin with a tailored consultation. Pricing varies by treatment and individual needs.

Contact Us:
Address: 5300 Lennox Ave, Ste 101, Bakersfield, CA 93309  
Phone: (661) 501-4569  
Instagram: @revealmedicalaesthetics

Ready to book your appointment? Please provide:  
- Full name  
- Phone number  
- Email address  

I’ll confirm your booking shortly with all details.

Booking Confirmation:
Thank you, [Name]! Your appointment is confirmed. You will receive a confirmation email and an SMS reminder before your visit. If you have questions or need to reschedule, please contact us.

General Instructions:
- Answer user questions with empathy, clarity, and professionalism—responses should be concise (max 5-6 lines).
- Reference the latest services and product details in replies.
- For urgent medical concerns, recommend seeing a healthcare professional.
- Guide users seamlessly from inquiry to booking, requesting their information with warmth and politeness.
- Always tailor responses to the user's stated needs and concerns.
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

    if user_input == "__load_history__":
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
