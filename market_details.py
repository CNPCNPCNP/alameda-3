from dataclasses import dataclass, field

@dataclass
class MarketDetails:
    market_name: str
    market_id: str
    yes_token: str
    no_token: str
    neg_risk: bool
    yes_price: float = 0.
    no_price: float = 0.
    yes_sent_orders: dict = field(default_factory=dict)
    no_sent_orders: dict = field(default_factory=dict)
    yes_position: float = 0
    no_position: float = 0
    theoval: float = 0
    