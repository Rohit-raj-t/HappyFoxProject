#!/usr/bin/env python3
import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext, ttk
import json
import config  # Import the whole config module
from mysql_db import create_database_if_not_exists, create_mysql_table
from rules_engine import process_email_rules, fetch_and_store_emails

# ----------------- Action Row for Rule Editor -----------------
class ActionRow(tk.Frame):
    ACTIONS = ["Mark as Read", "Mark as Unread", "Move Message"]
    MOVE_DESTINATIONS = ["Inbox", "Forum", "Updates", "Promotions"]

    def __init__(self, master):
        super().__init__(master)
        self.action_var = tk.StringVar(value=self.ACTIONS[0])
        self.destination_var = tk.StringVar(value=self.MOVE_DESTINATIONS[0])
        self.create_widgets()

    def create_widgets(self):
        self.action_cb = ttk.Combobox(self, textvariable=self.action_var, values=self.ACTIONS, width=20)
        self.action_cb.grid(row=0, column=0, padx=2)
        self.action_cb.bind("<<ComboboxSelected>>", self.update_destination_visibility)
        
        # Destination drop-down; only visible for Move Message.
        self.destination_cb = ttk.Combobox(self, textvariable=self.destination_var, values=self.MOVE_DESTINATIONS, width=20)
        self.destination_cb.grid(row=0, column=1, padx=2)
        if self.action_var.get().lower() != "move message":
            self.destination_cb.grid_remove()
        
        self.remove_btn = tk.Button(self, text="Remove",
                                    command=lambda: self.master.master.remove_action_row(self))
        self.remove_btn.grid(row=0, column=2, padx=2)

    def update_destination_visibility(self, event=None):
        if self.action_var.get().lower() == "move message":
            self.destination_cb.grid()
        else:
            self.destination_cb.grid_remove()

    def get_action(self):
        action = self.action_var.get().strip()
        if not action:
            return None
        action_dict = {"action": action.lower()}
        if action.lower() == "move message":
            destination = self.destination_var.get().strip()
            if not destination:
                return None
            action_dict["destination"] = destination.lower()
        return action_dict

