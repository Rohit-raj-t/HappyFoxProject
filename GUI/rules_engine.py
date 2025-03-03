#!/usr/bin/env python3

"""
rules_engine.py

This module handles rule-based email processing. It:
- Loads rules from a JSON file.
- Checks each email against those rules.
- Runs actions on emails that match (like marking as read or moving them)
  using the Gmail API.
- Also has a function to grab emails from Gmail (by count or query) and store them.
"""

import os
import json
from datetime import datetime
from gmail_api import authenticate_gmail
from mysql_db import fetch_emails_mysql
from config import RULES_FILE

# Mapping from simple names to Gmail API label IDs.
LABEL_MAPPING = {
    "inbox": "INBOX",
    "forum": "CATEGORY_FORUMS",
    "updates": "CATEGORY_UPDATES",
    "promotions": "CATEGORY_PROMOTIONS"
}

def load_rules():
    """
    Load the rules from our JSON file.

    If the file isn't there or is messed up, it prints an error and returns None.
    """
    if not os.path.exists(RULES_FILE):
        print("Rules file not found. Please create one using the Rule Editor.")
        return None
    with open(RULES_FILE, "r") as f:
        try:
            rules = json.load(f)
            return rules
        except json.JSONDecodeError:
            print("Error decoding the rules file. Check its contents.")
            return None

def match_condition(email_value, condition):
    """
    Check if a single condition passes for an email field.

    For text fields, it handles:
      - contains, does not contain, equals, and does not equal.
    For dates (like the received date), it handles:
      - less than or greater than, treating the value as a number (days or months).

    Returns True if the condition is met, else False.
    """
    predicate = condition["predicate"].lower()
    value = condition["value"]
    
    if isinstance(email_value, datetime) and predicate in ["less than", "greater than"]:
        try:
            num = int(value)
        except ValueError:
            return False
        unit = condition.get("unit", "days").lower()
        if unit == "months":
            num *= 30  # rough conversion to days
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
    """
    Check an email against a set of rules.

    It maps fields like "Received Date/Time" to the email's received_date
    and "Message" to the email's message. Depending on the overall match policy
    ("All" or "Any"), it returns True if the email passes the rules.
    """
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
    """
    Run a list of actions on an email using the Gmail API.

    Supported actions include:
      - Marking as read/unread.
      - Moving the email (with a specified destination).
      
    Returns a string that summarizes what actions were taken.
    """
    output = []
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
                # Map the user-given destination to a Gmail label.
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
    """
    Load the rules, grab emails from the database, and for each email that matches
    the rules, run the specified actions via the Gmail API.

    Returns a string with a summary of what happened.
    """
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
            output.append(f"Email {email['email_id']} matches rules. Running actions...")
            actions_output = process_actions(service, email["email_id"], ruleset["actions"])
            output.append(actions_output)
    return "\n".join(output)

def fetch_and_store_emails(message_count="10"):
    """
    Log in to Gmail, grab emails (either a set number or using a query like 'newer_than:7d'),
    get details for each email, and save them into our MySQL database.

    Returns a summary string of what happened during the process.
    """
    from gmail_api import list_emails, get_email
    from mysql_db import insert_email_mysql
    
    try:
        service = authenticate_gmail()
    except Exception as e:
        return f"Error authenticating with Gmail: {e}"
    
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