from dataclasses import dataclass

@dataclass
class Order:
    order_id: str
    token_id: str
    side: str
    size: float
    price: float
    theoval: float    

    def __post__init__(self):
        assert 0 < self.price < 1
        assert 0 < self.theoval < 1
        assert self.side == "YES" or self.side == "NO"