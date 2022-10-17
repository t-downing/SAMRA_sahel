import pyodbc 
import os

cnxn = pyodbc.connect(
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=tcp:gvalabaidb03t.gva.icrc.priv;"
    "Database=SAMRA;"
    "Trusted_Connection=yes;"
    f'PASSWORD={os.environ.get("MSSQL_PASSWORD")}'
    'USER=l_samra_sql_t'

)
