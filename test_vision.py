import google.generativeai as genai
from PIL import Image
import io
import json

GEMINI_API_KEY = "AIzaSyBCX120ZK8VZweRdWoSKzaXkgwcEktB3gY"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

# Creating a tiny dummy image to test vision
img = Image.new('RGB', (100, 100), color = (73, 109, 137))
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='PNG')
img_byte_arr = img_byte_arr.getvalue()

extract_prompt = """Extract medicines. Return JSON only."""

try:
    response = model.generate_content([extract_prompt, Image.open(io.BytesIO(img_byte_arr))])
    print(f"Raw Output: {response.text}")
except Exception as e:
    print(f"Error: {e}")
