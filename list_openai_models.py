import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("No OpenAI API Key found")
else:
    client = OpenAI(api_key=api_key)
    try:
        print("Available OpenAI Models:")
        models = client.models.list()
        # Sort models by id for better readability
        sorted_models = sorted([m.id for m in models.data])
        for model_id in sorted_models:
            print(f"- {model_id}")
    except Exception as e:
        print(f"Error: {e}")
