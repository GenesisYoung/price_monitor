import sqlite3

con=sqlite3.connect("../sql/sku.db")
cur=con.cursor()
with open("../sql/insert.sql", 'r', encoding="utf-8") as f:
    sql_script=f.read()

cur.executescript(sql_script)

con.commit()
con.close()