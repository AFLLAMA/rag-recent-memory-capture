import os
import logging
from datetime import datetime
from bs4 import BeautifulSoup

import argparse
from core.ingestion import process_and_ingest

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64

# If modifying these scopes, delete the file config/token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

logger = logging.getLogger(__name__)

def get_gmail_service():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file config/token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('config/token.json'):
        creds = Credentials.from_authorized_user_file('config/token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('config/credentials.json'):
                logger.error("Missing config/credentials.json. Please download it from Google Cloud Console.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('config/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('config/token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def clean_html(html_content: str) -> str:
    """Removes HTML tags and noise from email bodies."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    # Kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()    # rip it out
    text = soup.get_text()
    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

def parse_message_parts(parts):
    """
    Utility function that parses the content of an email partition
    """
    text = ""
    for part in parts:
        mimeType = part.get("mimeType")
        body = part.get("body")
        data = body.get("data")
        if data:
            decoded_data = base64.urlsafe_b64decode(data).decode("utf-8")
            if mimeType == "text/plain":
                text += decoded_data
            elif mimeType == "text/html":
                text += clean_html(decoded_data)
        elif part.get("parts"):
            text += parse_message_parts(part.get("parts"))
    return text

def ingest_recent_emails(max_results=100, max_chars=50000):
    service = get_gmail_service()
    if not service:
        return

    logger.info("Fetching recent emails...")
    try:
        results = service.users().messages().list(userId='me', maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            logger.info("No messages found.")
            return

        for msg in messages:
            msg_id = msg['id']
            # Fetch full message
            message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = ""
            sender = ""
            date_str = ""
            
            for header in headers:
                name = header.get('name', '').lower()
                if name == 'subject':
                    subject = header.get('value', '')
                elif name == 'from':
                    sender = header.get('value', '')
                elif name == 'date':
                    date_str = header.get('value', '')
            
            # Parse Date
            try:
                from email.utils import parsedate_to_datetime
                created_at = parsedate_to_datetime(date_str) if date_str else datetime.now()
            except Exception:
                created_at = datetime.now()
                
            # Extract Text
            content = ""
            if 'parts' in payload:
                content = parse_message_parts(payload.get('parts'))
            elif 'body' in payload and 'data' in payload['body']:
                data = payload['body']['data']
                decoded_data = base64.urlsafe_b64decode(data).decode('utf-8')
                if payload.get("mimeType") == "text/html":
                    content = clean_html(decoded_data)
                else:
                    content = decoded_data
            
            if content.strip():
                import re
                # Formulate final document
                full_content = f"From: {sender}\nSubject: {subject}\n\n{content.strip()}"
                
                # Clean up white spaces and \r
                full_content = full_content.replace('\r', '')
                full_content = re.sub(r'[ \t]+', ' ', full_content) # Squash multiple spaces to single
                full_content = re.sub(r'\n\s*\n', '\n', full_content) # Squash multiple newlines to single
                full_content = full_content.strip()
                
                # Ingest!
                process_and_ingest(
                    content=full_content,
                    source_type="email",
                    created_at=created_at,
                    source_id=f"gmail_{msg_id}",
                    metadata={"subject": subject, "sender": sender},
                    max_chars=max_chars
                )
                
    except Exception as error:
        logger.error(f"An error occurred: {error}")

if __name__ == '__main__':
    pass
