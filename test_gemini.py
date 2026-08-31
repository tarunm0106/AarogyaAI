import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyDTJ5jZEm3kexoWLH9BZlJfmDqykrGdLd8"

try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
    response = model.generate_content("Say hello")
    print(f"Success: {response.text}")
except Exception as e:
    print(f"Error: {e}")
