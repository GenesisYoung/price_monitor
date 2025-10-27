from tmall import *
from database.db import *

async def main():
    # await create_session()
    try:
        con = connect_db()
        cur = con.cursor()
        if not os.path.exists("sql/sku.db"):
            init_sql(cur)
        #   淘宝平台检索
        await create_tmall_session()
    finally:
        con.close()

if __name__=="__main__":
    asyncio.run(main())