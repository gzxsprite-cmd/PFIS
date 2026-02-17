"""Utility helpers for shared application concerns."""

from urllib.parse import quote


def encode_header_value(value: str) -> str:
    """Percent-encode a header value so it can carry non-ASCII text.

    Starlette (and thus FastAPI) restricts header values to latin-1 encodable
    strings. To safely transport localized messages (e.g., Chinese toast text)
    we percent-encode them and decode on the client side.
    """

    return quote(value or "", safe="")

