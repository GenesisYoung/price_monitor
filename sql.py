import sqlite3

con=sqlite3.connect("sku.db")
cur=con.cursor()
with open("insert.sql",'r',encoding="utf-8") as f:
    sql_script=f.read()

cur.executescript(sql_script)

con.commit()
con.close()