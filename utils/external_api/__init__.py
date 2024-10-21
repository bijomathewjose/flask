import requests
import json

def handle_external_api_error(e, response=None):
    """
    Handles exceptions from external API calls, including parsing error details from the API response.
    """
    error_message = f"External API Error: {e}"
    if response is not None:
        try:
            # Try to parse and include JSON error details if available
            error_details = response.json()
            error_message += f" Error details: {json.dumps(error_details)}"
        except (ValueError, AttributeError):
            # If response is not JSON or response is None, include raw content if available
            if hasattr(response, 'content'):
                error_message += f" Response content: {response.content.decode('utf-8', errors='replace')}"
    raise Exception(error_message) from e

def make_api_request(method, url, **kwargs):
    """
    Makes an API request and handles errors using the reusable error handling function.
    """
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as e:
        handle_external_api_error(e, response)
    except requests.exceptions.RequestException as e:
        raise Exception(f"External API Error: Network error occurred: {e}") from e
    except Exception as e:
        raise Exception(f"External API Error: An unexpected error occurred: {e}") from e

from .remove_bg import *
from .replace_background import *
