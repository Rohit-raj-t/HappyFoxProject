#!/usr/bin/env python3

"""
rules_engine.py

This module handles rule-based processing of emails:
- It loads rules from a JSON file.
- Evaluates each email against the rules.
- Executes actions on emails that match the rules using the Gmail API.
- It also provides a function to fetch and store emails from Gmail based on a given message count
  or query (e.g., "newer_than:7d").
"""

import os
import json
from datetime import datetime
from gmail_api import authenticate_gmail
from mysql_db import fetch_emails_mysql
from config import RULES_FILE

# Mapping from user-friendly label names to Gmail API label IDs.
LABEL_MAPPING = {
    "inbox": "INBOX",
    "forum": "CATEGORY_FORUMS",
    "updates": "CATEGORY_UPDATES",
    "promotions": "CATEGORY_PROMOTIONS"
}

def load_rules():
    """
    Loads the processing rules from the JSON file.
    
    Returns:
        dict: The ruleset if the file exists and is valid; otherwise, None.
    """
    if not os.path.exists(RULES_FILE):
        print("Rules file not found. Please create a rules file using the Rule Editor.")
        return None
    with open(RULES_FILE, "r") as f:
        try:
            rules = json.load(f)
            return rules
        except json.JSONDecodeError:
            print("Error decoding rules file. Please check its contents.")
            return None

def match_condition(email_value, condition):
    """
    Evaluates a single condition on the email value.
    
    For string fields, supports:
      - contains, does not contain, equals, does not equal.
    For datetime fields (e.g., Received Date/Time), supports:
      - less than, greater than (interpreting the value as an integer, optionally in months).
    
    Args:
        email_value: The value from the email (string or datetime).
        condition (dict): A condition with keys 'predicate', 'value', and optionally 'unit'.
        
    Returns:
        bool: True if the condition is met, False otherwise.
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
            num *= 30  # approximate conversion to days
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
    Evaluates an email against a given ruleset.
    
    Uses alias mapping:
      - For fields like "Received Date/Time", it uses the email's received_date.
      - For the "Message" field, it uses the email's message.
    
    The overall match policy ("All" or "Any") is used to determine if the email meets the rules.
    
    Args:
        email (dict): The email data.
        ruleset (dict): The ruleset loaded from the rules file.
    
    Returns:
        bool: True if the email meets the overall rules, False otherwise.
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
    Processes a list of actions on an email using the Gmail API.
    
    Supported actions (as dictionaries):
      - {"action": "mark as read"}
      - {"action": "mark as unread"}
      - {"action": "move message", "destination": "updates"}
    
    Args:
        service: The authenticated Gmail service.
        email_id (str): The ID of the email to process.
        actions (list): A list of action dictionaries.
    
    Returns:
        str: A newline-separated string of action results.
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
                # Get the user-selected destination and map it to a valid Gmail label
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
    Loads the rules, fetches stored emails from MySQL, and for each email that matches
    the rules, executes the specified actions via the Gmail API.
    
    Returns:
        str: A newline-separated string with processing results.
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
            output.append(f"Email {email['email_id']} matches rules. Executing actions...")
            actions_output = process_actions(service, email["email_id"], ruleset["actions"])
            output.append(actions_output)
    return "\n".join(output)

def fetch_and_store_emails(message_count="10"):
    """
    Authenticates with Gmail, fetches a list of emails based on the message_count
    parameter (which can be a digit or a query like 'newer_than:7d'), retrieves details for each,
    and stores them in MySQL.
    
    Args:
        message_count (str): A string representing either the total number of messages to fetch
                             or a Gmail query (e.g., "newer_than:7d").
                             
    Returns:
        str: A newline-separated string with the results of the fetch/store operations.
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