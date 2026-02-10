import os
import requests
import time
from typing import List, Optional

# Constants for API interaction
UPSTAGE_API_URL = "https://api.upstage.ai/v1/embeddings" # Placeholder, need to verify actual endpoint
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

    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        print("Error: UPSTAGE_API_KEY environment variable not set.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": text,
        "model": "solar-embedding-korean" # Assuming this is the correct model name
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(UPSTAGE_API_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

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
    # Example usage (requires UPSTAGE_API_KEY to be set in environment)
    # You might need to set it like: export UPSTAGE_API_KEY="YOUR_API_KEY"
    # Or in Windows: $env:UPSTAGE_API_KEY="YOUR_API_KEY"
    
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
    original_api_key = os.getenv("UPSTAGE_API_KEY")
    if original_api_key:
        del os.environ["UPSTAGE_API_KEY"]
    
    print("\nTesting without API Key:")
    embedding_no_key = get_embedding(test_text_1)
    if embedding_no_key is None:
        print("Correctly handled missing API key.")

    if original_api_key:
        os.environ["UPSTAGE_API_KEY"] = original_api_key
