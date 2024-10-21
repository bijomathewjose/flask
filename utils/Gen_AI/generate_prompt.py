from . import setup_gen_ai

def generate_prompt(input_text):
    try:
        model = setup_gen_ai()
        response = model.generate_content(input_text)
        return response.text
    except Exception as e:
        raise e