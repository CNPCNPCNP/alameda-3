class GetMarketId():
    def __init__(self, client, first_slug, second_slug, third_slug):
        self.client = client
        self.first_slug = first_slug
        self.second_slug = second_slug
        self.third_slug = third_slug

    def get_market_ids(self):
        next_cursor = "ODcwMA=="
        while next_cursor != "LTE=":
            markets = self.client.get_markets(next_cursor)
            data = markets["data"]
            ids = [None,None,None]
            for market in data:
                if market["market_slug"] == self.first_slug:
                    ids[0] = market["condition_id"]
                if market["market_slug"] == self.second_slug:
                    ids[1] = market["condition_id"]
                if market["market_slug"] == self.third_slug:
                    ids[2] = market["condition_id"]
            next_cursor = markets["next_cursor"]
        return ids