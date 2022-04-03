"""Shared text utilities."""
from typing import Iterable


def join_comma_or(items: Iterable[str]) -> str:
    """Join strings with commas and 'or'."""
    if not items:
        raise ValueError("No items to join")

    *rest, last = items

    if not rest:
        return last

    return f"{', '.join(rest)} or {last}"
