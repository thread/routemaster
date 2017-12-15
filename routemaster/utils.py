"""Shared utilities."""
from typing import Any, Dict, Sequence


def dict_merge(d1, d2):
    """
    Recursively merge two dicts to create a new dict.

    Does not modify either dict. The second dict's values will take priority
    over the first's.
    """
    new = dict(d1)
    for k, v in d2.items():
        if (
            k in new and
            isinstance(new[k], dict) and
            isinstance(d2[k], dict)
        ):
            new[k] = dict_merge(new[k], d2[k])
        else:
            new[k] = d2[k]
    return new


def is_list_prefix(l1, l2):
    """
    Given two lists, determine if the first is a prefix of the second.
    """
    if len(l1) > len(l2):
        return False

    for idx, elem in enumerate(l1):
        if l2[idx] != elem:
            return False

    return True


def get_path(path: Sequence[str], d: Dict[str, Any]) -> Any:
    """Get the path from the dict."""
    component, rest = path[0], path[1:]
    if rest:
        return get_path(rest, d.get(component, {}))
    return d.get(component)
