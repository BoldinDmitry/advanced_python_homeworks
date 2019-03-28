import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()


print(cursor.execute("SELECT name FROM sqlite_temp_master WHERE type='table';").fetchall())
