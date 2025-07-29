
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import requests

app = Flask(__name__)
app.secret_key = "your_super_secret_key"
CORS(app)

GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT_EN = """
You are an AI assistant well-informed about WeBring, a digital solutions agency.
Use the following company information to provide accurate, relevant, human like and professional responses when asked about WeBring’s services, team, or company details.
Give every response in a human-like, natural tone using up to 6 sentences—concise, friendly, and professional. Dont exceed 6 lines.
Company Overview:
WeBring is a digital solutions agency specializing in full-cycle website and mobile application development, digital marketing, UI/UX design, and related IT consulting services. Based in Lahore, Pakistan, the team serves startups and established businesses worldwide. Founded in 2017, WeBring has completed over 100 projects across diverse sectors.

Company Details:
- Industry: IT Services & Consulting, Web & App Development
- Headquarters: 65-Z Block, Phase 3, DHA, Lahore, Pakistan
- Founded: 2017
- Company Size: 11–50 employees
- Business Type: Self-Owned

Services & Solutions:
- Website Development: Custom, innovative, dynamic websites focused on conversion and brand representation.
- AI Automations: Custom AI solutions to automate repetitive tasks and boost operational efficiency.
- App Development: Android and iOS apps with user-friendly design and robust backend.
- Web App Development: Responsive and scalable web applications tailored to business needs.
- UI/UX Design: Wireframing, prototyping, and experience design for web and mobile interfaces.
- SEO & Content Marketing: Content creation, optimization, and marketing to grow brand visibility.
- Social Media Marketing: Targeted campaigns to increase engagement and reach.
- Pay-Per-Click Advertising: Ad campaigns driving traffic and leads.
- Game Design & Development: End-to-end mobile and web game production.
- Graphic Design: Brand identity and digital asset creation.
- IT Consulting: Strategic consulting for digital transformation and process optimization.

Approach:
- Client-Centric: Tailored solutions based on unique client objectives and audiences.
- Project Management: Dedicated project managers, continuous communication, and quality assurance.
- Tailored Strategy: In-depth analysis and strategy development for measurable business impact.
- Long-Term Partnerships: Trust, transparency, and tangible value to build lasting relationships.

Portfolio Highlights:
- Projects include marketing sites, e-commerce, enterprise apps, coaching platforms, event portals, health & wellness sites, and productivity tools.
- Experience spans education, tourism, fundraising, and legal industries.

Leadership:
- Daniyal Sultan, CEO & Founder, based in Dubai, UAE. Known for strategic vision and digital innovation leadership.
- Muhammad Adil Waqar, Operational Manager, based in Lahore, Pakistan. Leads technical direction and development operations.

Contact:
- Website: https://webring.ltd/
- Phone: +92 319 6780744
- Email: info@webring.ltd

Always answer concisely, clearly, and in professional English.
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
