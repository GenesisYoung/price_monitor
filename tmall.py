import asyncio
import random
from playwright.async_api import async_playwright,TimeoutError
import os, re, sqlite3, asyncio, random
from typing import Optional, Tuple
from playwright.async_api import async_playwright, TimeoutError, Page, ElementHandle
from utils import  Util
from tables import SKUItem
from db import connect_db

def clean_price(raw: str) -> float:
    """把 '￥1,234.56 - ￥1,999' / '1,288' 等清洗成 float，下取区间最低价"""
    if not raw:
        raise ValueError("empty price text")
    text = raw.strip()
    # 取区间最低
    part = text.split('-', 1)[0]
    # 去货币符号、逗号、空格
    part = re.sub(r'[^\d\.]', '', part)
    if part.count('.') > 1:
        # 极端脏数据，保底拿第一段
        part = part.split('.', 1)[0]
    return float(part)

# === 登录/入口 ===
async def create_tmall_session():
    from utils import Util  # 你原有的工具
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        if os.path.exists("auth.json"):
            context = await browser.new_context(storage_state="auth.json")
            page = await context.new_page()
            util = Util(page=page)
            home_page = util.get_env("HOME_PAGE")
            await page.goto(home_page)
            await page.wait_for_load_state("domcontentloaded")
            keywords = os.getenv("PRODUCT_KEYWORDS", "").split(",")
            for kw in filter(None, (k.strip() for k in keywords)):
                await change_pages(1, page, kw)
        else:
            page = await browser.new_page()
            util = Util(page=page)
            login_path = util.get_env("LOGIN_PATH")
            await page.goto(login_path)
            # 给手动登录留时间
            await asyncio.sleep(15)
            await page.wait_for_load_state("domcontentloaded")
            await page.context.storage_state(path="auth.json")
            await page.close()
            # 递归再进一次
            await create_tmall_session()

# === 翻页/列表抓取 ===
async def change_pages(current: int, page: Page, keyword: str, max_pages: int = 5):
    target = f"https://s.taobao.com/search?page={current}&q={keyword}"
    await page.goto(target)
    await page.wait_for_load_state("domcontentloaded")

    entries = await fetch_entries(page)
    for entry in entries:
        try:
            desc_ele=await entry.query_selector(".title--qJ7Xg_90")
            desc = await desc_ele.get_attribute("title")
            if desc.find("ERNTE") > 0 and desc.find("昂特") > 0:
                await enter_detail(entry, page)  # 进入详情→写库都在里面做
            await asyncio.sleep(random.randint(5, 10))
        except Exception as e:
            print(f"[WARN] entry failed: {e}")

    if current < max_pages:
        await asyncio.sleep(random.randint(10, 30))
        await change_pages(current + 1, page, keyword, max_pages)

# === 抓取当前页所有商品卡片 ===
async def fetch_entries(page: Page):
    await page.wait_for_selector(".mainPicAndDesc--Q5PYrWux", state="attached")
    return await page.query_selector_all(".mainPicAndDesc--Q5PYrWux")
