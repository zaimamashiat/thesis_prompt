import requests
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retrieve API key from environment variable (for app.py compatibility)
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    logger.error("GROQ_API_KEY environment variable is not set.")
    print("Error: GROQ_API_KEY environment variable is not set.")
    exit(1)

# Define the URL and file to upload
url = "http://localhost:8000/upload"
file_path = "D:\\thesis_prompt\\calculator.py"
logger.info(f"Sending request to {url} with file: {file_path}")

try:
    with open(file_path, "rb") as file:
        files = {"file": file}
        response = requests.post(url, files=files, timeout=30)
    
    response.raise_for_status()
    logger.info(f"Request status code: {response.status_code}")
    logger.info(f"Response headers: {response.headers}")
    logger.info(f"Response text: {response.text}")

    if response.status_code == 200:
        try:
            print("JSON Response:")
            print(response.json())
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")
            print(f"Raw response: {response.text}")
    else:
        logger.error(f"Request failed with status code: {response.status_code}")
        print(f"Response: {response.text}")

except requests.exceptions.RequestException as e:
    logger.error(f"Request failed: {str(e)} - Response: {response.text if 'response' in locals() else 'No response'}")
    print(f"Request failed: {str(e)} - Response: {response.text if 'response' in locals() else 'No response'}")
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    print(f"Unexpected error: {str(e)}")