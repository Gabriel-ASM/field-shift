"""MongoDB access: collections validated by the v2 contracts."""

from .collections import COLLECTIONS, CollectionSpec, validator_for
from .store import InvalidDocument, connect, ensure_collections, find_one, list_documents, sync_contracts, upsert

__all__ = [
    "COLLECTIONS", "CollectionSpec", "InvalidDocument", "connect", "ensure_collections",
    "find_one", "list_documents", "sync_contracts", "upsert", "validator_for",
]
