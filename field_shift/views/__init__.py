"""Views of the contracts: a graph of every link and a tree with references inlined."""

from ..contracts import load_schemas
from .graph import build_graph, build_tree


def contract_graph() -> dict:
    return build_graph(load_schemas())


def contract_tree() -> dict:
    schemas = load_schemas()
    return build_tree(schemas, build_graph(schemas))


__all__ = ["build_graph", "build_tree", "contract_graph", "contract_tree"]
