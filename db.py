import sqlite3
from sqlite3 import Cursor,Connection


def connect_db(name:str="sku.db")->Connection:
    con=sqlite3.connect(name)
    return con

def init_sql(cur:Cursor):
    # SKU records that fetched
    cur.execute("CREATE TABLE sku_item(" \
    "seller TEXT," \
    "seller_link TEXT," \
    "title TEXT," \
    "price REAL," \
    "sub_price REAL," \
    "is_legal NUMERIC," \
    "sku_id TEXT," \
    "big_pic TEXT)")
    # SKU standard
    cur.execute("CREATE TABLE sku_standard(" \
    "sku_id TEXT," \
    "sku TEXT," \
    "sku_price REAL," \
    "promot_price REAL)")