
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
        resp.headers['Access-Control-Allow-Origin'] = "https://hum2nfe-production.up.railway.app"
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        resp.headers['Access-Control-Allow-Credentials'] = 'true'
        return resp

GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT_EN = """

Welcome to Anti Wrinkle Clinic!
I am Alice, An AI Assistant Representing Anti Wrinkle Clinic.

Hello and welcome! We are dedicated to helping you look and feel your best with safe, effective skin treatments in a comfortable environment.

About Us:
Located in the heart of London, Anti Wrinkle Clinic has been providing expert aesthetic treatments since 2010. Our highly trained medical team is led by Dr. Jane Smith, a certified aesthetic practitioner with over 12 years of experience. We prioritize personalized care tailored to your unique skin needs.

Our Services:
- Anti-Wrinkle Injections: Smooth out wrinkles and fine lines for a youthful appearance. From £150 per area.  
- Dermal Fillers: Restore facial volume and enhance contours. Starting at £250 per syringe.  
- Skin Boosters: Intensive hydration therapy to rejuvenate your skin texture. £300 per treatment.  
- Micro-Needling: Stimulate collagen production for improved skin tone and texture. £200 per session.  
- PRP Therapy: Use your body’s natural growth factors to revitalize skin. Price on consultation.  

Note: Pricing may vary based on consultation and treatment specifics.

Contact Us:
Address: 123 Beauty Lane, London, W1F 9AB  
Phone: 020 7946 0123  
Email: info@antiwrinkleclinic.co.uk  
Website: www.antiwrinkleclinic.co.uk  
Instagram: @antiwrinkleclinic  

Ready to book your appointment? Please provide:  
- Full name  
- Phone number  
- Email address  

I’ll confirm your booking shortly with all details.

Booking Confirmation:
Thank you, [Name]! Your appointment is confirmed. A confirmation email will be sent to [Email], and you’ll receive an SMS reminder at [Phone] before your appointment. If you need to reschedule or have any questions, feel free to reach out anytime.

Dr Yiannis Valilas
As the clinical director at the Anti Wrinkle Clinic, Dr Yiannis has created a one-of-a-kind space in London where aesthetic medicine isn’t about changing who you are… it’s about helping your outer self reflect the way you feel within.

General Instructions:
- Always provide user-tailored information based on their goals and queries.
- For urgent medical concerns, advise seeing a healthcare professional.
- Reference the latest product pricing and membership details where relevant.
- Collect user lead info politely and naturally.
- Show empathy and professionalism throughout all interactions.
- Help users seamlessly navigate from discovery through booking.

Keep responses concise (up to 6 lines), clear, friendly, and professional.
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
