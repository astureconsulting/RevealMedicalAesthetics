from flask import Flask, request, jsonify, session
from flask_cors import CORS
import requests
import re

app = Flask(__name__)
app.secret_key = "your_super_secret_key"  # Replace with your real secret key
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "https://hum2nfe-production.up.railway.app/"}})

GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


SYSTEM_PROMPT_HUM2N = """
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
    """Clean up LLM response text by removing markdown asterisks and normalizing bullets."""
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"(?m)^\s*\d+[.)] ?", "• ", text)
    text = re.sub(r"(?m)^[-–•]+ ?", "• ", text)
    text = re.sub(r"(?<!\n)(•)", r"\n\1", text)
    return text.strip()


def is_valid_phone(phone):
    """Basic phone validation: allows digits, optional +, length 7-20."""
    phone_clean = re.sub(r"[^\d+]", "", phone)
    return bool(re.match(r"^\+?[\d]{7,20}$", phone_clean))


def is_valid_email(email):
    """Basic email validation regex."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w{2,}$"
    return bool(re.match(pattern, email.strip()))


def call_groq_api(messages):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.7
    }
    response = requests.post(GROQ_URL, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    if "choices" not in data or not data["choices"]:
        raise ValueError("No choices returned from Groq API.")
    return data["choices"][0]["message"]["content"]


@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "Empty message received"}), 400

    # Initialize chat history & bot state if not present
    if "history" not in session:
        session["history"] = [{"role": "system", "content": SYSTEM_PROMPT_HUM2N}]
    if "bot_state" not in session:
        session["bot_state"] = {
            "awaiting_name": False,
            "awaiting_phone": False,
            "awaiting_email": False,
            "collected_data": {}
        }

    chat_history = session["history"]
    bot_state = session["bot_state"]

    # Booking data collection flow

    # 1) Collect Name
    if bot_state["awaiting_name"]:
        # Save name given by user
        bot_state["collected_data"]["name"] = user_input
        bot_state["awaiting_name"] = False
        # Next ask for phone
        bot_state["awaiting_phone"] = True
        session["bot_state"] = bot_state
        return jsonify({"response": "Thanks! Could you please provide your phone number?"})

    # 2) Collect & validate Phone
    if bot_state["awaiting_phone"]:
        if is_valid_phone(user_input):
            bot_state["collected_data"]["phone"] = user_input
            bot_state["awaiting_phone"] = False
            # Ask for email next
            bot_state["awaiting_email"] = True
            session["bot_state"] = bot_state
            return jsonify({"response": "Great, now please provide your email address."})
        else:
            # Invalid phone format, but user might have asked something else
            # Let LLM answer then politely remind for valid phone
            chat_history.append({"role": "user", "content": user_input})
            try:
                assistant_message = call_groq_api(chat_history)
                cleaned = format_response(assistant_message)
                chat_history.append({"role": "assistant", "content": cleaned})
                session["history"] = chat_history
                reminder = "\n\nBy the way, I still need your phone number to complete your booking. Could you please provide it?"
                return jsonify({"response": cleaned + reminder})
            except Exception as e:
                return jsonify({"error": "Groq API error", "details": str(e)}), 500

    # 3) Collect & validate Email
    if bot_state["awaiting_email"]:
        if is_valid_email(user_input):
            bot_state["collected_data"]["email"] = user_input
            bot_state["awaiting_email"] = False
            session["bot_state"] = bot_state
            # All collected? Confirm booking
            data = bot_state["collected_data"]
            if all(k in data for k in ["name", "phone", "email"]):
                confirmation_msg = (
                    f"Thank you, {data['name']}. Your booking request has been received. "
                    f"Our team will contact you shortly at {data['phone']} or {data['email']} "
                    "to confirm your appointment and provide further details."
                )
                # Reset bot_state after confirmation
                session["bot_state"] = {
                    "awaiting_name": False,
                    "awaiting_phone": False,
                    "awaiting_email": False,
                    "collected_data": {}
                }
                return jsonify({"response": confirmation_msg})
            else:
                # Should not happen, but fallback prompt
                return jsonify({"response": "Thank you. Is there anything else I can assist you with?"})
        else:
            # Invalid email - answer any other user query, then remind for email
            chat_history.append({"role": "user", "content": user_input})
            try:
                assistant_message = call_groq_api(chat_history)
                cleaned = format_response(assistant_message)
                chat_history.append({"role": "assistant", "content": cleaned})
                session["history"] = chat_history
                reminder = "\n\nI still need your valid email address to finalize your booking. Could you please provide it?"
                return jsonify({"response": cleaned + reminder})
            except Exception as e:
                return jsonify({"error": "Groq API error", "details": str(e)}), 500

    # If not awaiting booking info, process normally:

    # Append user message to history
    chat_history.append({"role": "user", "content": user_input})

    # Detect if user wants to start booking flow (basic keyword detection)
    booking_triggers = [
        "book an appointment",
        "schedule a consultation",
        "book a session",
        "appointment",
        "book now",
        "schedule",
        "consultation"
    ]
    if any(trigger in user_input.lower() for trigger in booking_triggers):
        bot_state["awaiting_name"] = True
        bot_state["awaiting_phone"] = False
        bot_state["awaiting_email"] = False
        bot_state["collected_data"] = {}
        session["bot_state"] = bot_state
        session["history"] = chat_history
        return jsonify({"response": "Sure! To book your appointment, may I have your full name please?"})

    # Normal assistant reply from LLM
    try:
        assistant_message = call_groq_api(chat_history)
        cleaned_response = format_response(assistant_message)
        chat_history.append({"role": "assistant", "content": cleaned_response})
        session["history"] = chat_history
        session["bot_state"] = bot_state
        return jsonify({"response": cleaned_response})
    except Exception as e:
        return jsonify({"error": "Groq API error", "details": str(e)}), 500


@app.route("/reset", methods=["POST"])
def reset():
    session.pop("history", None)
    session.pop("bot_state", None)
    return jsonify({"message": "Chat history and state reset."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
