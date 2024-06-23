from dataclasses import dataclass, field

@dataclass
class Order:
    order_id: str
    token_id: str
    side: str
    size: float
    price: float
    theoval: float    
