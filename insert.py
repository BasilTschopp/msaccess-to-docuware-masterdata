# --- IMPORTS ---
import os
import sqlite3
import requests
import pandas as pd
import pyodbc
import logging
import math
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
ACCESS  = os.getenv("ACCESS")
SQLITE_DATABASE = os.getenv("SQLITE_DATABASE")
SQLITE_TABLE    = os.getenv("SQLITE_TABLE")

# --- DATABASE SETUP ---
# Connect to MS Access using ODBC
def connect_access():
    try:
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            f'DBQ={ACCESS};'
        )
        return pyodbc.connect(conn_str)
    except Exception as e:
        logging.error("Failed to connect to Access: %s", e)
        return None

# Connect to SQLite and create the table if it does not exist
class SQLiteManager:
    def __init__(self):
        self.db_path = SQLITE_DATABASE
        self.table_name = SQLITE_TABLE

    def execute(self, query, params=None, fetch=False):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(query, params or ())
            if fetch:
                return cur.fetchall()

    def setup(self):
        self.execute(f"""CREATE TABLE IF NOT EXISTS {self.table_name} (id TEXT PRIMARY KEY, field1 TEXT, field2 TEXT)""")
        logging.info(f"SQLite table '{self.table_name}' initialized.")

    def is_duplicate(self, field1, field2):
        query = f"""SELECT 1 FROM {self.table_name} WHERE field1 = ? AND field2 = ?"""
        result = self.execute(query, (field1 or "", field2 or ""), fetch=True)
        return bool(result)

    def insert(self, id_val, **fields):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"""INSERT OR REPLACE INTO {self.table_name} (id, field1, field2) VALUES (?, ?, ?)""",
                (id_val, fields.get("field1"), fields.get("field2"))
            )
            conn.commit()
        logging.info("Eintrag gespeichert: %s", id_val)

# --- DOCUWARE SESSION ---
# Login requires not only a username and password, but also the organization name and license type.
# A status code other than 200 indicates a failed login attempt.
# Logout is performed using the session and the logout URL.
def docuware_login():
    session = requests.Session()
    response = session.post(
        f"{DW_URL}/Account/Logon",data={"UserName": DW_USER, "Password": DW_PW, "Organization": DW_ORG,"LicenseType": "NamedUser"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if response.status_code != 200:
        logging.error("DocuWare login failed: %s", response.text)
        raise Exception("DocuWare login failed.")
    logging.info("DocuWare login successful.")
    return session

def docuware_logout(session):
    try:
        session.post(f"{DW_URL}/Account/Logoff")
        logging.info("DocuWare logout successful.")
    except Exception as e:
        logging.error("DocuWare logout error: %s", e)

# --- UTILITY FUNCTIONS ---
# Executes the given SQL query using an MS Access connection.
# Returns a pandas DataFrame with the results, or an empty DataFrame on failure.
def fetch_data(query):
    conn = connect_access()
    if conn is None:
        return pd.DataFrame()
    try:
        df = pd.read_sql_query(query, conn)
        conn.close()
        logging.info("Data fetched successfully.")
        return df
    except Exception as e:
        logging.error("Failed to fetch data: %s", e)
        return pd.DataFrame()

# Sends data to DocuWare without attaching a document file.
# The entry is created in the specified file cabinet using the active session.
def send_to_docuware(fields, session):
    payload = {"Fields": fields}
    response = session.post(
        f"{DW_URL}/FileCabinets/{DW_GUID}/Documents",
        json=payload,
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    return response

# --- IMPORT FUNCTION ---
# Imports records from a DataFrame into DocuWare based on the given field mapping and item type.
# Duplicate entries are skipped using the SQLite manager.
# Successfully imported records are logged and stored in the local tracking database.
def import_records(df, field_mapping, session, sqlite_manager):
    def build_fields(row):
        fields = []
        for field_name, source in field_mapping.items():
            value = row.get(source, source)
            if pd.isna(value) or (isinstance(value, float) and math.isnan(value)):
                value = ""
            fields.append({"FieldName": field_name, "Item": value})
        return fields

    for _, row in df.iterrows():
        field1 = row.get("field1", "")
        field2 = row.get("field2", "")

        if sqlite_manager.is_duplicate(field1, field2):
            logging.info("Eintrag bereits importiert – übersprungen.")
            continue

        fields = build_fields(row)
        response = send_to_docuware(fields, session)

        if response.status_code == 200:
            logging.info("Eintrag erfolgreich importiert.")
            sqlite_manager.insert(f"ID_{hash(field1+field2)}", field1=field1, field2=field2)
        else:
            logging.error("Fehler beim Import: %s", response.status_code)
            logging.error("Antwort: %s", response.text)

# Enables triggering multiple import functions, each of which can support a different set of hardcoded fields.
def import_set1(session, sqlite_manager):
    query = """SELECT field1, field2 FROM source_table"""
    df = fetch_data(query)

    if df.empty:
        logging.warning("Aborted: No data found for import.")
        return

    field_mapping = {"field1": "field1", "field2": "field2"}
    import_records(df, field_mapping, session, sqlite_manager)

# --- MAIN ENTRY POINT ---
# Logs into DocuWare and imports data.
# The local SQLite database, including duplicate checking, is integrated into the import function.
def main():
    sqlite_manager = SQLiteManager()
    sqlite_manager.setup()

    while True:
        session = None
        try:
            session = docuware_login()
            import_set1(session, sqlite_manager)
            break
        finally:
            if session:
                docuware_logout(session)

if __name__ == "__main__":
    main()