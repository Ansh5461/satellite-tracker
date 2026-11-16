"""orjson helpers — serialize once, fan-out many."""

from __future__ import annotations

from typing import Any

import orjson
from pydantic import BaseModel


def dumps(obj: Any) -> bytes:
    if isinstance(obj, BaseModel):
        return obj.model_dump_json().encode("utf-8")
    return orjson.dumps(obj, option=orjson.OPT_SERIALIZE_NUMPY)


def loads(data: bytes | str) -> Any:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return orjson.loads(data)
