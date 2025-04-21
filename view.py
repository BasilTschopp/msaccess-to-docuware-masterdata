import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

SQLITE_DATABASE = os.getenv("SQLITE_DATABASE")
SQLITE_TABLE = os.getenv("SQLITE_TABLE")

# Connects to the local SQLite database and prints all records
# from the specified table in a formatted output.
def print_sqlite_table():
    try:
        conn = sqlite3.connect(SQLITE_DATABASE)
        cursor = conn.cursor()

        cursor.execute(f"SELECT * FROM {SQLITE_TABLE}")
        rows = cursor.fetchall()

        if not rows:
            print("No records found.")
        else:
            print(f"Records in '{SQLITE_TABLE}':\n")
            columns = [desc[0] for desc in cursor.description]
            print(" | ".join(columns))
            print("-" * 80)
            for row in rows:
                print(" | ".join(str(cell) if cell is not None else "" for cell in row))

        conn.close()
    except Exception as e:
        print(f"Error reading from SQLite: {e}")

if __name__ == "__main__":
    print_sqlite_table()