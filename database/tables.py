class SKUItem:
    def __init__(self,seller:str,seller_link:str,title:str,price:float,discount_price:float=0,sku_id:str=None,is_legal:int=-1,big_pic:str=None,great_discount:int=0,platform:str="tmall"):
        self.seller=seller
        self.seller_link=seller_link
        self.title=title
        # 商品价格，如果可以使用券则是券后实际价格
        self.price=price
        # 仅在有券时有值，有券时表示未用券前的价格
        self.discount_price=discount_price
        # 0表示低于标准;1表示正常价格
        self.is_legal=is_legal
        self.sku_id=sku_id
        self.big_pic=big_pic
        self.great_discount=great_discount
        self.platform=platform
class SKUStandard:
    def __init__(self,sku_id:str,sku:str,sku_price:float,discount_price:float,great_discount:float=0):
        self.sku_id=sku_id
        self.sku=sku
        self.sku_price=sku_price
        self.discount_price=discount_price
        self.great_discount=great_discount