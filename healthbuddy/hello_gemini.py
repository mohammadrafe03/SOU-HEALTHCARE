import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import errors

def main():
    # 1. Load the .env file
    load_dotenv()

    # 2. Read GEMINI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "paste-your-key-here":
        print("ERROR: GEMINI_API_KEY is not set or is still placeholder in .env file.")
        print("Please check your .env file and configure a valid Gemini API key.")
        sys.exit(1)

    print("Initializing Gemini client...")
    client = genai.Client(api_key=api_key)

    # Preferred model from competition guidelines: gemini-3.5-flash-lite
    # We test gemini-3.5-flash-lite first, with fallback to gemini-2.5-flash / gemini-2.0-flash if needed
    candidate_models = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash"]
    
    prompt = "Give three simple tips for maintaining a healthy lifestyle."
    print(f"Testing Health Awareness Prompt: '{prompt}'\n")

    success = False
    for model_name in candidate_models:
        try:
            print(f"Attempting with model: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            print("\n--- SOU HEALTHCARE / Gemini Response ---")
            print(response.text)
            print("----------------------------------------")
            print(f"SUCCESS: Successfully generated health tips with model '{model_name}'.")
            success = True
            break
        except errors.APIError as api_err:
            print(f"API Error with {model_name}: {api_err}")
        except Exception as e:
            print(f"Unexpected error with {model_name}: {e}")

    if not success:
        print("\nFailed to generate content with tested models. Please verify your GEMINI_API_KEY.")
        sys.exit(1)

if __name__ == "__main__":
    main()
