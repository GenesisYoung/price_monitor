import asyncio,os
from tmall import *
from db import *

async def main():
    # await create_session()
    try:
        con = connect_db()
        cur = con.cursor()
        if not os.path.exists("sku.db"):
            init_sql(cur)
        await create_session()
    finally:
        con.close()

if __name__=="__main__":
    asyncio.run(main())