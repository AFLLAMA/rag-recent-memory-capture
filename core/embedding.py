import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"

def generate_embedding(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    text = text.replace("\n", " ") # recommended to remove newlines for better embeddings
    response = client.embeddings.create(
        input=[text],
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of text strings."""
    if not texts:
        return []
        
    cleaned_texts = [text.replace("\n", " ") for text in texts]
    response = client.embeddings.create(
        input=cleaned_texts,
        model=EMBEDDING_MODEL
    )
    return [data.embedding for data in response.data]

def generate_chat_response(messages: list[dict], model: str = "gpt-4o-mini", temperature: float = 0.0) -> str:
    """Generate a chat response using OpenAI Models."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    return response.choices[0].message.content
