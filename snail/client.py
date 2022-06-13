from . import gqlclient, web3client


class Client:
    def __init__(
        self,
        http_token=None,
        proxy=None,
        wallet=None,
        private_key=None,
        web3_provider=None,
        web3_provider_class=None,
    ):
        self.gql = gqlclient.Client(http_token=http_token, proxy=proxy)
        if wallet and private_key and web3_provider:
            self.web3 = web3client.Client(wallet, private_key, web3_provider, web3_provider_class=web3_provider_class)

    def iterate_all_snails_marketplace(self, filters={}):
        c = 0
        while True:
            snails = self.gql.get_all_snails_marketplace(offset=c, filters=filters)
            if not snails["snails"]:
                break
            yield from snails["snails"]
            c += len(snails["snails"])

    def iterate_all_snails(self, filters={}):
        c = 0
        while True:
            snails = self.gql.get_all_snails(offset=c, filters=filters)
            if not snails["snails"]:
                break
            yield from snails["snails"]
            c += len(snails["snails"])
            print(snails['count'])
            print(c)

    def iterate_mission_races(self, filters={}):
        c = 0
        while True:
            snails = self.gql.get_mission_races(offset=c, filters=filters)
            if not snails["all"]:
                break
            yield from snails["all"]
            c += len(snails["all"])

    def iterate_my_snails_for_missions(self, owner):
        c = 0
        while True:
            snails = self.gql.get_my_snails_for_missions(owner, offset=c)
            if not snails["snails"]:
                break
            yield from snails["snails"]
            c += len(snails["snails"])

    def join_mission_races(self, snail_id: int, race_id: int, address: str):
        """join mission race - signature is generated by `sign_daily_mission`"""
        signature = self.web3.sign_daily_mission(address, snail_id, race_id)
        return self.gql.join_mission_races(snail_id, race_id, address, signature)
