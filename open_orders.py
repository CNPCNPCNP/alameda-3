from dataclasses import dataclass

@dataclass
class OpenOrders:
    yes_price: float = 0.
    no_price: float = 0.
    yes_sent_vol: int = 0
    no_sent_vol: int = 0
    yes_confirmed_vol: int = 0
    no_confirmed_vol: int = 0

    assert yes_price + no_price < 1