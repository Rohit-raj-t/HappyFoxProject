#!/usr/bin/env python3

import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG

def create_database_if_not_exists(config):
    """Connects to MySQL and creates the specified database if it doesn't exist."""
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
    """Creates the 'emails' table in the selected database if it does not exist."""
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
    """Inserts a fetched email into MySQL (or updates it if it already exists)."""
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
    """Fetches all stored emails from MySQL and returns them as a list of dictionaries."""
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