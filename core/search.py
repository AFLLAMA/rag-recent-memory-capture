import json
import logging
from db.db import get_connection
from core.embedding import generate_embedding, generate_chat_response

logger = logging.getLogger(__name__)

def search(query: str, filters: dict = None, top_k: int = 5):
    """
    Convert query to embedding, apply SQL filters, 
    perform vector similarity search, and return top chunks.
    """
    query_embedding = generate_embedding(query)
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Base query using pgvector's <=> (cosine distance) operator
        sql = """
            SELECT 
                e.chunk_text, 
                e.metadata,
                d.source_type,
                d.created_at,
                1 - (e.embedding <=> %s::vector) AS similarity
            FROM embeddings e
            JOIN documents d ON e.document_id = d.id
        """
        params = [query_embedding]
        
        # Build filter clauses dynamically
        where_clauses = []
        if filters:
            if "source_type" in filters:
                where_clauses.append("d.source_type = %s")
                params.append(filters["source_type"])
            if "days_ago" in filters:
                where_clauses.append("d.created_at >= CURRENT_DATE - INTERVAL '%s days'")
                params.append(filters["days_ago"])
                
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
            
        # Order by similarity
        sql += " ORDER BY e.embedding <=> %s::vector LIMIT %s"
        params.extend([query_embedding, top_k])
        
        cur.execute(sql, tuple(params))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "chunk_text": row[0],
                "metadata": row[1],
                "source_type": row[2],
                "created_at": row[3],
                "similarity": row[4]
            })
            
        return results
    finally:
        cur.close()
        conn.close()

def ask_with_context(question: str, filters: dict = None) -> str:
    """
    Main RAG function. Retrieves relevant chunks and asks LLM.
    """
    # 1. Retrieve chunks
    relevant_chunks = search(question, filters=filters, top_k=5)
    
    if not relevant_chunks:
        return "I couldn't find any relevant information in your data."
        
    # 2. Build context
    context = ""
    for i, chunk in enumerate(relevant_chunks):
        date_str = chunk["created_at"].strftime("%Y-%m-%d")
        context += f"\n--- Source {i+1} ({chunk['source_type']} from {date_str}) ---\n"
        context += chunk["chunk_text"] + "\n"
        
    # 3. Formulate Prompt
    messages = [
        {"role": "system", "content": "You are a personalized AI Data Engineering assistant. Using the provided context extracted from the user's personal data, answer their question. If the answer is not contained in the context, say you don't know based on the provided data."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ]
    
    # 4. Generate Answer
    answer = generate_chat_response(messages)
    return answer
