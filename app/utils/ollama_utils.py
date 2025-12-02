"""Ollama integration utilities"""
import requests
from typing import List


def get_ollama_models() -> List[str]:
    """
    Get list of available Ollama models
    
    Returns:
        List of model names or empty list if Ollama is not available
    """
    model_list = []
    try:
        url = "http://localhost:11434/api/tags"
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            for model in data.get("models", []):
                model_list.append(model["model"])
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f"Warning: Could not connect to Ollama at localhost:11434. Error: {e}")
    
    return model_list


def check_ollama_available() -> bool:
    """Check if Ollama is running"""
    try:
        url = "http://localhost:11434/api/tags"
        response = requests.get(url, timeout=1)
        return response.status_code == 200
    except:
        return False
