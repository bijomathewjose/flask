import os
import google.generativeai as genai
# Set up your API key

def setup_gen_ai():
    GENAI_API_KEY = os.getenv("GENAI_API_KEY")
    # Configure the model
    GENERATION_CONFIG = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash",generation_config=GENERATION_CONFIG)
    return model

from .generate_prompt import *