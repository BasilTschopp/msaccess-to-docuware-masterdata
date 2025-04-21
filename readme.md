# Master Data Scripts

This repository includes three scripts for managing master data entries (not document imports) — from MS Access to DocuWare.  
- `insert.py`: For importing entries  
- `delete.py`: For deleting all entries
- `view.py`: For displaying the SQLite cache

Install the required libraries with:

  ```bash
  pip install python-dotenv requests pandas pyodbc
  ```

## insert_select_list.py

### Overview
Automates the import of records from a Microsoft Access database into DocuWare. It ensures no duplicates are uploaded by tracking entries in a local SQLite database.

### Features

- Connects to an Access database via ODBC
- Uses a local SQLite database to track imported entries
- Authenticates with DocuWare using REST API
- Uploads selection list entries as structured JSON
- Logs all operations for traceability and debugging

### Workflow

1. Establish connection to Access database
2. Fetch and transform data using SQL and mapping logic
3. Check for duplicates in SQLite
4. Upload new selection list entries to DocuWare via API
5. Store import history in SQLite
6. Log all operations

### Configuration

Create a `.env` file with the following variables:

```
SQLITE=
ACCESS=
DW_URL=
DW_USER=
DW_PW=
DW_ORG=
DW_GUID=
SQLITE_DATABASE=
SQLITE_TABLE=
```

### Usage

Run the script with:

```bash
python insert.py
```

## delete_select_list.py

### Overview
Deletes all selection list entries from a DocuWare file cabinet and clears the local SQLite tracking table.

### Features

- Authenticates with DocuWare using REST API
- Deletes up to 10,000 entries per request, repeated until all are removed
- Clears the local SQLite table used for duplicate tracking
- Logs each deletion operation

### Workflow

1. Log in to DocuWare
2. Query all available entries (up to 10,000 per request)
3. Delete entries iteratively
4. Clear the local SQLite table
5. Log all operations

```bash
  pip install requests pandas pyodbc python-dotenv
```

### Configuration

Uses the same `.env` file as `insert_select_list_entries.py`.

### Usage

Run the script with:

```bash
python delete.py
```

## view_select_list.py

### Overview
Displays the current contents of the local SQLite database used for tracking selection list entries.

Run the script with:

```bash
python view.py
```