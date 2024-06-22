from dataclasses import dataclass

@dataclass
class Position:
    market_id: str
    yes_token: str
    no_token: str
    neg_risk: bool
    yes: int = 0
    no: int = 0