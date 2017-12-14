"""Shared utilities."""


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
