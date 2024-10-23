import os
import logging
import google.generativeai as genai

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Starting setup_gen_ai()...")
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
logger.info(f"GENAI_API_KEY retrieved: {'Yes' if GENAI_API_KEY else 'No'}")

# Configure the model
GENERATION_CONFIG = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}
logger.info("Generation config set")

genai.configure(api_key=GENAI_API_KEY)
logger.info("genai configured with API key")

model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=GENERATION_CONFIG)
logger.info("GenerativeModel instance created")

logger.info("setup_gen_ai() completed")


from .generate_prompt import *