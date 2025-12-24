import orjson
from typing import Any
from litestar.response import Response


class ORJSONResponse(Response):
    """
    High-performance JSON response using orjson.
    """

    def render(self, content: Any) -> bytes:
        return orjson.dumps(content)
