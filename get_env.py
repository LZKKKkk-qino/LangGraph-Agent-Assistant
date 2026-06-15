import os
from dotenv import load_dotenv


load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")

