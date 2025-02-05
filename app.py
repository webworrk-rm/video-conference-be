from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os
import time

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ✅ Daily.co API Configuration
dailyco_api_key = os.getenv("DAILY_CO_API_KEY", "YOUR_DAILY_CO_API_KEY")
dailyco_base_url = "https://api.daily.co/v1/rooms"
token_api_url = "https://api.daily.co/v1/meeting-tokens"

headers = {
    "Authorization": f"Bearer {dailyco_api_key}",
    "Content-Type": "application/json"
}

waiting_list = {}  # Store join requests

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "API is running!"}), 200

# ✅ API to create a meeting with controlled access
@app.route("/api/create-meeting", methods=["POST"])
def create_meeting():
    try:
        print("✅ Received request to create a meeting")

        # Set meeting expiration (1 hour)
        future_timestamp = int(time.time()) + 3600

        # ✅ Create **private** meeting where all participants require approval
        response = requests.post(dailyco_base_url, headers=headers, json={
            "privacy": "private",
            "properties": {
                "enable_knocking": True,  # Participants require host approval
                "exp": future_timestamp,
                "start_audio_off": True,
                "start_video_off": True,
                "enable_chat": True
            }
        })
        data = response.json()
        print("✅ Daily.co Response:", data)

        if "url" in data:
            meeting_url = data["url"]
            room_name = data["name"]

            # ✅ Generate secure meeting tokens for host and participants
            host_token = generate_token(room_name, is_owner=True)
            participant_token = generate_token(room_name, is_owner=False)

            if host_token and participant_token:
                host_url = f"{meeting_url}?t={host_token}"
                participant_url = f"{meeting_url}?t={participant_token}"
                waiting_list[room_name] = []  # Initialize waiting list for the meeting

                print(f"✅ Meeting created: Host URL = {host_url}, Participant URL = {participant_url}")
                return jsonify({
                    "host_url": host_url,
                    "participant_url": participant_url
                }), 201
            else:
                return jsonify({"error": "Failed to generate meeting tokens"}), 500
        else:
            return jsonify({"error": "Failed to create meeting", "details": data}), 500
    except Exception as e:
        print("❌ Create Meeting Error:", str(e))
        return jsonify({"error": str(e)}), 500

# ✅ Function to generate a **secure meeting token**
def generate_token(room_name, is_owner=False):
    try:
        response = requests.post(token_api_url, headers=headers, json={
            "properties": {
                "room_name": room_name,
                "is_owner": is_owner
            }
        })
        token_data = response.json()
        return token_data.get("token")
    except Exception as e:
        print(f"❌ Token Generation Failed: {e}")
        return None

# ✅ API to request to join a meeting (Participant requests approval)
@app.route("/api/request-join", methods=["POST"])
def request_join():
    try:
        data = request.json
        room_name = data.get("room_name")
        user_name = data.get("user_name")

        if room_name not in waiting_list:
            return jsonify({"error": "Room not found"}), 404

        waiting_list[room_name].append({"user_name": user_name})
        print(f"🔔 Join request received: {user_name} for {room_name}")

        return jsonify({"message": "Request sent to host", "room_name": room_name}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ API for host to get the waiting list
@app.route("/api/waiting-list/<room_name>", methods=["GET"])
def get_waiting_list(room_name):
    try:
        if room_name not in waiting_list:
            return jsonify({"error": "Room not found"}), 404

        return jsonify({"waiting_list": waiting_list[room_name]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ API for host to admit a participant
@app.route("/api/admit-participant", methods=["POST"])
def admit_participant():
    try:
        data = request.json
        room_name = data.get("room_name")
        user_name = data.get("user_name")

        if room_name not in waiting_list:
            return jsonify({"error": "Room not found"}), 404

        waiting_list[room_name] = [p for p in waiting_list[room_name] if p["user_name"] != user_name]

        print(f"✅ {user_name} admitted to {room_name}")
        return jsonify({"message": "User admitted", "user_name": user_name}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
