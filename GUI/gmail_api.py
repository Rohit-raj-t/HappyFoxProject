#!/usr/bin/env python3
import os
import pickle
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import config  # Import the whole config module

def authenticate_gmail():
    """Authenticate with Gmail via OAuth and return the service object."""
    creds = None
    token_file = "token.pickle"
    if os.path.exists(token_file):
        with open(token_file, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(config.OAUTH_CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Missing {config.OAUTH_CREDENTIALS_FILE}. Please provide your OAuth credentials file."
                )
            flow = InstalledAppFlow.from_client_secrets_file(config.OAUTH_CREDENTIALS_FILE, config.SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "wb") as token:
            pickle.dump(creds, token)
    return build("gmail", "v1", credentials=creds)

def list_emails(service, message_count="50"):
    """
    Fetches emails from Gmail based on the message_count parameter.
    
    If message_count is a digit (e.g. "50"), it is treated as the total number
    of emails to fetch. Otherwise, it is treated as a query string (e.g., "newer_than:7d").
    """
    messages = []
    if message_count.isdigit():
        desired_count = int(message_count)
        query = ""
        # Use desired_count or 100, whichever is smaller, for max_results per page.
        max_results = min(desired_count, 100)
    else:
        query = message_count  # e.g., "newer_than:7d"
        max_results = 100

    response = service.users().messages().list(
        userId="me", maxResults=max_results, q=query
    ).execute()
    messages.extend(response.get("messages", []))
    
    while "nextPageToken" in response and (not message_count.isdigit() or len(messages) < desired_count):
        page_token = response["nextPageToken"]
        response = service.users().messages().list(
            userId="me", maxResults=max_results, q=query, pageToken=page_token
        ).execute()
        messages.extend(response.get("messages", []))
    
    if message_count.isdigit():
        messages = messages[:desired_count]
    
    return messages

def get_email(service, msg_id):
    """
    Retrieve details of an email message.
    Extracts key fields: From, To, Subject, Received Date, and a snippet as the Message.
    """
    message = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
    email_data = {
        "email_id": msg_id,
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "received_date": parse_date(headers.get("date", "")),
        "message": message.get("snippet", "")
    }
    return email_data

def parse_date(date_str):
    """Attempt to parse an email header date string into a datetime object."""
    try:
        return datetime.strptime(date_str[:31], '%a, %d %b %Y %H:%M:%S %z')
    except Exception:
        return None
