import csv
from datetime import datetime
import os
exact_loc = {"indore": ["Yashwant Plaza", "5, Ratlam Kothi, AB Road, Geeta Bhavan Square, near Brainmaster Classes, Indore, Madhya Pradesh 452001", "Mezzanine Floor Omega Tower 32, Mechanic Nagar Extension, Sayaji Club Rd, Scheme No 54, Indore, Madhya Pradesh 452010", "57, Shri Nagar Main Rd, Near POOJA MILK CENTRE, Shree Nagar Ext, Shree Nagar, Indore, Madhya Pradesh 452001"
    ],
    "ujjain": ["JYOTIBA PHULE COMPLEX, C-2, Vegetable Market Rd, behind RAJAWADI RESTAURANT, Nanakheda, Mahakal Vanijya, Ujjain, Madhya Pradesh 456010"
    ],
    "delhi": [ "B‑101, Pushpanjali Enclave, Outer Ring Road, Opposite Pillar No‑39, Pitampura, New Delhi, Delhi, India"
    ],
    "mumbai": [ "27 MIDC, Office No. 201 & 202, 2nd Floor, Kondivita, Andheri East, Mumbai, Maharashtra 400093"
    ],
    "kolkata": ["3rd and 4th Floor, Garpati Tower, 55 Bisdhanagar Road, Kolkata, West Bengal 700067"
    ],
    "lucknow": [ "Metro Station, 17/34, near Munsi Puliya, Munshi Pulia, Sector 13, Indiranagar, Lucknow, Uttar Pradesh 226016"
    ]
}
labs_by_city = {"indore": ["Yashwant Plaza", "Geeta Bhavan", "Scheme No 54", "Shree Nagar"],
    "ujjain": ["Nanakheda"],
    "delhi": [ "Pitampura" ],
    "mumbai": [ "Andheri East" ],
    "kolkata": ["55 Bisdhanagar Road7"],
    "lucknow": [ " Indiranagar" ] 
}
time_slots = ["9 AM – 11 AM", "11 AM – 1 PM", "2 PM – 4 PM"]
available_coupons = ["HEALTH50", "FIRSTLAB100"]

from session_store import user_sessions

BOOKING_FILE = "bookings.csv"

if not os.path.exists(BOOKING_FILE):
    with open(BOOKING_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["UserID", "City", "Lab", "Date", "Time", "Location", "Payment", "BookingID"])


def handle_booking(user_id, message):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "state": "awaiting_city",
            "booking": {}
        }
        return "📍 Please enter your city (e.g., Delhi, Indore):"

    session = user_sessions[user_id]
    state = session["state"]
    booking = session["booking"]
    message = message.strip().lower()

    if state == "awaiting_city":
        if message not in labs_by_city:
            return "❌ Sorry, we don't serve this city yet. Please choose from: " + ", ".join(labs_by_city.keys())
        booking["city"] = message
        session["state"] = "awaiting_lab"
        return f"🏥 Available labs in {message.title()}: " + ", ".join(labs_by_city[message])

    elif state == "awaiting_lab":
        if message not in [lab.lower() for lab in labs_by_city[booking["city"]]]:
            return "❌ Please choose a valid lab from the list."
        booking["lab"] = message
        session["state"] = "awaiting_date"
        # Here you can add logic to provide the exact location of the lab
        # for lab in exact_loc[booking["city"]]:
        #     if lab.lower() == booking["lab"]:
        #         loc = lab
        # return f"Exact location of the lab is \n {loc} \n📅 Please enter your preferred date (e.g., 2025-08-01):"
        return f"Please enter your preferred date (e.g., 2025-08-01):"
    elif state == "awaiting_date":
        try:
            datetime.strptime(message, "%Y-%m-%d")  # validate date format
        except:
            return "⚠️ Invalid date format. Use YYYY-MM-DD."
        booking["date"] = message
        session["state"] = "awaiting_time"
        return "⏰ Please enter 1,2,3 as the selected time slot:\n" + "\n".join([f"{i+1}. {slot}" for i, slot in enumerate(time_slots)])

    elif state == "awaiting_time":
    # Show numbered slots if this is the first prompt for time
        numbered_slots = "\n".join([f"{i+1}. {slot}" for i, slot in enumerate(time_slots)])
    
    # If the user typed a number
        if message.isdigit():
            choice = int(message)
            if 1 <= choice <= len(time_slots):
                booking["time"] = time_slots[choice - 1]
                session["state"] = "awaiting_location"
                return "📌 Please type your preferred location (e.g., Home visit address or Lab visit):"
            else:
                return f"❌ Invalid choice. Please type 1, 2, or 3.\nAvailable slots:\n{numbered_slots}"
        
        # If the user typed something else
        return f"⏰ Please choose a time slot by number:\n{numbered_slots}"


    elif state == "awaiting_location":
        booking["location"] = message
        session["state"] = "awaiting_confirmation"
        return (
            f"✅ Please confirm your booking:\n"
            f"City: {booking['city'].title()}\n"
            f"Lab: {booking['lab'].title()}\n"
            f"Date: {booking['date']}\n"
            f"Time: {booking['time']}\n"
            f"Location: {booking['location']}\n"
            f"Type 'confirm' to proceed or 'cancel' to stop."
        )

    elif state == "awaiting_confirmation":
        if message == "confirm":
            session["state"] = "awaiting_payment"
            return (
                "💳 Please choose a payment option:\n"
                "1. UPI\n"
                "2. Credit/Debit Card\n"
                "3. Pay on Visit"
            )
        elif message == "cancel":
            del user_sessions[user_id]
            return "❌ Booking cancelled. Let me know if you’d like to start again!"
        else:
            return "Please type 'confirm' or 'cancel'."

    elif state == "awaiting_payment":
        options = {
            "1": "UPI",
            "2": "Card",
            "3": "Pay on Visit",
            "upi": "UPI",
            "card": "Card",
            "pay on visit": "Pay on Visit"
        }
        if message not in options:
            return "❌ Invalid payment option. Please type: 1, 2, or 3."

        booking["payment"] = options[message]

        booking_id = f"LAB{datetime.now().strftime('%Y%m%d%H%M%S')}"
        booking["booking_id"] = booking_id

        with open(BOOKING_FILE, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                user_id,
                booking["city"],
                booking["lab"],
                booking["date"],
                booking["time"],
                booking["location"],
                booking["payment"],
                booking_id
            ])

        del user_sessions[user_id]

        return (
            f"🎉 Your test is booked!\n"
            f"📄 Booking ID: {booking_id}\n"
            f"💰 Payment Method: {booking['payment']}\n"
            f"Thank you for choosing us! 💙"
        )

    return "⚠️ Something went wrong. Please restart booking by saying 'book test'."
