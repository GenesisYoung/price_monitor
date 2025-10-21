import os
from playwright.async_api import Page,Union,ElementHandle

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

      
