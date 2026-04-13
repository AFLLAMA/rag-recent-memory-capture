import os
import json
import tiktoken
import logging
import hashlib
from datetime import datetime
from db.db import insert_document, insert_embeddings
from core.embedding import generate_embeddings_batch

logger = logging.getLogger(__name__)

def get_chunks(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """
    Split text into chunks of `chunk_size` tokens with `overlap` tokens overlap.
    Preserves semantic meaning by not splitting mid-sentence if possible.
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    sentences = text.replace("\n", " \n").split(". ") # Naive sentence split
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence = sentence.strip() + "."
        if sentence == ".":
            continue
            
        sentence_tokens = len(encoding.encode(sentence))
        
        if current_length + sentence_tokens > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            # Keep overlap
            overlap_length = 0
            overlap_chunk = []
            for s in reversed(current_chunk):
                s_len = len(encoding.encode(s))
                if overlap_length + s_len > overlap:
                    break
                overlap_chunk.insert(0, s)
                overlap_length += s_len
            current_chunk = overlap_chunk
            current_length = overlap_length
            
        current_chunk.append(sentence)
        current_length += sentence_tokens
        
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def process_and_ingest(content: str, source_type: str, created_at: datetime, source_id: str = None, metadata: dict = None, max_chars: int = 50000):
    """Process text content, chunk it, embed it, and save to DB."""
    if not content:
        logger.warning(f"Skipping empty content for source: {source_id or 'unknown'}")
        return False
        
    # Security: Limit maximum document length to prevent API token exhaustion
    # Note: 50,000 characters is roughly 12,500 OpenAI tokens. 
    # At $0.02 per 1M tokens, this caps ingestion at ~$0.00025 per document!
    if len(content) > max_chars:
        logger.warning(f"Content for {source_id} exceeds {max_chars} length. Truncating.")
        content = content[:max_chars]
        
    doc_id = insert_document(content, source_type, created_at, source_id)
    if not doc_id:
        logger.info(f"Duplicate content detected for {source_id}, skipping embeddings.")
        return False
        
    chunks = get_chunks(content)
    if not chunks:
        return True
        
    embeddings = generate_embeddings_batch(chunks)
    
    base_meta = metadata or {}
    base_meta["source_type"] = source_type
    metadatas = [base_meta for _ in chunks]
    
    insert_embeddings(doc_id, chunks, embeddings, metadatas)
    logger.info(f"Ingested target {source_id}: {len(chunks)} chunks.")
    return True

def ingest_file(filepath: str, max_chars: int = 50000):
    """Read a JSON document from disk, chunk it, embed it, and save to DB."""
    with open(filepath, "r") as f:
        data = json.load(f)
        
    content = data.get("content", "")
    source_type = data.get("source_type", "unknown")
    timestamp_str = data.get("timestamp")
        
    try:
        created_at = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()
    except ValueError:
        created_at = datetime.now()
        
    file_hash = hashlib.sha256(content.encode()).hexdigest()
    
    process_and_ingest(
        content=content, 
        source_type=source_type, 
        created_at=created_at, 
        source_id=file_hash, 
        metadata={"source_file": os.path.basename(filepath)},
        max_chars=max_chars
    )

def ingest_directory(directory: str, max_chars: int = 50000):
    """Ingest all JSON files in a directory."""
    if not os.path.exists(directory):
        logger.error(f"Directory {directory} does not exist.")
        return
        
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.json')]
    for file in files:
        ingest_file(file, max_chars=max_chars)
