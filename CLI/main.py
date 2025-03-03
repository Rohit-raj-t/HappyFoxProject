#!/usr/bin/env python3
import os
import sys
import pickle
import json
from datetime import datetime, timedelta

# MySQL
import mysql.connector
from mysql.connector import Error

# Google API libraries
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ----------------- Global Configuration -----------------
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
OAUTH_CREDENTIALS_FILE = "credentials.json"  # Default value; can be changed interactively
TOKEN_FILE = "token.pickle"
RULES_FILE = "rules.json"  # File that stores your rules
DB_CONFIG = {}  # Will be set during setup

# ----------------- Gmail API Functions -----------------
def authenticate_gmail():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(OAUTH_CREDENTIALS_FILE):
                sys.exit(f"Missing OAuth credentials file: {OAUTH_CREDENTIALS_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)
    return build("gmail", "v1", credentials=creds)

def list_emails(service, message_count="50"):
    messages = []
    if message_count.isdigit():
        desired_count = int(message_count)
        query = ""
        max_results = min(desired_count, 100)
    else:
        query = message_count
        max_results = 100
    response = service.users().messages().list(userId="me", maxResults=max_results, q=query).execute()
    messages.extend(response.get("messages", []))
    while "nextPageToken" in response and (not message_count.isdigit() or len(messages) < desired_count):
        page_token = response["nextPageToken"]
        response = service.users().messages().list(userId="me", maxResults=max_results, q=query, pageToken=page_token).execute()
        messages.extend(response.get("messages", []))
    if message_count.isdigit():
        messages = messages[:desired_count]
    return messages

def get_email(service, msg_id):
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
    try:
        return datetime.strptime(date_str[:31], '%a, %d %b %Y %H:%M:%S %z')
    except Exception:
        return None

# ----------------- MySQL Functions -----------------
def create_database_if_not_exists(config):
    try:
        connection = mysql.connector.connect(
            host=config["host"],
            user=config["user"],
            password=config["password"]
        )
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config['database']}")
        connection.commit()
        return f"Database '{config['database']}' is ready."
    except Error as e:
        return f"Error creating database: {e}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def create_mysql_table():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        create_table_query = """
            CREATE TABLE IF NOT EXISTS emails (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email_id VARCHAR(255) UNIQUE,
                from_address VARCHAR(255),
                to_address VARCHAR(255),
                subject VARCHAR(255),
                received_date DATETIME,
                snippet TEXT
            );
        """
        cursor.execute(create_table_query)
        connection.commit()
        return "MySQL table 'emails' is ready."
    except Error as e:
        return f"Error creating MySQL table: {e}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def insert_email_mysql(email_data):
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        insert_query = """
            INSERT INTO emails (email_id, from_address, to_address, subject, received_date, snippet)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                from_address = VALUES(from_address),
                to_address = VALUES(to_address),
                subject = VALUES(subject),
                received_date = VALUES(received_date),
                snippet = VALUES(snippet);
        """
        cursor.execute(insert_query, (
            email_data["email_id"],
            email_data.get("from", ""),
            email_data.get("to", ""),
            email_data.get("subject", ""),
            email_data.get("received_date", None),
            email_data.get("message", "")
        ))
        connection.commit()
        return f"Stored email {email_data['email_id']}"
    except Error as e:
        return f"Error inserting email: {e}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def fetch_emails_mysql():
    emails = []
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        cursor.execute("SELECT email_id, from_address, subject, received_date, snippet FROM emails;")
        rows = cursor.fetchall()
        for row in rows:
            emails.append({
                "email_id": row[0],
                "from": row[1],
                "subject": row[2],
                "received_date": row[3],
                "message": row[4]
            })
        return emails
    except Error as e:
        return f"Error fetching emails: {e}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# ----------------- Rules Engine Functions -----------------
def load_rules():
    if not os.path.exists(RULES_FILE):
        print("Rules file not found. Please create a rules file (e.g., rules.json).")
        return None
    with open(RULES_FILE, "r") as f:
        try:
            rules = json.load(f)
            return rules
        except json.JSONDecodeError:
            print("Error decoding rules file. Please check its contents.")
            return None

def match_condition(email_value, condition):
    predicate = condition["predicate"].lower()
    value = condition["value"]
    if isinstance(email_value, datetime) and predicate in ["less than", "greater than"]:
        try:
            num = int(value)
        except ValueError:
            return False
        unit = condition.get("unit", "days").lower()
        if unit == "months":
            num *= 30
        diff = (datetime.now(email_value.tzinfo) - email_value).days
        if predicate == "less than":
            return diff < num
        elif predicate == "greater than":
            return diff > num
    elif isinstance(email_value, str):
        if predicate == "contains":
            return value.lower() in email_value.lower()
        elif predicate == "does not contain":
            return value.lower() not in email_value.lower()
        elif predicate == "equals":
            return email_value.lower() == value.lower()
        elif predicate == "does not equal":
            return email_value.lower() != value.lower()
    return False

def evaluate_email(email, ruleset):
    results = []
    for condition in ruleset.get("rules", []):
        field = condition.get("field", "").lower()
        if field in ["from", "to", "subject"]:
            email_value = email.get(field, "")
        elif "received" in field:
            email_value = email.get("received_date", None)
        elif field == "message":
            email_value = email.get("message", "")
        else:
            email_value = email.get(field, "")
        results.append(match_condition(email_value, condition))
    policy = ruleset.get("match_policy", "All").lower()
    return all(results) if policy == "all" else any(results)

def process_actions(service, email_id, actions):
    output = []
    LABEL_MAPPING = {
        "inbox": "INBOX",
        "forum": "CATEGORY_FORUMS",
        "updates": "CATEGORY_UPDATES",
        "promotions": "CATEGORY_PROMOTIONS"
    }
    for action_dict in actions:
        action_type = action_dict.get("action", "").lower()
        try:
            if action_type == "mark as read":
                service.users().messages().modify(
                    userId="me", id=email_id,
                    body={"removeLabelIds": ["UNREAD"]}
                ).execute()
                output.append(f"Email {email_id} marked as read.")
            elif action_type == "mark as unread":
                service.users().messages().modify(
                    userId="me", id=email_id,
                    body={"addLabelIds": ["UNREAD"]}
                ).execute()
                output.append(f"Email {email_id} marked as unread.")
            elif action_type == "move message":
                user_destination = action_dict.get("destination", "inbox").lower()
                destination_label = LABEL_MAPPING.get(user_destination, user_destination.upper())
                service.users().messages().modify(
                    userId="me", id=email_id,
                    body={
                        "removeLabelIds": ["INBOX"],
                        "addLabelIds": [destination_label]
                    }
                ).execute()
                output.append(f"Email {email_id} moved to {destination_label}.")
        except Exception as e:
            output.append(f"Error processing action '{action_type}' on email {email_id}: {e}")
    return "\n".join(output)

def process_email_rules():
    ruleset = load_rules()
    if not ruleset:
        return "Missing or invalid rules.json file."
    emails = fetch_emails_mysql()
    if not emails or not isinstance(emails, list):
        return "No emails to process."
    service = authenticate_gmail()
    output = []
    for email in emails:
        if evaluate_email(email, ruleset):
            output.append(f"Email {email['email_id']} matches rules. Executing actions...")
            actions_output = process_actions(service, email["email_id"], ruleset["actions"])
            output.append(actions_output)
    return "\n".join(output)

def fetch_and_store_emails(message_count="10"):
    service = authenticate_gmail()
    messages = list_emails(service, message_count)
    if not messages:
        return "No messages found."
    output = []
    for msg in messages:
        try:
            email_data = get_email(service, msg["id"])
            result = insert_email_mysql(email_data)
            output.append(result)
        except Exception as e:
            output.append(f"Error processing message {msg['id']}: {e}")
    return "\n".join(output)

# ----------------- Interactive CLI Loop -----------------
def interactive_loop():
    print("Welcome to the Gmail CLI Application (MySQL & Rules Engine)")
    while True:
        print("\nSelect an option:")
        print("1. Setup configuration and database")
        print("2. Fetch emails from Gmail and store them in MySQL")
        print("3. Process stored emails using rules")
        print("4. Exit")
        choice = input("Enter choice (1-4): ").strip()

        if choice == "1":
            # Setup configuration
            host = input("Enter MySQL host [default: localhost]: ").strip() or "localhost"
            user = input("Enter MySQL username: ").strip()
            password = input("Enter MySQL password: ").strip()
            database = input("Enter MySQL database name: ").strip()
            oauth_file = input("Enter path to OAuth credentials file [default: credentials.json]: ").strip() or "credentials.json"
            global DB_CONFIG, OAUTH_CREDENTIALS_FILE
            DB_CONFIG = {
                "host": host,
                "user": user,
                "password": password,
                "database": database
            }
            OAUTH_CREDENTIALS_FILE = oauth_file
            print(create_database_if_not_exists(DB_CONFIG))
            print(create_mysql_table())

        elif choice == "2":
            # Fetch emails
            method = input("Fetch by (1) Count or (2) Query? Enter 1 or 2: ").strip()
            if method == "1":
                count = input("Enter number of messages to fetch [default: 10]: ").strip() or "10"
                result = fetch_and_store_emails(count)
            elif method == "2":
                query = input("Enter Gmail query (e.g., newer_than:7d): ").strip()
                result = fetch_and_store_emails(query)
            else:
                result = "Invalid option for fetching emails."
            print(result)

        elif choice == "3":
            # Process emails based on rules
            result = process_email_rules()
            print(result)

        elif choice == "4":
            print("Exiting application.")
            break

        else:
            print("Invalid choice. Please enter a number between 1 and 4.")

if __name__ == "__main__":
    try:
        interactive_loop()
    except KeyboardInterrupt:
        print("\nExiting application.")
