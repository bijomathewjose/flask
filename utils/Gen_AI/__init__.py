import os
import logging
import google.generativeai as genai

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

model=None
def setup_gen_ai():
    global model
    logger.info("Checking if model is already set up")
    if model is not None:
        logger.info("Model is already set up")
        return model
    else:
        logger.info("Model is not set up, setting up model...")
    GENAI_API_KEY = os.getenv("GENAI_API_KEY")
    if not GENAI_API_KEY:
        logger.error("GENAI_API_KEY is missing. Please set the environment variable.")
        raise ValueError("GENAI_API_KEY is not set.")
    logger.info(f"GENAI_API_KEY retrieved")
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
    return model

from .generate_prompt import *