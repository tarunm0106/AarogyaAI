import requests

BASE_URL = "http://127.0.0.1:5000"

def check_health():
    try:
        # Check history
        r = requests.get(f"{BASE_URL}/api/history")
        print(f"History Status: {r.status_code}")
        
        # Check reminders
        r = requests.get(f"{BASE_URL}/api/reminders")
        print(f"Reminders Status: {r.status_code}")
        
        # Check a voice query (dummy)
        payload = {"question": "Hello", "language": "english"}
        r = requests.post(f"{BASE_URL}/api/voice-query", json=payload)
        print(f"Voice Query Status: {r.status_code}")
        if r.status_code == 200:
            print(f"Voice Answer: {r.json().get('answer')}")
            
    except Exception as e:
        print(f"Health Check Error: {e}")

if __name__ == "__main__":
    check_health()
