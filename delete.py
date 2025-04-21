import os
import sqlite3
import logging
import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

# --- CONSTANTS ---
# All constants are loaded from the environment file.
DW_URL  = os.getenv("DW_URL")
DW_USER = os.getenv("DW_USER")
DW_PW   = os.getenv("DW_PW")
DW_ORG  = os.getenv("DW_ORG")
DW_GUID = os.getenv("DW_GUID")
SQLITE_DATABASE = os.getenv("SQLITE_DATABASE")
SQLITE_TABLE    = os.getenv("SQLITE_TABLE")

# --- DOCUWARE SESSION ---
# Login requires not only a username and password, but also the organization name and license type.
# A status code other than 200 indicates a failed login attempt.
# Logout is performed using the session and the logout URL.
def login() -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{DW_URL}/Account/Logon",
        data={
            "UserName": DW_USER,
            "Password": DW_PW,
            "Organization": DW_ORG,
            "LicenseType": "NamedUser"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if response.status_code != 200:
        logging.error("Login failed: %s", response.text)
    else:
        logging.info("Login successful.")
    return session

# --- DELETE DOCUWARE DATA ---
# Deletes all data entries (not documents) from the specified DocuWare file cabinet.
# The request is repeated in batches of 10,000 until no more entries are found.
def delete_docuware_data(session: requests.Session) -> None:

    while True:
        url = f"{DW_URL}/FileCabinets/{DW_GUID}/Documents?count=10000&query=DWDocID:*"
        response = session.get(url, headers={"Accept": "application/json"})

        if response.status_code != 200:
            logging.error("Failed to load data: %s", response.status_code)
            logging.error(response.text)
            break

        items = response.json().get("Items", [])
        data_count = len(items)
        logging.info("Found %d DocuWare data entries to delete.", data_count)

        if data_count == 0:
            logging.info("No more DocuWare data found. Exiting deletion loop.")
            break

        for item in items:
            data_id = item.get("Id") or item.get("DocID")
            del_url = f"{DW_URL}/FileCabinets/{DW_GUID}/Documents/{data_id}"
            del_response = session.delete(del_url)
            if del_response.status_code == 200:
                logging.info("Deleted DocuWare data entry ID: %s", data_id)
            else:
                logging.error("Failed to delete DocuWare data entry %s: %s", data_id, del_response.text)

# --- CLEAR SQLITE TABLE ---
# Clears the local SQLite table 'cache_table' that tracks processed entries.
def clear_sqlite_table() -> None:
    try:
        with sqlite3.connect(SQLITE_DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {SQLITE_TABLE}")
            conn.commit()
        logging.info(f"Local table '{SQLITE_TABLE}' cleared.")
    except Exception as e:
        logging.error("SQLite cleanup failed: %s", e)

# --- MAIN ENTRY POINT ---
# Logs into DocuWare, deletes data entries from DocuWare, and clears the local SQLite database cache.
def main() -> None:

    try:
        session = login()
        delete_docuware_data(session)
        clear_sqlite_table()

    except Exception as e:
        logging.error("Script failed: %s", e)

if __name__ == "__main__":
    main()