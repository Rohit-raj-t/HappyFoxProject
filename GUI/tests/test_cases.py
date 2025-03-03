#!/usr/bin/env python3

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Append the parent directory (GUI) to sys.path so that modules can be imported.
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import functions from your modules
import gmail_api
import rules_engine

# ----------------------- Unit Tests -----------------------

class TestGmailAPI(unittest.TestCase):
    def test_parse_date_valid(self):
        # A valid email date header.
        date_str = "Tue, 15 Nov 2022 12:45:26 +0000"
        dt = gmail_api.parse_date(date_str)
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.strftime('%Y-%m-%d'), '2022-11-15')
    
    def test_parse_date_invalid(self):
        # An invalid date string should return None.
        date_str = "Invalid Date String"
        dt = gmail_api.parse_date(date_str)
        self.assertIsNone(dt)

class TestRulesEngineUnit(unittest.TestCase):
    def test_match_condition_contains(self):
        condition = {"predicate": "contains", "value": "test"}
        self.assertTrue(rules_engine.match_condition("This is a test email", condition))
        self.assertFalse(rules_engine.match_condition("No match here", condition))
    
    def test_match_condition_date_less_than(self):
        condition = {"predicate": "less than", "value": "7", "unit": "days"}
        email_date = datetime.now() - timedelta(days=5)
        self.assertTrue(rules_engine.match_condition(email_date, condition))
    
    def test_match_condition_date_greater_than(self):
        condition = {"predicate": "greater than", "value": "7", "unit": "days"}
        email_date = datetime.now() - timedelta(days=10)
        self.assertTrue(rules_engine.match_condition(email_date, condition))
    
    def test_evaluate_email_all(self):
        email = {
            "from": "example@example.com",
            "subject": "Test Email",
            "received_date": datetime.now() - timedelta(days=3),
            "message": "This is a test email."
        }
        ruleset = {
            "match_policy": "All",
            "rules": [
                {"field": "From", "predicate": "contains", "value": "example"},
                {"field": "Subject", "predicate": "contains", "value": "Test"}
            ]
        }
        self.assertTrue(rules_engine.evaluate_email(email, ruleset))
    
    def test_evaluate_email_any(self):
        email = {
            "from": "user@domain.com",
            "subject": "Another Email",
            "received_date": datetime.now() - timedelta(days=1),
            "message": "No test content here."
        }
        ruleset = {
            "match_policy": "Any",
            "rules": [
                {"field": "From", "predicate": "contains", "value": "example"},
                {"field": "Subject", "predicate": "contains", "value": "Email"}
            ]
        }
        # Should return True because at least one condition (Subject) matches.
        self.assertTrue(rules_engine.evaluate_email(email, ruleset))

# ----------------------- Integration Tests -----------------------

class TestIntegration(unittest.TestCase):
    @patch('gmail_api.authenticate_gmail')
    @patch('gmail_api.list_emails')
    @patch('gmail_api.get_email')
    @patch('mysql_db.insert_email_mysql')
    def test_fetch_and_store_emails_integration(self, mock_insert_email, mock_get_email, mock_list_emails, mock_authenticate):
        # Setup mocks to simulate Gmail API responses.
        fake_service = MagicMock()
        mock_authenticate.return_value = fake_service
        
        # Simulate list_emails returning a fake message.
        fake_message = {"id": "12345"}
        mock_list_emails.return_value = [fake_message]
        
        # Simulate get_email returning fake email data.
        fake_email_data = {
            "email_id": "12345",
            "from": "test@example.com",
            "to": "user@example.com",
            "subject": "Integration Test",
            "received_date": datetime.now(),
            "message": "This is a test message."
        }
        mock_get_email.return_value = fake_email_data
        
        # Simulate insert_email_mysql returning a success message.
        mock_insert_email.return_value = "Stored email 12345"
        
        # Call fetch_and_store_emails (imported from rules_engine).
        from rules_engine import fetch_and_store_emails
        result = fetch_and_store_emails("1")
        self.assertIn("Stored email 12345", result)
    
    @patch('rules_engine.authenticate_gmail')
    @patch('rules_engine.fetch_emails_mysql')
    @patch('rules_engine.process_actions')
    def test_process_email_rules_integration(self, mock_process_actions, mock_fetch_emails, mock_authenticate):
        # Setup mocks to simulate the rules processing flow.
        fake_service = MagicMock()
        mock_authenticate.return_value = fake_service
        
        # Simulate fetch_emails_mysql returning a fake email.
        fake_email = {
            "email_id": "67890",
            "from": "rule@example.com",
            "subject": "Rule Test",
            "received_date": datetime.now() - timedelta(days=2),
            "message": "Apply rule."
        }
        mock_fetch_emails.return_value = [fake_email]
        
        # Create a fake ruleset.
        fake_ruleset = {
            "match_policy": "All",
            "rules": [
                {"field": "From", "predicate": "contains", "value": "rule"}
            ],
            "actions": [{"action": "mark as read"}]
        }
        
        # Patch load_rules to return our fake ruleset.
        with patch('rules_engine.load_rules', return_value=fake_ruleset):
            # Simulate process_actions returning a success message.
            mock_process_actions.return_value = "Email 67890 marked as read."
            result = rules_engine.process_email_rules()
            self.assertIn("Email 67890", result)
            self.assertIn("marked as read", result)

if __name__ == "__main__":
    unittest.main()
