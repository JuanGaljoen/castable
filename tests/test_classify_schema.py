"""RNG-21: structured-output schema stays compilable by the real Messages API.

The real API 400'd, then (once unions were cut) HUNG and timed out, on the
vision schema. Root cause: strict structured output treats every field that has
a default as OPTIONAL, and a schema with many optional fields incurs exponential
compilation cost ("too many parameters with type arrays or anyOf"). Every
existing classify test stubs the client, so the schema was never sent to the
real API and the defect shipped invisibly.

These guards enforce the fix offline, without a key:
  1. EVERY property is required (no optional fields) -- the load-bearing rule.
  2. Union/array params stay within Claude's 16-param cap -- a related shape
     limit; keep numeric dims plain (required `float`), not `float | None`.
Keep RingClassification and RingConfidence free of field defaults.
"""
from ringcad.classify import RingClassification

# Claude's structured-output cap on union/array params. We stay well under it.
UNION_PARAM_LIMIT = 16


def _iter_objects(schema: dict):
    """Yield the root object schema and every object in `$defs`."""
    yield schema
    yield from schema.get("$defs", {}).values()


def _optional_params(schema: dict) -> list[str]:
    """Property names (across root and `$defs`) that are NOT required -- the
    fields whose present/absent combinations blow up compilation."""
    optional = []
    for obj in _iter_objects(schema):
        required = set(obj.get("required", []))
        for name in obj.get("properties", {}):
            if name not in required:
                optional.append(name)
    return optional


def _union_or_array_params(schema: dict) -> int:
    """Count properties that are union-typed (`anyOf`) or array-typed."""
    count = 0
    for obj in _iter_objects(schema):
        for prop in obj.get("properties", {}).values():
            if "anyOf" in prop or prop.get("type") == "array":
                count += 1
    return count


def test_classification_schema_has_no_optional_fields():
    schema = RingClassification.model_json_schema()
    optional = _optional_params(schema)
    assert optional == [], (
        f"RingClassification schema has optional fields {optional}; strict "
        f"structured output hangs when a schema has many optional fields. "
        f"Make every field required (no default)."
    )


def test_classification_schema_within_union_limit():
    schema = RingClassification.model_json_schema()
    n = _union_or_array_params(schema)
    assert n <= UNION_PARAM_LIMIT, (
        f"RingClassification has {n} union/array params (limit "
        f"{UNION_PARAM_LIMIT}); the real API rejects a schema above it. Prefer "
        f"required `float` numeric fields over `float | None`."
    )
