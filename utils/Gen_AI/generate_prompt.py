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


def generate_svg(prompt:str):
    """
    Generate an SVG vector graphic based on the given prompt.

    Args:
        prompt (str): The prompt to generate an SVG for
        path (str): Optional path to save the generated SVG to

    Returns:
        str: The generated SVG code as a string
    """
    
    model = setup_gen_ai()
    
    # Generate SVG code
    logger.info("Generating SVG vector graphic...")
    full_prompt = f"{prompt} in SVG format.Only provide the svg value as output no metadata or information"
    response = model.generate_content(full_prompt)
    
    # Extract the generated text response
    svg_code = response.text.strip()
    logger.info("SVG vector graphic generated")
    return svg_code