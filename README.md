# G-helper Application
=====================================

## Overview
------------

The G-helper Application is a Python-based tool that integrates the Gmail API, rule-based email processing, and
MySQL database interactions. The application features a user-friendly Tkinter GUI for configuration, email
fetching, and rule management.

## Features
-------------

* **Gmail API Authentication:** Securely authenticate using OAuth 2.0.
* **Rule-Based Email Processing:** Define custom rules to automate email management.
* **MySQL Database Integration:** Automatically create and manage a MySQL database to store email data.
* **Intuitive GUI:** Built with Tkinter for easy configuration and operation.

## Project Structure
--------------------

```markdown
├── config.py                # Global configuration settings (OAuth, DB, rules file path)
├── gmail_api.py             # Gmail API authentication and email retrieval functions
├── mysql_db.py              # MySQL operations (database/table creation, email insertion/fetching)
├── rules_engine.py          # Rule engine for processing emails based on JSON-defined rules
├── gui_components.py        # GUI components including RuleEditorWindow, ActionRow, ConditionRow, etc.
├── main.py                  # Main application entry point that initializes the GUI
├── rules.json               # Default rules file
├── README.md                # Project documentation
└── tests
    ├── __init__.py
    └── test_cases.py
```


## Prerequisites
----------------

* **Python 3.6+**
* **Required Libraries:**
        + `tkinter` (bundled with Python)
        + `google-auth-oauthlib`
        + `google-api-python-client`
        + `mysql-connector-python`
* **Other Requirements:**
        + A running MySQL server (local or remote)
        + Gmail API credentials file (e.g., `credentials.json`)

## Installation
---------------

1. Clone the Repository:

```bash
git clone https://github.com/Rohit-raj-t/HappyFoxProject.git
cd HappyFoxProject/GUI
```

2. Create and Activate a Virtual Environment (Recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the Required Packages:

```bash
pip install -r requirements.txt
```

## Configuration
---------------

### OAuth Credentials:
Place your `credentials.json` file in the project directory, or update the path in `config.py`.

### Database Settings:
Configure your MySQL username, password, and database name through the application's GUI.

### Rules File:
The default rules file is `rules.json`. Use the built-in Rule Editor to create or modify rules.

## Usage
-----

1. Run the Application:

```bash
python main.py
```

2. Configure the Application:
In the GUI, enter your MySQL credentials, select your OAuth credentials file, and choose the email retrieval
method (by number of messages or timeframe).

3. Initialize the Database:
Click Save Configuration to create the database and tables.

4. Fetch Emails:
Click the Fetch Emails button to retrieve emails from Gmail and store them in the database.

5. Manage Rules:
Open the Rule Editor to define conditions and actions for processing emails. Once saved, click Apply Rules to
execute the rules on stored emails.

6. Review Output:
The output area displays status messages, including results of configuration, fetching, and rule processing.

## Design Decisions
-----------------

* **Modular Design:** The project is divided into separate modules (Gmail API, database operations, rule
processing, GUI) to facilitate easier maintenance and scalability.
* **Security with OAuth:** OAuth 2.0 is used for Gmail API authentication, ensuring secure access without exposing
sensitive credentials.
* **Rule-Based Engine:** A JSON-based rule engine allows users to define dynamic conditions and actions,
automating email management.
* **Tkinter GUI:** The GUI is designed to be simple and intuitive, providing easy access to configuration, email
fetching, and rule management functionalities.
-----

## Screenshots
- Main-App
  
    <img src="https://github.com/user-attachments/assets/da88bc12-4ec4-4bf4-8736-d5e50d09acdd" alt="image" width="500" height="500">

- Rule-Editor
  
    <img src="https://github.com/user-attachments/assets/253e2083-3a52-41d3-94fc-875bbd064886" alt="image" width="500" height="450">


---
---
Thank you for using the G-helper Application!
