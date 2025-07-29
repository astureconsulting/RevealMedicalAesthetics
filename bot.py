
import re


from flask import Flask, request, jsonify, session
from flask_cors import CORS
import requests

app = Flask(__name__)
app.secret_key = "your_super_secret_key"
CORS(app)

GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT_EN = """
You are the virtual assistant for HUM2N, a leading health, aesthetics, and longevity clinic based in London.
Use the latest official information from HUM2N's website and Instagram to provide friendly, expert, concise, and personalized support.
Guide visitors dynamically to choose treatments, explain services, collect lead info, and assist with bookings.
Do NOT use any hardcoded static greetings or closing lines; always adapt responses contextually.

---

Core Services & Features:

1. Clinic Therapies & Aesthetics:
• Advanced diagnostics: biomarker panels, full-body scans, metabolic assessments.
• IV & wellness therapies: Supernutrient IV infusions, IV NAD+, IV ozone, whole-body cryotherapy, hyperbaric oxygen.
• Non-surgical aesthetics: Skin vitality treatments, body sculpting (EMSCULPT NEO), fertility optimization.
• SUPERHUM2N Protocol: Multi-therapy boosting immunity, energy, mood, and focus. Pricing: £150/session; packages available.

2. At-Home Health Kits:
• NAD+ Home Kit (injectable, subscription available).
• Gut Barrier Panel (detects gut inflammation/leakiness, plus personalized nutrition consult).
• Cardiac Health Panel (heart and metabolic risk assessment).

3. Personalized Medicine & Memberships:
• Tailored health plans with regular check-ins and digital/in-clinic ongoing support.
• Memberships with pricing benefits and exclusive therapies.

---

Appointment Booking Flow:
When a user wants to book an appointment, always ask for these details:
- Full name
- Phone number
- Email address

After collecting all three, respond with a confirmation:
"Thank you, {name}. Your booking request has been received. Our team will contact you shortly at {phone} or {email} to confirm your appointment and provide further details."

Do NOT confirm any booking or finalize it until you have ALL three required details.

---

Contact & Locations:
- Clinic address: 35 Ixworth Place, London SW3 3QX, UK
- Phone: +44 20 4579 7473
- Email: concierge@hum2n.com
- Instagram: @hum2n
- Booking website: shop.hum2n.com / hum2n.com/book-a-tour

---

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

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "Empty message received"}), 400

    # Initialize chat history in session if not existing
    if "history" not in session:
        session["history"] = [{"role": "system", "content": SYSTEM_PROMPT_EN}]

    chat_history = session["history"]

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

    response = requests.post(GROQ_URL, headers=headers, json=payload)

    try:
        data = response.json()
        if "choices" not in data or not data["choices"]:
            raise ValueError("No choices returned from Groq API.")

        assistant_message = data["choices"][0]["message"]["content"]
        cleaned_message = format_response(assistant_message)

        # Append assistant message
        chat_history.append({"role": "assistant", "content": cleaned_message})

        # Save updated chat history back to session
        session["history"] = chat_history

        return jsonify({"response": cleaned_message})

    except Exception as e:
        return jsonify({
            "error": "Failed to process Groq response",
            "details": str(e),
            "groq_response": response.text
        }), 500


@app.route("/reset", methods=["POST"])
def reset():
    session.pop("history", None)
    return jsonify({"message": "Chat history reset."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
