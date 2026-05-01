# import google.generativeai as genai
# import os

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# for model in genai.list_models():
#     print(model.name, model.supported_generation_methods)

from google import genai
from dotenv import load_dotenv
import os

load_dotenv(override=True)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(GEMINI_API_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)


# models = client.models.list()

# for m in models:
#     print(m.name)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Say hello"
)

print(response.text)