# ----------------- Updated Rule Editor Window -----------------
class RuleEditorWindow(tk.Toplevel):
    """A Toplevel window for creating/editing processing rules."""
    def __init__(self, master):
        super().__init__(master)
        self.title("Rule Editor")
        self.geometry("800x500")
        self.rules_applied = False  # Flag to indicate if rules were applied
        self.condition_rows = []
        self.action_rows = []
        self.create_widgets()

    def create_widgets(self):
        instructions = (
            "Enter your rules below. Each rule consists of a Condition with the following columns:\n"
            "- Field: Choose from [From, To, Subject, Received Date/Time, Message]\n"
            "- Predicate: For text fields use [contains, does not contain, equals, does not equal];\n"
            "  for 'Received Date/Time' use [less than, greater than]\n"
            "- Value: Enter the text to search for, or number of days/months (if applicable)\n"
            "- Unit: Only applicable for 'Received Date/Time' (default is 'days', or select 'months')\n"
            "\nBelow, add one or more Actions. You can add or remove actions.\n"
            "For actions, select the action type. For 'Move Message', choose the destination folder."
        )
        tk.Label(self, text=instructions, justify="left").pack(padx=10, pady=5, anchor="w")
        
        # Conditions section
        conditions_label = tk.Label(self, text="Conditions:")
        conditions_label.pack(padx=10, pady=(5, 0), anchor="w")
        self.conditions_frame = tk.Frame(self)
        self.conditions_frame.pack(fill="x", padx=10, pady=5)
        # Header for conditions
        header = tk.Frame(self.conditions_frame)
        header.pack(fill="x")
        tk.Label(header, text="Field", width=20, borderwidth=1, relief="solid").grid(row=0, column=0)
        tk.Label(header, text="Predicate", width=20, borderwidth=1, relief="solid").grid(row=0, column=1)
        tk.Label(header, text="Value", width=20, borderwidth=1, relief="solid").grid(row=0, column=2)
        tk.Label(header, text="Unit (if applicable)", width=20, borderwidth=1, relief="solid").grid(row=0, column=3)
        tk.Label(header, text="Action", width=10, borderwidth=1, relief="solid").grid(row=0, column=4)
        self.rows_container = tk.Frame(self.conditions_frame)
        self.rows_container.pack(fill="x")
        tk.Button(self, text="Add Condition", command=self.add_condition_row)\
            .pack(padx=10, pady=5, anchor="w")
        
        # Overall match policy
        policy_frame = tk.Frame(self)
        policy_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(policy_frame, text="Match Policy (All/Any):").grid(row=0, column=0, sticky="w")
        self.match_policy_var = tk.StringVar(value="All")
        ttk.Combobox(policy_frame, textvariable=self.match_policy_var, values=["All", "Any"], width=10)\
            .grid(row=0, column=1, sticky="w", padx=5)
        
        # Actions section
        actions_label = tk.Label(self, text="Actions:")
        actions_label.pack(padx=10, pady=(10, 0), anchor="w")
        self.actions_frame = tk.Frame(self)
        self.actions_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(self, text="Add Action", command=self.add_action_row)\
            .pack(padx=10, pady=5, anchor="w")
        
        # Button frame with Apply and Exit buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(padx=10, pady=10)
        tk.Button(btn_frame, text="Apply Rules", command=self.save_rules)\
            .grid(row=0, column=0, padx=10)
        tk.Button(btn_frame, text="Exit", command=self.destroy)\
            .grid(row=0, column=1, padx=10)
        
        # Start with one condition row and one action row by default
        self.add_condition_row()
        self.add_action_row()

    def add_condition_row(self):
        row = ConditionRow(self.rows_container)
        row.pack(fill="x", pady=2)
        self.condition_rows.append(row)

    def add_action_row(self):
        row = ActionRow(self.actions_frame)
        row.pack(fill="x", pady=2)
        self.action_rows.append(row)

    def remove_action_row(self, row):
        row.destroy()
        self.action_rows.remove(row)

    def remove_condition_row(self, row):
        row.destroy()
        self.condition_rows.remove(row)

    def save_rules(self):
        rules = []
        for row in self.condition_rows:
            cond = row.get_condition()
            if cond is None:
                messagebox.showerror("Error", "Please fill all condition fields correctly.")
                return
            rules.append(cond)
        actions = []
        for row in self.action_rows:
            act = row.get_action()
            if act is None:
                messagebox.showerror("Error", "Please fill all action fields correctly.")
                return
            actions.append(act)
        ruleset = {
            "match_policy": self.match_policy_var.get(),
            "rules": rules,
            "actions": actions
        }
        with open(config.RULES_FILE, "w") as f:
            json.dump(ruleset, f, indent=4)
        messagebox.showinfo("Success", "Rules saved successfully.")
        self.rules_applied = True
        self.destroy()  # Close the rule editor window

# ----------------- ConditionRow -----------------
class ConditionRow(tk.Frame):
    FIELDS = ["From", "To", "Subject", "Received Date/Time", "Message"]
    PREDICATES_TEXT = ["contains", "does not contain", "equals", "does not equal"]
    PREDICATES_DATE = ["less than", "greater than"]

    def __init__(self, master):
        super().__init__(master)
        self.field_var = tk.StringVar(value=self.FIELDS[0])
        self.predicate_var = tk.StringVar()
        self.value_var = tk.StringVar()
        self.unit_var = tk.StringVar(value="days")
        self.create_widgets()

    def create_widgets(self):
        self.field_cb = ttk.Combobox(self, textvariable=self.field_var, values=self.FIELDS, width=18)
        self.field_cb.grid(row=0, column=0, padx=2)
        self.field_cb.bind("<<ComboboxSelected>>", self.update_predicates)
        self.predicate_cb = ttk.Combobox(self, textvariable=self.predicate_var, values=self.PREDICATES_TEXT, width=18)
        self.predicate_cb.grid(row=0, column=1, padx=2)
        self.value_entry = tk.Entry(self, textvariable=self.value_var, width=18)
        self.value_entry.grid(row=0, column=2, padx=2)
        self.unit_cb = ttk.Combobox(self, textvariable=self.unit_var, values=["days", "months"], width=18)
        self.unit_cb.grid(row=0, column=3, padx=2)
        self.unit_cb.grid_remove()
        self.remove_btn = tk.Button(self, text="Remove",
                                    command=lambda: self.master.master.remove_condition_row(self))
        self.remove_btn.grid(row=0, column=4, padx=2)

    def update_predicates(self, event=None):
        field = self.field_var.get()
        if field == "Received Date/Time":
            self.predicate_cb['values'] = self.PREDICATES_DATE
            self.unit_cb.grid()
        else:
            self.predicate_cb['values'] = self.PREDICATES_TEXT
            self.unit_cb.grid_remove()

    def get_condition(self):
        field = self.field_var.get().strip()
        predicate = self.predicate_var.get().strip()
        value = self.value_var.get().strip()
        if not field or not predicate or not value:
            return None
        cond = {
            "field": field,
            "predicate": predicate,
            "value": value
        }
        if field == "Received Date/Time":
            cond["unit"] = self.unit_var.get().strip() or "days"
        return cond

