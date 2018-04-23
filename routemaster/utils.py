"""Shared utilities."""
import contextlib
from typing import Any, Dict, Callable, Iterable, Sequence

StartResponse = Callable[
    [
        str,
        Dict[str, str],
        Any,
    ],
    None,
]

WSGIEnvironment = Dict[str, Any]

WSGICallable = Callable[
    [
        WSGIEnvironment,
        StartResponse,
    ],
    Iterable[bytes],
]


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


def get_path(path: Sequence[str], d: Dict[str, Any]) -> Any:
    """Get the path from a structure of nested dicts."""
    if not len(path):
        # Empty path returns the whole dict, i.e. no _filter_ on the dict
        return d

    component, rest = path[0], path[1:]
    if rest:
        return get_path(rest, d.get(component, {}))
    return d.get(component)


@contextlib.contextmanager
def suppress_exceptions(logger):
    """Catch all exceptions and log to a provided logger."""
    try:
        yield
    except Exception:
        logger.exception("Error suppressed")


def template_url(
    url_template: str,
    state_machine_name: str,
    label: str,
) -> str:
    """
    Templates a URL for an external service.

    Adds the label and state machine to a url that contains placeholders in the
    format `<label>` or '<state_machine>'.
    """
    return url_template.replace(
        '<label>',
        label,
    ).replace(
        '<state_machine>',
        state_machine_name,
    )
