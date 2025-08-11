# doc_book.py
import json
import os
from datetime import datetime
from session_store import user_sessions  # router/session flag from app.py

# ---------- Paths (portable) ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCTORS_PATH = os.path.join(BASE_DIR, "doctors.json")
APPOINTMENTS_FILE = os.path.join(BASE_DIR, "doctor_appointments.json")

# ---------- Load doctor data ----------
with open(DOCTORS_PATH, "r", encoding="utf-8") as f:
    doctor_data = json.load(f)["doctors"]

# ---------- In-memory per-connection state for doctor flow ----------
doc_sessions = {}  # { user_id: { step, mode, doctor, locations, location, times, time, ... } }


def _save_appointment(appointment: dict) -> None:
    try:
        with open(APPOINTMENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    data.append(appointment)
    with open(APPOINTMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _clear_all_for(user_id: str) -> None:
    # Clear both the flow state and the router state used by app.py
    doc_sessions.pop(user_id, None)
    user_sessions.pop(user_id, None)


def handle_doctor_booking(user_id: str, message: str) -> str:
    # Get or initialize session
    session = doc_sessions.get(user_id, {"step": 0})
    msg = (message or "").strip()

    # STEP 0: Choose mode
    if session["step"] == 0:
        session["step"] = 1
        doc_sessions[user_id] = session
        return (
            "🩺 Would you prefer:\n"
            "1️⃣ On-call consultation\n"
            "2️⃣ Hospital visit\n"
            "(Type 1 or 2)"
        )

    # STEP 1: Validate mode
    elif session["step"] == 1:
        if msg == "1":
            session["mode"] = "on_call"
        elif msg == "2":
            session["mode"] = "hospital"
        else:
            return "❌ Please type 1 for On-call or 2 for Hospital."

        session["step"] = 2
        doc_sessions[user_id] = session

        # List doctors
        lines = ["👨‍⚕️ Available Doctors:"]
        for d in doctor_data:
            lines.append(f"{d['id']}. {d['name']} ({d['specialty']})")
        lines.append("\nPlease enter the doctor number.")
        return "\n".join(lines)

    # STEP 2: Doctor selection
    elif session["step"] == 2:
        if not msg.isdigit():
            return "❌ Invalid doctor number. Please enter the number shown."

        doc_id = int(msg)
        doctor = next((d for d in doctor_data if d["id"] == doc_id), None)
        if not doctor:
            return "❌ Invalid doctor number. Please try again."

        session["doctor"] = doctor

        # On-call => show on-call times
        if session["mode"] == "on_call":
            times = doctor.get("on_call", [])
            if not times:
                return "⚠️ No on-call slots available. Try Hospital visit."
            session["times"] = times
            session["step"] = 3
            doc_sessions[user_id] = session
            listing = "\n".join(f"{i+1}. {t}" for i, t in enumerate(times))
            return f"☎️ Choose a time slot:\n{listing}"

        # Hospital => choose location first
        locations = list(doctor.get("locations", {}).keys())
        if not locations:
            return "⚠️ No hospital locations available. Try On-call."
        session["locations"] = locations
        session["step"] = 3.5
        doc_sessions[user_id] = session
        listing = "\n".join(f"{i+1}. {loc}" for i, loc in enumerate(locations))
        return f"🏥 Choose location:\n{listing}"

    # STEP 3.5: Location selection (hospital)
    elif session["step"] == 3.5:
        locations = session.get("locations", [])
        if not locations:
            return "⚠️ No locations found. Please start over (type 'book doctor')."

        if not msg.isdigit():
            return "❌ Invalid selection. Please enter the number shown."

        idx = int(msg) - 1
        if not (0 <= idx < len(locations)):
            return "❌ Invalid location selection."

        location = locations[idx]
        session["location"] = location

        times = session["doctor"]["locations"].get(location, [])
        if not times:
            return "⚠️ No time slots at this location. Pick another location."

        session["times"] = times
        session["step"] = 4
        doc_sessions[user_id] = session
        listing = "\n".join(f"{i+1}. {t}" for i, t in enumerate(times))
        return f"🕒 Available slots at {location}:\n{listing}"

    # STEP 3: On-call time selection
    elif session["step"] == 3:
        times = session.get("times", [])
        if not times:
            return "⚠️ No time slots found. Please start over (type 'book doctor')."

        choice = msg
        if choice.isdigit():
            idx = int(choice) - 1
            if not (0 <= idx < len(times)):
                return "❌ Invalid time selection."
            time = times[idx]
        else:
            time = choice
            if time not in times:
                return "❌ Invalid time slot."

        session["time"] = time
        session["step"] = 5
        doc_sessions[user_id] = session
        return f"✅ Confirm booking with {session['doctor']['name']} (on-call) at {time}? (yes/no)"

    # STEP 4: Hospital time selection
    elif session["step"] == 4:
        times = session.get("times", [])
        if not times:
            return "⚠️ No time slots found. Please start over (type 'book doctor')."

        choice = msg
        if choice.isdigit():
            idx = int(choice) - 1
            if not (0 <= idx < len(times)):
                return "❌ Invalid time selection."
            time = times[idx]
        else:
            time = choice
            if time not in times:
                return "❌ Invalid time slot."

        session["time"] = time
        session["step"] = 5
        doc_sessions[user_id] = session
        return (
            f"✅ Confirm booking with {session['doctor']['name']} "
            f"at {session['location']} on {time}? (yes/no)"
        )

    # STEP 5: Confirmation
    elif session["step"] == 5:
        if msg.lower() == "yes":
            appointment = {
                "doctor": session["doctor"]["name"],
                "mode": session.get("mode", "on_call"),
                "location": session.get("location", "On-call"),
                "time": session["time"],
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
            _save_appointment(appointment)
            _clear_all_for(user_id)
            return (
                f"🎉 Appointment confirmed with {appointment['doctor']} "
                f"({appointment['mode']}) at {appointment['location']} on {appointment['time']}!"
            )
        else:
            _clear_all_for(user_id)
            return "❌ Booking cancelled. You can start again anytime."

    # Fallback
    else:
        _clear_all_for(user_id)
        return "⚠️ Something went wrong. Let's start over. Type 'book doctor'."
