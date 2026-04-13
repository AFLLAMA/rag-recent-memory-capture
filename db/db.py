import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

def get_connection(setup=False):
    """Establish a connection to the PostgreSQL database."""
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise ValueError("DB_PASSWORD environment variable must be explicitly defined in .env")
        
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER", "de_user"),
        password=password,
        dbname=os.getenv("DB_NAME", "de_assist")
    )
    # Register the pgvector type on the connection if not in setup mode
    if not setup:
        register_vector(conn)
    return conn

def init_db():
    """Initialize the database schema."""
    conn = get_connection(setup=True)
    cur = conn.cursor()
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    
    try:
        cur.execute(schema_sql)
        conn.commit()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize schema: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def insert_document(content: str, source_type: str, created_at, source_id: str = None) -> int:
    """Insert a new document and return its ID, or None if it's a duplicate."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO documents (content, source_type, created_at, source_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (source_id) DO NOTHING
            RETURNING id;
            """,
            (content, source_type, created_at, source_id)
        )
        result = cur.fetchone()
        doc_id = result[0] if result else None
        conn.commit()
        return doc_id
    finally:
        cur.close()
        conn.close()

def insert_embeddings(document_id: int, chunks: list, embeddings: list, metadatas: list):
    """Insert vector chunks into embeddings table."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        for chunk, embedding, metadata in zip(chunks, embeddings, metadatas):
            import json
            cur.execute(
                """
                INSERT INTO embeddings (document_id, chunk_text, embedding, metadata)
                VALUES (%s, %s, %s, %s);
                """,
                (document_id, chunk, embedding, json.dumps(metadata))
            )
        conn.commit()
    finally:
        cur.close()
        conn.close()
