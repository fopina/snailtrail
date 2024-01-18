from jinja2 import Environment, PackageLoader, select_autoescape

from snail.gqlclient import types as gql_types

env = Environment(loader=PackageLoader("cli"), autoescape=select_autoescape())


def render_cheap_soon_join(snail: gql_types.Snail, race: gql_types.Race):
    template = env.get_template("cheap_soon_join.html")
    return template.render(snail=snail, race=race)
