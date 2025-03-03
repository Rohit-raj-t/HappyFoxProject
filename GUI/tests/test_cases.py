#!/usr/bin/env python3

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add the parent directory (GUI) to sys.path so our modules can be imported.
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import functions from our project modules
import gmail_api
import rules_engine

# ----------------------- Unit Tests -----------------------
class TestGmailAPI(unittest.TestCase):
    def test_parse_date_valid(self):
        # Test with a proper email date header.
        date_str = "Tue, 15 Nov 2022 12:45:26 +0000"
        dt = gmail_api.parse_date(date_str)
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.strftime('%Y-%m-%d'), '2022-11-15')
    
    def test_parse_date_invalid(self):
        # When the date string is bogus, we should get None.
        date_str = "Invalid Date String"
        dt = gmail_api.parse_date(date_str)
        self.assertIsNone(dt)

class TestRulesEngineUnit(unittest.TestCase):
    def test_match_condition_contains(self):
        # Check if the 'contains' condition works for text.
        condition = {"predicate": "contains", "value": "test"}
        self.assertTrue(rules_engine.match_condition("This is a test email", condition))
        self.assertFalse(rules_engine.match_condition("No match here", condition))
    
    def test_match_condition_date_less_than(self):
        # Test the date condition: email received less than 7 days ago.
        condition = {"predicate": "less than", "value": "7", "unit": "days"}
        email_date = datetime.now() - timedelta(days=5)
        self.assertTrue(rules_engine.match_condition(email_date, condition))
    
    def test_match_condition_date_greater_than(self):
        # Test the date condition: email received more than 7 days ago.
        condition = {"predicate": "greater than", "value": "7", "unit": "days"}
        email_date = datetime.now() - timedelta(days=10)
        self.assertTrue(rules_engine.match_condition(email_date, condition))
    
    def test_evaluate_email_all(self):
        # Test evaluating an email when ALL conditions must match.
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
        # Test evaluating an email when ANY condition is enough to match.
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
        # Since the subject contains "Email", at least one condition is met.
        self.assertTrue(rules_engine.evaluate_email(email, ruleset))

# ----------------------- Integration Tests -----------------------
class TestIntegration(unittest.TestCase):
    @patch('gmail_api.authenticate_gmail')
    @patch('gmail_api.list_emails')
    @patch('gmail_api.get_email')
    @patch('mysql_db.insert_email_mysql')
    def test_fetch_and_store_emails_integration(self, mock_insert_email, mock_get_email, mock_list_emails, mock_authenticate):
        # Setup mocks to fake Gmail API responses.
        fake_service = MagicMock()
        mock_authenticate.return_value = fake_service
        
        # Simulate list_emails returning one fake message.
        fake_message = {"id": "12345"}
        mock_list_emails.return_value = [fake_message]
        
        # Simulate get_email returning fake email details.
        fake_email_data = {
            "email_id": "12345",
            "from": "test@example.com",
            "to": "user@example.com",
            "subject": "Integration Test",
            "received_date": datetime.now(),
            "message": "This is a test message."
        }
        mock_get_email.return_value = fake_email_data
        
        # Simulate a successful insert into the database.
        mock_insert_email.return_value = "Stored email 12345"
        
        # Call the function to fetch and store emails.
        from rules_engine import fetch_and_store_emails
        result = fetch_and_store_emails("1")
        self.assertIn("Stored email 12345", result)
    
    @patch('rules_engine.authenticate_gmail')
    @patch('rules_engine.fetch_emails_mysql')
    @patch('rules_engine.process_actions')
    def test_process_email_rules_integration(self, mock_process_actions, mock_fetch_emails, mock_authenticate):
        # Setup mocks to fake the rules processing flow.
        fake_service = MagicMock()
        mock_authenticate.return_value = fake_service
        
        # Simulate fetching one fake email from the database.
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
