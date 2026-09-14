# Release notes

## 2026-09-13 — initial private distribution

- Packaged the canonical Ondine product-listing skill, its profiles, schemas, signed offline fixtures, maintenance record, and seven gallery slots `01`, `01b`, `02`–`06`.
- Added the minimal local gallery handoff compiler: its handoff script, three source modules, documentation, and two historical test fixtures. The Shopify app, app configuration, and dependency tree are excluded.
- Preserved all signed contract files unchanged and used the repository root plus `.claude/skills/product-listing` layout so their validation remains active.
- Documented manual update flow only: approved private-repository push, Haider notification, and pull before the next run. No automatic update mechanism is included.

Known setup gaps: Haider's client and connector are unconfirmed; authenticated source extraction, image generation, connector access, FactPacket registration, and a real product trial remain pending.

Historical issue, resolved by the repair below: the canonical `pack-manifest.json` has seven template SHA-256 mismatches against the supplied slot files. The same mismatches exist in the source skill. This package preserves both sides unchanged; no replacement hashes or approval records were made.

### Gallery verification repair

Refreshed template, human-note, combined-template and manifest checksums after the documented runtime metadata change. Added an offline regression test covering all referenced gallery files. The pre-repair manifest is preserved in the skill archives. No image template or historical composition approval was changed.

## 2026-09-14 — GitHub handoff

Included the approved complete workflow image in the README, clarified that the product link is the only required input, and added repository download/manual-update instructions. Verified 64 listing tests plus 15 gallery tests before publication. Live operator setup and the first supervised product trial remain separate.
