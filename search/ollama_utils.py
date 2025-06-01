import requests
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

def ollama_chat(prompt, model="llama3", host="http://localhost:11434/api/generate"):
    """
    Send a prompt to Ollama API and get a response
    
    Args:
        prompt (str): The text prompt to send to Ollama
        model (str): The model to use (default: llama3)
        host (str): The host address for Ollama API
    
    Returns:
        str: The response from Ollama or an error message
    """
    try:
        endpoint = f"{host}/api/generate"
        logger.info(f"Sending request to Ollama at {endpoint}")
        
        response = requests.post(
            endpoint,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "No response received")
        else:
            error_msg = f"Error communicating with Ollama: {response.status_code}"
            logger.error(f"{error_msg} - Response: {response.text}")
            return error_msg
    except requests.exceptions.ConnectionError:
        error_msg = "Could not connect to Ollama. Make sure Ollama is running (try: 'ollama serve')"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Exception when calling Ollama API: {str(e)}"
        logger.error(error_msg)
        return error_msg