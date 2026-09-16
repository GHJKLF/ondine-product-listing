"""RFC 8785 JSON Canonicalization Scheme for Phase 2 evidence.

Phase 1 deliberately keeps its historical serializer and locked hashes.  This
module is the single canonical JSON implementation for Phase 2 projection,
policy, copy-guard, and ListingPlan hash lanes.
"""

from decimal import Decimal
import json
import math
from typing import Any, List, Set


MAX_SAFE_INTEGER = (1 << 53) - 1


class CanonicalizationError(ValueError):
    """Raised when a value cannot be represented as RFC 8785/I-JSON."""


def _validate_unicode(value: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise CanonicalizationError("lone Unicode surrogate is not valid I-JSON")


def _serialize_string(value: str) -> str:
    _validate_unicode(value)
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _serialize_float(value: float) -> str:
    """Serialize one IEEE-754 value using ECMAScript NumberToString rules.

    Python and ECMAScript use the same shortest round-tripping significand.
    Their presentation thresholds differ, so the shortest Python significand
    is placed according to ECMAScript's fixed/scientific boundaries.
    """

    if not math.isfinite(value):
        raise CanonicalizationError("non-finite JSON number")
    if value == 0.0:
        return "0"

    sign = "-" if value < 0 else ""
    decimal_value = Decimal(repr(abs(value))).normalize()
    decimal_tuple = decimal_value.as_tuple()
    digits = "".join(str(digit) for digit in decimal_tuple.digits)
    decimal_point = len(digits) + decimal_tuple.exponent

    if 0 < decimal_point <= 21:
        if len(digits) <= decimal_point:
            encoded = digits + ("0" * (decimal_point - len(digits)))
        else:
            encoded = digits[:decimal_point] + "." + digits[decimal_point:]
    elif -6 < decimal_point <= 0:
        encoded = "0." + ("0" * -decimal_point) + digits
    else:
        exponent = decimal_point - 1
        mantissa = digits[0]
        if len(digits) > 1:
            mantissa += "." + digits[1:]
        encoded = mantissa + "e" + ("+" if exponent >= 0 else "") + str(exponent)
    return sign + encoded


def _utf16_sort_key(value: str) -> bytes:
    _validate_unicode(value)
    return value.encode("utf-16-be")


def _serialize(value: Any, active_containers: Set[int]) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            raise CanonicalizationError("integer exceeds the I-JSON safe domain")
        return str(value)
    if isinstance(value, float):
        return _serialize_float(value)
    if isinstance(value, str):
        return _serialize_string(value)

    if isinstance(value, (list, tuple)):
        identity = id(value)
        if identity in active_containers:
            raise CanonicalizationError("cyclic JSON value")
        active_containers.add(identity)
        try:
            return "[" + ",".join(
                _serialize(item, active_containers) for item in value
            ) + "]"
        finally:
            active_containers.remove(identity)

    if isinstance(value, dict):
        identity = id(value)
        if identity in active_containers:
            raise CanonicalizationError("cyclic JSON value")
        if any(not isinstance(key, str) for key in value):
            raise CanonicalizationError("JSON object keys must be strings")
        active_containers.add(identity)
        try:
            keys: List[str] = sorted(value, key=_utf16_sort_key)
            return "{" + ",".join(
                _serialize_string(key) + ":" + _serialize(value[key], active_containers)
                for key in keys
            ) + "}"
        finally:
            active_containers.remove(identity)

    raise CanonicalizationError(
        "unsupported JSON value type: %s" % type(value).__name__
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return UTF-8 RFC 8785 canonical JSON bytes for a JSON-compatible value."""

    return _serialize(value, set()).encode("utf-8")
