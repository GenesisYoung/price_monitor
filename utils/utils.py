import os,re
import pandas as pd
from playwright.async_api import Page,Union,ElementHandle

from utils.price_standard import PriceStandard


class Util:
    def __init__(self,page:Page):
        self.page=page
    # Get env by name
    def get_env(self,name:str)->str:
        return os.getenv(name)
    async def select_ele(self,selector:str)->Union[ElementHandle, None]:
        try:
            await self.page.wait_for_selector(selector=selector,state='visible',strict=True)
            return await self.page.query_selector(selector=selector)
        except:
            print("ERROR:>>>Error when select element by selector<<<ERROR")
    async def select_eles(self,selector:str)->list[ElementHandle]:
        try:
            await self.page.wait_for_selector(selector=selector,state="visible")
            return await self.page.query_selector_all(selector=selector)
        except:
            print("ERROR:>>>Error when select multiple elements by selector<<<ERROR")
    def parse_excel(self,excel:str):
        excel=pd.read_excel("./data/green_stone.xlsx")
        print(excel)
    def check_price(self,sku:str,price:float,is_promote:int,keyword:str)-> bool | None:
        # >>>>青石系列价格判定<<<<
        green_stone=price_of_green_stone()
        # 小火锅
        hot_pot=green_stone["火锅"]
        end = sku.index("】") + 3
        key=sku[0:end]
        if hot_pot[key] != None:
            model=hot_pot[key]
            regular_price=model.price
            prompted_price=model.promote_price
            if  is_promote==0:
                if regular_price > price:
                    return False
                else:
                    return True
            else:
                if prompted_price > price:
                    return False
                else:
                    return True
        else:
            print(">>>>>>>>SKU naming error!!!<<<<<<<<")
            return None
def price_of_green_stone():
    df=pd.read_excel("./data/green_stone.xlsx",sheet_name=0,
                     skiprows=3,
                     header=0,
                     usecols=[4,5,8,9]
                     )
    hot_pot={}
    for value in df.values[1:29]:
        end=value[1].index("】")+3
        hot_pot[value[1][0:end]]=PriceStandard(value)
    sandwich_machine={"三明治机":df.values[0][0]}
    other={}
    for value in df.values[29:46]:
        other[value[0]] = PriceStandard(value)
    green_stone={"火锅":hot_pot,"三明治机":sandwich_machine}
    for key in other:
        green_stone[key]=other[key]
    return green_stone