#!/usr/bin/env python3
import mysql.connector
from mysql.connector import Error
import config  # Import the whole config module for consistent configuration access

def create_database_if_not_exists(config_dict: dict) -> str:
    """
    Connects to MySQL and creates the specified database if it doesn't exist.

    Args:
        config_dict (dict): A dictionary containing MySQL connection details.
                            Expected keys: host, user, password, database.

    Returns:
        str: A message indicating whether the database is ready or an error occurred.
    """
    connection = None
    try:
        connection = mysql.connector.connect(
            host=config_dict["host"],
            user=config_dict["user"],
            password=config_dict["password"]
        )
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config_dict['database']}")
        connection.commit()
        return f"Database '{config_dict['database']}' is ready."
    except Error as e:
        return f"Error creating database: {e}"
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def create_mysql_table() -> str:
    """
    Creates the 'emails' table in the specified database if it does not exist.

    Returns:
        str: A message indicating whether the table is ready or an error occurred.
    """
    connection = None
    try:
        connection = mysql.connector.connect(**config.DB_CONFIG)
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
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def insert_email_mysql(email_data: dict) -> str:
    """
    Inserts a fetched email into MySQL (or updates it if it already exists).

    Args:
        email_data (dict): A dictionary containing email details.

    Returns:
        str: A message indicating whether the email was stored or an error occurred.
    """
    connection = None
    try:
        connection = mysql.connector.connect(**config.DB_CONFIG)
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
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def fetch_emails_mysql():
    """
    Fetches all stored emails from MySQL and returns them as a list of dictionaries.

    Returns:
        list: A list of dictionaries containing email data, or an error message as a string.
    """
    emails = []
    connection = None
    try:
        connection = mysql.connector.connect(**config.DB_CONFIG)
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
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
