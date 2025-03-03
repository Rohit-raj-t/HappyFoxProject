#!/usr/bin/env python3

# Global settings for our project, used across different modules.

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']  # Permissions for Gmail API actions.
DB_CONFIG = {}  # This will be filled in with database settings later by the GUI.
OAUTH_CREDENTIALS_FILE = "credentials.json"  # Where our OAuth credentials are stored.
RULES_FILE = "rules.json"  # File containing the rules for processing emails.