# ----------------- Main Application -----------------
class GmailCRUDApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("G-helper")
        self.geometry("700x700")
        # New Server field added with default 'localhost'
        self.server = tk.StringVar(value="localhost")
        self.db_user = tk.StringVar(value="root")
        self.db_password = tk.StringVar()
        self.db_name = tk.StringVar(value="gmailcrud")
        self.oauth_file = tk.StringVar(value="credentials.json")
        self.retrieval_method = tk.StringVar(value="Number of Messages")
        self.message_number = tk.StringVar(value="10")
        self.timeframe_number = tk.StringVar(value="7")
        self.timeframe_unit = tk.StringVar(value="Days")
        self.create_widgets()

    def create_widgets(self):
        self.build_config_frame()
        self.build_ops_frame()
        self.build_output_area()

    def build_config_frame(self):
        config_frame = tk.LabelFrame(self, text="Configuration", padx=10, pady=10)
        config_frame.pack(fill="x", padx=10, pady=5)
        # Server field
        tk.Label(config_frame, text="Server:").grid(row=0, column=0, sticky="e")
        tk.Entry(config_frame, textvariable=self.server, width=25).grid(row=0, column=1, padx=5, pady=2)
        
        tk.Label(config_frame, text="MySQL Username:").grid(row=1, column=0, sticky="e")
        tk.Entry(config_frame, textvariable=self.db_user, width=25).grid(row=1, column=1, padx=5, pady=2)
        tk.Label(config_frame, text="MySQL Password:").grid(row=2, column=0, sticky="e")
        tk.Entry(config_frame, textvariable=self.db_password, show="*", width=25).grid(row=2, column=1, padx=5, pady=2)
        tk.Label(config_frame, text="Database Name:").grid(row=3, column=0, sticky="e")
        tk.Entry(config_frame, textvariable=self.db_name, width=25).grid(row=3, column=1, padx=5, pady=2)
        tk.Label(config_frame, text="OAuth Credentials File:").grid(row=4, column=0, sticky="e")
        tk.Entry(config_frame, textvariable=self.oauth_file, width=25).grid(row=4, column=1, padx=5, pady=2)
        tk.Button(config_frame, text="Browse", command=self.browse_oauth_file).grid(row=4, column=2, padx=5, pady=2)
        
        # Retrieval Method Section
        tk.Label(config_frame, text="Retrieval Method:").grid(row=5, column=0, sticky="e")
        retrieval_options = ["Number of Messages", "Timeframe"]
        retrieval_menu = ttk.Combobox(config_frame, textvariable=self.retrieval_method, values=retrieval_options, width=22)
        retrieval_menu.grid(row=5, column=1, padx=5, pady=2)
        retrieval_menu.bind("<<ComboboxSelected>>", self.update_retrieval_fields)
        
        # Frame for number of messages
        self.message_number_frame = tk.Frame(config_frame)
        tk.Label(self.message_number_frame, text="Number:").grid(row=0, column=0, sticky="e")
        tk.Entry(self.message_number_frame, textvariable=self.message_number, width=10).grid(row=0, column=1, padx=5)
        self.message_number_frame.grid(row=6, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        
        # Frame for timeframe
        self.timeframe_frame = tk.Frame(config_frame)
        tk.Label(self.timeframe_frame, text="Timeframe:").grid(row=0, column=0, sticky="e")
        tk.Entry(self.timeframe_frame, textvariable=self.timeframe_number, width=10).grid(row=0, column=1, padx=5)
        timeframe_unit_options = ["Days", "Months"]
        ttk.Combobox(self.timeframe_frame, textvariable=self.timeframe_unit, values=timeframe_unit_options, width=10)\
            .grid(row=0, column=2, padx=5)
        self.timeframe_frame.grid_forget()  # Hide timeframe frame by default
        
        tk.Button(config_frame, text="Save Configuration", command=self.update_config)\
            .grid(row=7, column=0, columnspan=3, pady=5)

    def build_ops_frame(self):
        ops_frame = tk.LabelFrame(self, text="Operations", padx=10, pady=10)
        ops_frame.pack(fill="x", padx=10, pady=5)
        self.fetch_button = tk.Button(ops_frame, text="Fetch Emails", command=self.fetch_emails_threaded)
        self.fetch_button.grid(row=0, column=0, padx=5, pady=5)
        self.apply_button = tk.Button(ops_frame, text="Apply Rules", command=self.open_rule_editor_threaded)
        self.apply_button.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(ops_frame, text="Exit", command=self.quit).grid(row=0, column=2, padx=5, pady=5)

    def build_output_area(self):
        self.output_text = scrolledtext.ScrolledText(self, height=30)
        self.output_text.pack(fill="both", padx=10, pady=5)

    def update_retrieval_fields(self, event=None):
        method = self.retrieval_method.get()
        if method == "Number of Messages":
            self.timeframe_frame.grid_forget()
            self.message_number_frame.grid(row=6, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        elif method == "Timeframe":
            self.message_number_frame.grid_forget()
            self.timeframe_frame.grid(row=6, column=0, columnspan=2, sticky="w", padx=5, pady=2)

    def browse_oauth_file(self):
        file_path = filedialog.askopenfilename(title="Select OAuth Credentials File",
                                               filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if file_path:
            self.oauth_file.set(file_path)

    def update_config(self):
        import config  # Import the module to reference its attributes
        if not self.server.get() or not self.db_user.get() or not self.db_password.get() or not self.db_name.get():
            messagebox.showerror("Error", "Please fill in Server, MySQL username, password, and database name.")
            return
        # Update DB_CONFIG via the config module
        config.DB_CONFIG.clear()
        config.DB_CONFIG.update({
            "host": self.server.get().strip(),
            "user": self.db_user.get(),
            "password": self.db_password.get(),
            "database": self.db_name.get()
        })
        # Process the OAuth credentials file path
        cred_path = self.oauth_file.get().strip()
        if not os.path.isabs(cred_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            cred_path = os.path.join(base_dir, cred_path)
        if not os.path.exists(cred_path):
            messagebox.showerror("Error", f"Credentials file not found: {cred_path}")
            return
        print("Using OAuth credentials file at:", cred_path)
        # Update the config module's variable
        config.OAUTH_CREDENTIALS_FILE = cred_path
        self.append_output("Configuration updated.")
        db_result = create_database_if_not_exists(config.DB_CONFIG)
        if db_result.startswith("Error"):
            messagebox.showerror("Connection Error", f"Please check your connection.\n{db_result}")
            return
        self.append_output(db_result)
        table_result = create_mysql_table()
        if table_result.startswith("Error"):
            messagebox.showerror("Connection Error", f"Please check your connection.\n{table_result}")
            return
        self.append_output(table_result)

    def run_task(self, task_func):
        """Runs a task function in a separate thread and disables operation buttons."""
        self.disable_ops_buttons()
        def wrapper():
            try:
                task_func()
            finally:
                self.after(0, self.enable_ops_buttons)
        threading.Thread(target=wrapper, daemon=True).start()

    def disable_ops_buttons(self):
        self.fetch_button.config(state="disabled")
        self.apply_button.config(state="disabled")

    def enable_ops_buttons(self):
        self.fetch_button.config(state="normal")
        self.apply_button.config(state="normal")

    def fetch_emails(self):
        self.update_config()
        if self.retrieval_method.get() == "Number of Messages":
            msg_param = self.message_number.get().strip() or "100"
        else:
            num = self.timeframe_number.get().strip() or "7"
            unit = self.timeframe_unit.get().strip().lower()
            unit_letter = "d" if unit == "days" else "m"
            msg_param = f"newer_than:{num}{unit_letter}"
        result = fetch_and_store_emails(msg_param)
        self.append_output(result)

    def fetch_emails_threaded(self):
        self.run_task(self.fetch_emails)

    def open_rule_editor(self):
        editor = RuleEditorWindow(self)
        self.wait_window(editor)
        # Only process emails if rules were applied
        if getattr(editor, "rules_applied", False):
            self.process_emails()

    def open_rule_editor_threaded(self):
        self.run_task(self.open_rule_editor)

    def process_emails(self):
        self.update_config()
        result = process_email_rules()
        self.append_output(result)

    def append_output(self, text):
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)

if __name__ == "__main__":
    import threading  # Ensure threading is imported
    app = GmailCRUDApp()
    app.mainloop()
