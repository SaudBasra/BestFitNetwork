# search/ollama_utils.py - Updated for Azure Llama 3.1 8B
import requests
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

def ollama_chat(prompt, model="llama3.1:8b", host="http://my-ollama-llama31.h2ffbjbfh3fveffu.westus2.azurecontainer.io:11434"):
    """
    Send a prompt to Ollama API and get a response - Enhanced for healthcare insights
    
    Args:
        prompt (str): The text prompt to send to Ollama
        model (str): The model to use (default: llama3.1:8b)
        host (str): The Azure Container host address for Ollama API
    
    Returns:
        str: The response from Ollama or an error message
    """
    try:
        endpoint = f"{host}/api/generate"
        logger.info(f"Sending healthcare insight request to Azure Ollama at {endpoint}")
        
        response = requests.post(
            endpoint,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower for more factual healthcare responses
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                    "num_ctx": 4096  # Larger context for analyzing multiple facilities
                }
            },
            timeout=45  # Increased timeout for better responses
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "No response received")
            
            # Log success for healthcare insights
            logger.info(f"Successfully generated healthcare insights using {model}")
            return response_text
        else:
            error_msg = f"Error communicating with Azure Ollama: {response.status_code}"
            logger.error(f"{error_msg} - Response: {response.text}")
            return error_msg
            
    except requests.exceptions.ConnectionError:
        error_msg = "Could not connect to Azure Ollama. Check if container is running and accessible."
        logger.error(error_msg)
        return error_msg
    except requests.exceptions.Timeout:
        error_msg = "Timeout connecting to Azure Ollama. Healthcare analysis may be complex - try again."
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Exception when calling Azure Ollama API: {str(e)}"
        logger.error(error_msg)
        return error_msg

def enhanced_healthcare_chat(prompt, model="llama3.1:8b"):
    """
    Enhanced healthcare-specific chat function with optimized settings
    """
    # Enhanced prompt for healthcare context
    healthcare_prompt = f"""
    You are a professional healthcare facility advisor. Analyze the following information and provide insights that help families make informed decisions about care facilities.

    {prompt}

    Please provide:
    - Specific facility recommendations based on the search criteria
    - Key strengths and considerations for each recommended facility
    - Practical advice for decision-making
    - Professional, empathetic tone suitable for families in healthcare transitions
    """
    
    return ollama_chat(healthcare_prompt, model)

def quick_facility_summary(facility_data, query):
    """
    Generate a quick summary for a single facility or small set
    """
    prompt = f"""
    Provide a concise professional summary for this healthcare facility search: "{query}"
    
    Facility Information:
    {json.dumps(facility_data, indent=2)}
    
    Focus on:
    - Why this facility matches the search criteria
    - Key features that matter for this type of care
    - Brief recommendation (2-3 sentences)
    """
    
    return ollama_chat(prompt, model="llama3.1:8b")

def get_ollama_status():
    """
    Check if Azure Ollama service is accessible
    """
    try:
        response = requests.get(
            "http://my-ollama-llama31.h2ffbjbfh3fveffu.westus2.azurecontainer.io:11434/api/tags",
            timeout=10
        )
        if response.status_code == 200:
            models = response.json().get('models', [])
            llama_models = [m for m in models if 'llama3.1' in m.get('name', '')]
            
            if llama_models:
                return {"status": "ready", "model": "llama3.1:8b", "message": "Azure Ollama ready for healthcare insights"}
            else:
                return {"status": "no_model", "message": "Llama 3.1 8B not found on Azure Ollama"}
        else:
            return {"status": "error", "message": f"Azure Ollama responded with status {response.status_code}"}
    except Exception as e:
        return {"status": "unreachable", "message": f"Cannot reach Azure Ollama: {str(e)}"}