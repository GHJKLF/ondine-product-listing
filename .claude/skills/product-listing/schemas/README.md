# Phase 1 source-capture contracts

`source-capture.schema.json` is generated from the strict Pydantic
`SourceCapture` model by `scripts/export_source_capture_schema.py`. Regenerate
and rerun the offline suite whenever the typed model changes.

## Frozen fixture consumer interface

The only bundle entrypoint is `bundle.json`. Its sibling
`bundle-files.sha256` must sign `bundle.json` and every artifact consumed by
the replay. Paths must be relative to the bundle directory and may not escape
it.

The Phase 1 bundle manifest uses schema `source-capture-fixture-v1` and a
`files` object containing exactly these roles:

- `structured_product`
- `sections`
- `size_guide`
- `media`
- `evidence`

Same-session Shopify Ajax evidence may use the legacy
`capture.commerce_json.path` form or the locked positive-denominator form
`capture.same_session_commerce_json.{product_path,cart_currency_path,currency}`.
Every referenced artifact must be present in the signed hash index, and the
cart-currency subset is reconciled as source commerce evidence rather than
target availability.
Optional frozen JSON-LD uses `capture.json_ld.path` under the same rule.
Rendered HTML is required at `rendered.sanitized.html`; all signed artifacts are
retained in `SourceCapture.artifacts` even when a blocker prevents a positive
denominator. When a capture record also declares an artifact SHA-256, it must
equal the verified hash-index value.

Replay never rewrites, upgrades, or repairs a fixture. An unknown artifact,
missing signature, digest mismatch, unsafe path, unsupported schema, or malformed
payload stops before reconciliation. Blocking conflicts and acquisition gaps
remain separate, and explicit absences never satisfy a conflict.

The same `bundle.json` interface is used for blocked and positive denominators.
`valid=true` is computed only after artifact verification, reconciliation and
critical-stop validation; it is never inferred from a fixture directory name or
oracle status.