# === 进入详情页（新标签/同页都兜底），抓数并写库 ===
async def enter_detail(card: ElementHandle, list_page: Page):
    DETAIL_WAIT = "domcontentloaded"
    detail_page: Optional[Page] = None
    opened_new_tab = False

    # 尝试新标签
    try:
        async with list_page.expect_popup() as pop:
            await card.click(force=True)
        detail_page = await pop.value
        opened_new_tab = True
    except TimeoutError:
        # 回退到同页导航
        try:
            async with list_page.expect_navigation(wait_until=DETAIL_WAIT):
                await card.click(force=True)
            detail_page = list_page
            opened_new_tab = False
        except TimeoutError:
            print("[WARN] click did not open detail")
            return

    try:
        # 等详情 DOM
        await detail_page.wait_for_load_state(DETAIL_WAIT)

        seller_ele = await detail_page.query_selector(".shopName--cSjM9uKk")  # 示例
        seller = (await seller_ele.text_content()).strip() if seller_ele else ""
        title_ele=await detail_page.query_selector(".mainTitle--R75fTcZL")
        title=(await title_ele.text_content()).strip() if title_ele else ""
        if seller in ["ernte美其特专卖店","ERNTE厨电旗舰店","全球潮流正品店"]:
            # 关闭新开的 tab；同页就不要关
            if opened_new_tab and detail_page and not detail_page.is_closed():
                await detail_page.close()
                return
            # 回到列表页
            if not opened_new_tab:
                await list_page.go_back(wait_until=DETAIL_WAIT)
                return
        sku_list=await detail_page.query_selector_all(".valueItem--smR4pNt4")
        sku_id=None
        for sku in sku_list:
            sku_id=await sku.get_attribute("data-vid")
            await sku.click()
            # 价格：两种选择器择一
            price_text = ""
            is_promote=1 # 0-无促销 1-促销
            try:
                await detail_page.wait_for_selector(".subPrice--KfQ0yn4v",timeout=5000,state="attached")
                await detail_page.query_selector(".subPrice--KfQ0yn4v")
            except TimeoutError:
                is_promote=0
            discount_price=0
            for cls in [".text--jyiUrkMu", ".text--LP7Wf49z"]:
                try:
                    await detail_page.wait_for_selector(cls, state="attached",timeout=5000)
                    if (cls==".text--LP7Wf49z" and is_promote==1):
                        prices=await detail_page.query_selector_all(cls)
                        price_text =await prices[0].text_content()
                        discount_price=await prices[2].text_content()
                    else:
                        price_text = await (await detail_page.query_selector(cls)).text_content()
                    break
                except TimeoutError:
                    continue
            if not price_text:
                raise RuntimeError("price selector not found")

            price = clean_price(price_text)

            # 大图
            big_pic = await detail_page.query_selector(".mainPicWrap--Ns5WQiHr img")
            big_pic_url = await big_pic.get_attribute("src") if big_pic else ""

            # 链接（同页就取当前，弹新页就取新页）
            item_link = detail_page.url

            # —— 写库 —— #
            await record_sku(
                sku=title,  # 建议用真实 sku_id
                seller=seller,
                sku_id=sku_id,
                link=item_link,
                price=price,
                big_pic=big_pic_url,
                is_prompt=is_promote,
                platform="天猫",
                great_discount=0,
                discount_price=discount_price  # 如有促销价/原价，请分字段
            )
            await asyncio.sleep(random.randint(5, 10))

    finally:
        # 关闭新开的 tab；同页就不要关
        if opened_new_tab and detail_page and not detail_page.is_closed():
            await detail_page.close()
        # 回到列表页
        if not opened_new_tab:
            await list_page.go_back(wait_until=DETAIL_WAIT)
# 记录抓取到的SKU信息
# === 写库 ===
async def record_sku(
    sku: str,
    seller: str,
    link: str,
    price: float,
    big_pic: str,
    is_prompt: int,
    platform: str,
    great_discount: int,
    discount_price: float,
    sku_id: str,
):
    from db import connect_db  # 你自己的封装
    con = None
    try:
        con = connect_db()
        cur = con.cursor()
        insert_data = (
            seller,
            link,
            sku,
            float(price),
            float(discount_price),
            int(1),           # is_legal: 先默认 1，或调用 check_price 决定
            sku_id,              # sku_id：不要再用 sku_id[0]，存完整
            big_pic,
            int(great_discount),
            platform
        )
        cur.execute("""
            INSERT INTO sku_item
            (seller, seller_link, title, price, discount_price, is_legal, sku_id, big_pic, great_discount, platform)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, insert_data)
        con.commit()
    except sqlite3.Error as e:
        print("数据库插入失败:", e)
    finally:
        if con:
            con.close()
    
# def check_price(sku:str,price:float)->bool:

    