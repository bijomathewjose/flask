from app import logger
from . import setup_gen_ai

def generate_prompt(input_text):
    model=setup_gen_ai()
    logger.info("Starting generate_prompt function")
    try:
        logger.info("Setting up Gen AI model")
        
        logger.info(f"Generating content for input: {input_text[:50]}...")  # Log first 50 chars of input
        response = model.generate_content(input_text)
        
        logger.info("Content generated successfully")
        return response.text
    except Exception as e:
        logger.error(f"Error in generate_prompt: {str(e)}", exc_info=True)
        raise e
    finally:
        logger.info("Exiting generate_prompt function")
