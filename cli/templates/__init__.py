from jinja2 import Environment, PackageLoader, select_autoescape

from snail.gqlclient import types as gql_types
from snail.web3client import web3_types

from .. import utils

env = Environment(loader=PackageLoader("cli"), autoescape=select_autoescape())


def render_cheap_soon_join(snail: gql_types.Snail, race: gql_types.Race):
    template = env.get_template("cheap_soon_join.html")
    return template.render(snail=snail, race=race)


def render_mission_joined(
    snail: gql_types.Snail, tx: web3_types.TxReceipt = None, cheap: bool = False, telegram: bool = False
):
    template = env.get_template("mission_joined.html")
    return template.render(snail=snail, tx=tx, cheap=cheap, telegram=telegram, tx_fee=utils.tx_fee)
