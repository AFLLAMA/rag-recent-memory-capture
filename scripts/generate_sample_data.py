import os
import json
import random
from datetime import datetime, timedelta

def generate_sample_data(num_records=35):
    """Generate sample data representing personal emails, technical notes, and career thoughts."""
    # Create data directory in the project root
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    source_types = ["email", "note", "thought"]
    
    templates = [
        # Technical Notes
        ("note", "some text"),
        # Career thoughts
        ("thought", "some text"),
        # Emails
        ("email", "some email text"),
    ]
    
    # Generate combinations + random ones to hit num_records
    for i in range(num_records):
        doc_type, content_template = random.choice(templates)
        
        # Vary the content slightly for the extras
        random_suffix = " " + f"(Ref: ID-{random.randint(1000, 9999)})"
        content = content_template + random_suffix
        
        # Random date within the last 60 days
        days_ago = random.randint(0, 60)
        timestamp = (datetime.now() - timedelta(days=days_ago)).isoformat()
        
        record = {
            "source_type": doc_type,
            "content": content,
            "timestamp": timestamp
        }
        
        file_path = os.path.join(data_dir, f"doc_{i+1:03d}.json")
        with open(file_path, "w") as f:
            json.dump(record, f, indent=2)
            
    print(f"Generated {num_records} sample documents in {data_dir}/")

if __name__ == "__main__":
    generate_sample_data()
