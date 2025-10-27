class PriceStandard:
    def __init__(self,data:list[str]):
        self.name=data[0]
        if data[1]!='nan':
            self.sku=data[1]
        else:
            self.sku=data[0]
        self.price=data[2]
        self.promote_price=data[3]