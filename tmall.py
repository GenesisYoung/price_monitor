import asyncio
import random
from playwright.async_api import async_playwright,TimeoutError
from utils import *
from tables import *
from db import *

# 创建一个Session
async def create_session():
    async with async_playwright() as p:
        if os.path.exists("auth.json"):
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(storage_state="auth.json")
            page = await context.new_page()
            util = Util(page=page)
            HOME_PAGE = util.get_env("HOME_PAGE")
            await page.goto(HOME_PAGE)
            await page.wait_for_load_state("domcontentloaded")

            KEYWORDS = os.getenv("PRODUCT_KEYWORDS").split(',')
            for keyword in KEYWORDS:
                target = "https://s.taobao.com/search?q=" + keyword
                await page.goto(target)
                await page.wait_for_load_state("domcontentloaded")
                entries = await fetch_entries(page)
                await change_pages(5,current=0, entries=entries, page=page)
        else:
            browser=await p.chromium.launch(headless=False)
            page=await browser.new_page()
            util=Util(page=page)
            LOGIN_PATH=util.get_env("LOGIN_PATH")
            await page.goto(LOGIN_PATH)
            await asyncio.sleep(15)
            await page.wait_for_load_state("domcontentloaded")
            await page.context.storage_state(path="auth.json")
            await page.close()
            await create_session()
async  def change_pages(entry_size,current,entries,page):
    for entry in entries:
        await enter_detail(entry, page)
    await asyncio.sleep(10)
    current += current
    if current <= entry_size:
        await change_pages(entry_size,current,entries,page)

# 抓取当前页所有商品的入口
async def fetch_entries(page:Page):
    await page.wait_for_selector(".imageSwitch--fJ9SrtEb",state="attached")
    entries = await page.query_selector_all(".imageSwitch--fJ9SrtEb")
    return entries
# 进入商品详情页
async def enter_detail(ele:ElementHandle,p:Page):
    DETAIL_WAIT = "domcontentloaded"
    popup_ctx = p.expect_popup()
    nav_ctx = p.expect_navigation(wait_until=DETAIL_WAIT)
    detail_page = None
    opened_new_tab = False
    panel=await p.query_selector("#tbpcDetail_SkuPanelFoot")

    try:
        async with p.expect_popup() as popup_info:
            await ele.click(force=True)
        detail_page = await popup_info.value
        opened_new_tab = True
    except TimeoutError:
        # 没有新页就等同页导航
        try:
            await nav_ctx
            detail_page = p
            opened_new_tab = False
        except TimeoutError:
            # 有些站点是 SPA，没有真正的导航，只是 DOM 变化
            detail_page = p
            await p.wait_for_load_state(DETAIL_WAIT)
    try:
        await detail_page.wait_for_load_state(state="domcontentloaded")
        await detail_page.wait_for_selector(".valueItem--smR4pNt4",state="attached")
        sku_list=await detail_page.query_selector_all(".valueItem--smR4pNt4")
        idx=0
        for sku in sku_list:
            await sku.wait_for_selector("span")
            span=await sku.query_selector("span")
            print("CURRENT SKU>>>"+await span.text_content()+"<<<<")
            if idx>0:
                await span.scroll_into_view_if_needed()
                await p.wait_for_load_state("networkidle")
                await span.click()
            idx+=1
            await detail_page.wait_for_selector(".detailWrap--svoEjPUO")
            link_ele=await detail_page.query_selector(".detailWrap--svoEjPUO")
            shop_link=await link_ele.get_attribute("href")
            seller_name=await detail_page.query_selector(".shopName--cSjM9uKk")
            seller=await seller_name.text_content()
            await detail_page.wait_for_selector(".text--jyiUrkMu")
            price_ele=await detail_page.query_selector(".text--jyiUrkMu")
            price=await price_ele.text_content()
            big_pic=await detail_page.query_selector(".mainPicWrap--Ns5WQiHr")
            big_pic_img=await big_pic.query_selector("img")
            big_pic_url=await big_pic_img.get_attribute("src")
            await record_sku(sku=sku,seller=seller,link="https:"+shop_link,price=price,big_pic=+big_pic_url)
            await asyncio.sleep(random.randint(5, 10))
        await asyncio.sleep(random.randint(10,30))
        if opened_new_tab:
            # 新标签页：直接关掉它，原来的 page 还在列表页
            await detail_page.close()
            await p.bring_to_front()
            # 保险起见，等一等列表 DOM
            await p.wait_for_load_state("domcontentloaded")
        else:
            # 同页跳转：用 go_back 返回
            # 注意：有些站点用 pushState，go_back 也能工作，但要等 DOM 状态
            await p.go_back(wait_until=DETAIL_WAIT)
    except Exception as e:
        print(e)
# 记录抓取到的SKU信息
async def record_sku(sku:ElementHandle,seller:str,link:str,price:float,sub_price:float=0,big_pic=None):
    await sku.wait_for_selector("span")
    sku_ele=await sku.query_selector("span")
    sku_title=await sku_ele.get_attribute("title")
    sku_id=await sku.get_attribute("data-vid"),
    sku_record=SKUItem(
        sku_id=sku_id[0],
        title=sku_title,
        seller=seller,
        seller_link=link,
        price=price,
        sub_price=sub_price,
        big_pic=big_pic
        )
    if check_price(sku=sku_title,price=price):
        sku_record.is_legal=1
    else:
        sku_record.is_legal=0
    try:
        con = sqlite3.connect("sku.db")
        cur = con.cursor()
        insert_data = (
            sku_record.seller,
            sku_record.seller_link,
            sku_record.title,
            float(sku_record.price),
            float(sku_record.sub_price),
            int(sku_record.is_legal),
            sku_record.sku_id[0],
            sku_record.big_pic
        )
        cur.execute("""
            INSERT INTO sku_item 
            (seller, seller_link, title, price, sub_price, is_legal, sku_id,big_pic)
            VALUES (?, ?, ?, ?, ?, ?, ?,?)
        """, insert_data)

        con.commit()
    except sqlite3.Error as e:
        print("数据库插入失败:", e)
    finally:
        if con:
            con.close()
    
def check_price(sku:str,price:float)->bool:
    con=connect_db()
    cursor=con.cursor()
    sel=cursor.execute("SELECT * FROM sku_standard WHERE sku = ?", (sku,))
    standard=sel.fetchone()
    if not standard:
        print(f"[WARN] SKU {sku} not found in standard table.")
        return False  # 或者 raise Exception()
    standard_price=standard[2]
    standard_prompt_price=standard[3]
    if float(price)<float(standard_price) and float(price)<float(standard_prompt_price):
        return False
    else:
        return True
    