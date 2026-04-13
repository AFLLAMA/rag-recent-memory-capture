import sys
import argparse
import logging
from db.db import init_db
from core.ingestion import ingest_directory
from core.search import search, ask_with_context
from connectors.gmail_ingestion import ingest_recent_emails

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    parser = argparse.ArgumentParser(description="AI Personal Data Engineer Assistant CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Initialize the database schema")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest data into the database")
    ingest_parser.add_argument("--source", type=str, choices=["local", "gmail"], default="local", help="Source of data (local or gmail)")
    ingest_parser.add_argument("--dir", type=str, default="data", help="Directory containing JSON files (used when source=local)")
    ingest_parser.add_argument("--max-chars", type=int, default=50000, help="Max characters per document for cost control")
    ingest_parser.add_argument("--max-results", type=int, default=100, help="Max emails to fetch (used when source=gmail)")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Perform vector similarity search on ingested data")
    search_parser.add_argument("query", type=str, help="Search query")
    search_parser.add_argument("--type", type=str, help="Filter by source_type (e.g. email, note, thought)")
    search_parser.add_argument("--days", type=int, help="Filter by last N days")
    search_parser.add_argument("--top-k", type=int, default=3, help="Number of results to return")
    
    # Ask command (RAG)
    ask_parser = subparsers.add_parser("ask", help="Ask a question and get an AI-generated answer using your data")
    ask_parser.add_argument("question", type=str, help="Question to ask")
    ask_parser.add_argument("--type", type=str, help="Filter by source_type (e.g. email, note, thought)")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        print("Initializing database...")
        init_db()
        print("Database initialized.")
        
    elif args.command == "ingest":
        if args.source == "local":
            print(f"Ingesting directory: {args.dir} with max {args.max_chars} chars per doc.")
            ingest_directory(args.dir, max_chars=args.max_chars)
            print("Local data ingestion complete.")
        elif args.source == "gmail":
            print(f"Ingesting from Gmail with max {args.max_chars} chars per email (fetching up to {args.max_results} emails).")
            ingest_recent_emails(max_results=args.max_results, max_chars=args.max_chars)
            print("Gmail ingestion complete.")
        
    elif args.command == "search":
        filters = {}
        if args.type:
            filters["source_type"] = args.type
        if args.days:
            filters["days_ago"] = args.days
            
        print(f"Searching for: '{args.query}'")
        results = search(args.query, filters, top_k=args.top_k)
        
        for i, res in enumerate(results):
            score = round(res['similarity'], 3)
            print(f"\n--- Result {i+1} | Score: {score} | Type: {res['source_type']} | Date: {res['created_at'].date()} ---")
            print(res['chunk_text'])
            
    elif args.command == "ask":
        filters = {}
        if args.type:
            filters["source_type"] = args.type
            
        print(f"Asking: '{args.question}'...")
        answer = ask_with_context(args.question, filters)
        print("\n=== AI Answer ===")
        print(answer)
        print("=================")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
