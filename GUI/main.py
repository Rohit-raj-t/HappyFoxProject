#!/usr/bin/env python3

# This is our main entry point for the Gmail CRUD app.
# It imports the main GUI class from gui_components, creates the app,
# and starts the Tkinter event loop so the window stays open.
from gui_components import GmailCRUDApp

if __name__ == "__main__":
    app = GmailCRUDApp()
    app.mainloop()
