import os
from dotenv import load_dotenv
from groq import Groq

# Load the API key from .env file
load_dotenv()

# Create the client
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# Test with a simple question
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[
        {"role": "user", "content": "What is a primary key in a database? Answer in 2 sentences."}
    ]
)

# Print the response
print(response.choices[0].message.content)