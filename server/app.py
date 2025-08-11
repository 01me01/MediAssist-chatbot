from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return "Chatbot Backend Running"

# Session & Handlers
from session_store import user_sessions
from utils import predict_disease
from booking_handler import handle_booking
from doc_book import handle_doctor_booking

# Intent detection helpers
SYMPTOM_KEYWORDS = [
    "pain", "fever", "headache", "cough", "vomit", "chills",
    "sneezing", "cold", "sore throat", "acidity", "rash", "fatigue",
    "breath", "nausea", "joint", "burning", "itching"
]

def is_booking_intent(message):
    keywords = ["book", "test", "appointment", "schedule", "lab", "checkup", "blood", "scan", "diagnostic"]
    return any(kw in message.lower() for kw in keywords)

def is_doctor_booking(message):
    keywords = ["doctor", "see a doctor", "consult", "dr.", "physician"]
    return any(kw in message.lower() for kw in keywords)

def looks_like_symptom_input(message):
    msg = message.lower()
    has_symptom_words = any(symptom in msg for symptom in SYMPTOM_KEYWORDS)
    return has_symptom_words or "," in msg

@socketio.on('user_message')
def handle_user_message(message):
    user_id = request.sid  # unique per connection
    if not isinstance(message, str):
        try:
            message = str(message)
        except Exception:
            message = ""

    msg = message.strip()
    low = msg.lower()

    print("handle_booking called for", user_id, "existing:", user_id in user_sessions, "| msg:", low)

    # 1) Early greet
    if low in ["start", "hello", ""]:
        response = (
            "👋 Hello! I'm your health assistant.\n"
            "I can help you with:\n"
            "🧪 Lab test booking\n"
            "🩺 Doctor appointment\n"
            "🤒 Symptom checker\n\n"
            "Try saying:\n"
            "- 'Book a blood test in Delhi'\n"
            "- 'See a doctor on call'\n"
            "- 'I have fever and headache'"
        )
        emit('bot_response', response)
        return

    # 2) Continue existing multi-step flow if any
    if user_id in user_sessions:
        session_type = user_sessions[user_id].get("type")
        if session_type == "doctor":
            response = handle_doctor_booking(user_id, msg)
        else:
            response = handle_booking(user_id, msg)
        emit('bot_response', response)
        return

    # 3) Start new flows
    if is_doctor_booking(msg):
        user_sessions[user_id] = {
            "type": "doctor",
            "state": "start",   # align with your doc_book expectations
            "booking": {}
        }
        response = handle_doctor_booking(user_id, msg)
        emit('bot_response', response)
        return

    if is_booking_intent(msg):
        user_sessions[user_id] = {
        "type": "lab",
        "state": "awaiting_city",
        "booking": {}
    }
        response = "📍 Please enter your city (e.g., Delhi, Indore):"
        emit('bot_response', response)
        response = handle_booking(user_id, msg)

        return

    # 4) Symptom checker
    if looks_like_symptom_input(msg):
        try:
            response = predict_disease(msg)
        except Exception as e:
            response = f"⚠️ Sorry, something went wrong: {str(e)}"
        emit('bot_response', response)
        return

    # 5) Default help
    response = (
        "👋 Hello! I can help you with:\n"
        "🧪 Lab test booking\n"
        "🩺 Doctor appointment\n"
        "🤒 Symptom checker\n\n"
        "Try saying:\n"
        "- 'Book a blood test in Delhi'\n"
        "- 'See a doctor on call'\n"
        "- 'I have fever and headache'"
    )
    emit('bot_response', response)


if __name__ == '__main__':
    socketio.run(app, debug=True)
