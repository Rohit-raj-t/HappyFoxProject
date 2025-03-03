#!/usr/bin/env python3
import mysql.connector
from mysql.connector import Error
import config  # Using our project settings for consistent config

def create_database_if_not_exists(config_dict: dict) -> str:
    """
    Connect to MySQL and make the database if it's not already there.
    
    Args:
        config_dict (dict): Should have your MySQL details like host, user, password, and database name.
    
    Returns:
        str: Tells you if the database is set up or if something went wrong.
    """
    connection = None
    try:
        # Connect to the MySQL server with the given host, user, and password.
        connection = mysql.connector.connect(
            host=config_dict["host"],
            user=config_dict["user"],
            password=config_dict["password"]
        )
        cursor = connection.cursor()
        # Create the database if it doesn't exist.
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
    Set up the 'emails' table if it's not there yet.
    
    Returns:
        str: A message saying the table is set up or an error message if something went wrong.
    """
    connection = None
    try:
        # Connect using our DB settings from the config.
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
    Insert a new email into MySQL (or update it if it's already there).
    
    Args:
        email_data (dict): Contains details about the email.
    
    Returns:
        str: A message that tells you if the email was stored or if an error happened.
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
    Grab all the emails stored in MySQL and return them as a list of dictionaries.
    
    Returns:
        list: A list of emails with their details, or a string error message if something goes wrong.
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
