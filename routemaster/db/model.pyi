import datetime
from typing import Any, Dict, List, Union, Optional

from sqlalchemy import MetaData

# Imperfect JSON type (see https://github.com/python/typing/issues/182)
_JSON = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]


metadata: MetaData


class Label:
    name: str
    state_machine: str
    metadata: _JSON
    metadata_triggers_processed: bool
    deleted: bool
    updated: datetime.datetime

    history: List['History']

    def __init__(
        self,
        *,
        name: str=...,
        state_machine: str=...,
        metadata: _JSON=...,
        metadata_triggers_processed: bool=...,
        deleted: bool=...,
        updated: datetime.datetime=...,
        history: List['History']=...,
    ) -> None: ...


class History:
    id: int

    label_name: str
    label_state_machine: str
    created: datetime.datetime
    forced: bool

    old_state: Optional[str]
    new_state: Optional[str]

    label: Label

    def __init__(
        self,
        *,
        id: int=...,
        label_name: str=...,
        label_state_machine: str=...,
        created: datetime.datetime=...,
        forced: bool=...,
        old_state: Optional[str]=...,
        new_state: Optional[str]=...,
        label: Label=...,
    ) -> None: ...
