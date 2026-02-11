import os
import requests
import time
from typing import List, Optional

# Ensure backend directory is in path for imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.config import get_settings # Import get_settings from backend.config

# Constants for API interaction
UPSTAGE_API_URL = "https://api.upstage.ai/v1/embeddings"
# UPSTAGE_API_URL = "https://api.upstage.ai/v1"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def get_embedding(text: str) -> Optional[List[float]]:
    
  
    
    
    """
    Retrieves the embedding for a given text using the Upstage Solar embedding API.

    Args:
        text (str): The input text to embed.

    Returns:
        Optional[List[float]]: A list of floats representing the embedding, or None if
                               the embedding could not be retrieved.
    """
    if not text or not text.strip():
        print("Warning: Attempted to get embedding for empty or whitespace-only text. Returning None.")
        return None

    # Get settings which loads from .env
    settings = get_settings()
    api_key = settings.upstage_api_key

    if not api_key:
        print("Error: UPSTAGE_API_KEY not found in settings. Please ensure it's set in your .env file.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": text,
        "model": "embedding-query" # Corrected to user-requested model name
    }
    
   

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(UPSTAGE_API_URL, headers=headers, json=payload, timeout=10)
            
            # response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            # Assuming the structure is data["data"][0]["embedding"]
            if data and "data" in data and len(data["data"]) > 0 and "embedding" in data["data"][0]:
                return data["data"][0]["embedding"]
            else:
                print(f"Error: Unexpected API response format: {data}")
                return None

        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred (Attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if response.status_code == 401: # Unauthorized
                print("Error: Invalid or expired UPSTAGE_API_KEY.")
                return None
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error occurred (Attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)
        except requests.exceptions.Timeout:
            print(f"Request timed out (Attempt {attempt + 1}/{MAX_RETRIES}).")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)
        except requests.exceptions.RequestException as e:
            print(f"An unexpected request error occurred (Attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            return None # Don't retry for unexpected request errors
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    print(f"Failed to get embedding after {MAX_RETRIES} attempts.")
    return None


if __name__ == '__main__':
    # Test a valid text
    test_text_1 = "안녕하세요, 무역 코칭 플랫폼입니다."
    embedding_1 = get_embedding(test_text_1)
    if embedding_1:
        print(f"Embedding for '{test_text_1[:20]}...' (first 20 chars): Length {len(embedding_1)}, First 5 values: {embedding_1[:5]}...")
    else:
        print(f"Failed to get embedding for '{test_text_1[:20]}...'.")

    # Test an empty text
    test_text_empty = ""
    embedding_empty = get_embedding(test_text_empty)
    if embedding_empty is None:
        print(f"Correctly handled empty text: Returned None.")
    
    # Test a whitespace text
    test_text_whitespace = "   "
    embedding_whitespace = get_embedding(test_text_whitespace)
    if embedding_whitespace is None:
        print(f"Correctly handled whitespace text: Returned None.")

    # Test for API Key missing (should print an error)
    # This test now relies on the .env file being correctly configured in the project root.
    settings_check = get_settings()
    if settings_check.upstage_api_key:
        print("\nAPI Key found via backend.config.get_settings().")
    else:
        print("\nNo API Key found via backend.config.get_settings(). Please ensure UPSTAGE_API_KEY is set in your .env file in the project root.")