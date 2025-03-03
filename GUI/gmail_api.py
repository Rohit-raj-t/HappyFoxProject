#!/usr/bin/env python3
import os
import pickle
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import config  # Import our project settings

def authenticate_gmail():
    """
    Log in to Gmail using OAuth and get a service object for the API.
    
    This function tries to load saved credentials from a file.
    If they don't exist or are expired, it refreshes or asks you to log in again.
    """
    creds = None
    token_file = "token.pickle"
    
    # If we've got saved credentials, load them
    if os.path.exists(token_file):
        with open(token_file, "rb") as token:
            creds = pickle.load(token)
    
    # If credentials are missing or no longer valid, refresh or sign in again
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Check if the OAuth credentials file exists
            if not os.path.exists(config.OAUTH_CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Missing {config.OAUTH_CREDENTIALS_FILE}. Please provide your OAuth credentials file."
                )
            # Kick off the login process
            flow = InstalledAppFlow.from_client_secrets_file(config.OAUTH_CREDENTIALS_FILE, config.SCOPES)
            creds = flow.run_local_server(port=0)
        # Save these credentials for next time so you don't have to log in again
        with open(token_file, "wb") as token:
            pickle.dump(creds, token)
    
    # Return our Gmail service object that lets us make API calls
    return build("gmail", "v1", credentials=creds)

def list_emails(service, message_count="50"):
    """
    Fetch a bunch of emails from your Gmail.
    
    If you pass a number (as a string) like "50", it'll get that many emails.
    Otherwise, it'll treat the input as a search query (e.g., "newer_than:7d").
    """
    messages = []
    
    if message_count.isdigit():
        desired_count = int(message_count)
        query = ""
        # The API limits us to a max of 100 per request, so we use the smaller number
        max_results = min(desired_count, 100)
    else:
        query = message_count  # This could be something like "newer_than:7d"
        max_results = 100

    response = service.users().messages().list(
        userId="me", maxResults=max_results, q=query
    ).execute()
    messages.extend(response.get("messages", []))
    
    # Keep fetching more pages of results if available
    while "nextPageToken" in response and (not message_count.isdigit() or len(messages) < desired_count):
        page_token = response["nextPageToken"]
        response = service.users().messages().list(
            userId="me", maxResults=max_results, q=query, pageToken=page_token
        ).execute()
        messages.extend(response.get("messages", []))
    
    # If we fetched too many, trim the list
    if message_count.isdigit():
        messages = messages[:desired_count]
    
    return messages

def get_email(service, msg_id):
    """
    Grab the details for one email using its ID.
    
    It pulls out important info like who it's from, who it's to, the subject,
    when it was received, and a little snippet of the email's content.
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
    """
    Try to convert an email's date string into a datetime object.
    
    If parsing fails for any reason, it just returns None.
    """
    try:
        return datetime.strptime(date_str[:31], '%a, %d %b %Y %H:%M:%S %z')
    except Exception:
        return None
