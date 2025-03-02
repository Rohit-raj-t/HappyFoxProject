#!/usr/bin/env python3
# Global configuration shared among modules.

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
DB_CONFIG = {}  # This dict will be populated by the GUI.
OAUTH_CREDENTIALS_FILE = "credentials.json"  # Default OAuth credentials file path.
RULES_FILE = "rules.json"  # Default rules file path.