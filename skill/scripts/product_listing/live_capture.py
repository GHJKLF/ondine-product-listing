"""Bridge real fetch_source output to the existing evidence contracts.

Preparation extracts candidates, not approved facts. The assistant completes the
source review before finalization; neither command makes a network or shop write.
"""

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from product_listing.adapters import JsonLdDomAdapter, ShopifyAjaxAdapter
from product_listing.evidence import canonical_json_bytes, model_sha256, sha256_file
from product_listing.models import (
    EvidenceSource, GapSeverity, ReplayResult, SourceAcquisitionGap,
    SourceArtifact, SourceCapture, SourceClassEvidence,
)
from product_listing.reconcile import ReconcileContext, reconcile
from product_listing.validation import validate_source_capture


def evidence_path(root: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise ValueError("evidence paths must be relative to the source bundle")
    root = root.resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError("evidence file missing or outside source bundle: %s" % relative)
    return path


def _verified_file(root: Path, relative: str, digest: str) -> Path:
    path = evidence_path(root, relative)
    if sha256_file(path) != digest:
        raise ValueError("evidence hash mismatch: %s" % relative)
    return path


def prepare_live_capture(report_path: Path, source_root: Path) -> SourceCapture:
    """Produce a schema-complete candidate, retaining unresolved source issues."""
    root = source_root.resolve()
    report_path = report_path.resolve()
    report_relative = str(report_path.relative_to(root))
    report = json.loads(evidence_path(root, report_relative).read_text(encoding="utf-8"))
    if report.get("capture_complete") is not True or report.get("errors"):
        raise ValueError("complete the raw source capture before preparing candidates")
    if report.get("method") not in {
        "SCRAPLING_GET_SAME_COOKIE_SESSION", "HTTP_GET_SAME_COOKIE_SESSION"
    }:
        raise ValueError("unsupported raw capture method; preserve actual acquisition evidence")
    captured_at = datetime.fromisoformat(report["captured_at"])
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("capture time must include its timezone")
    records = report["artifacts"]
    raw = {}
    artifacts = [SourceArtifact(
        artifact_id="capture-report", kind="network_manifest",
        relative_path=report_relative, media_type="application/json",
        sha256=sha256_file(report_path),
    )]
    for role, kind in (("page", "bundle"), ("product", "shopify_ajax"),
                       ("cart_currency", "cart_currency")):
        record = records[role]
        # fetch_source paths are relative to the report, not the run root.
        relative = str(Path(report_relative).parent / record["path"])
        if Path(record["path"]).is_absolute():
            raise ValueError("raw capture artifact path must be relative")
        path = _verified_file(root, relative, record["sha256"])
        raw[role] = path.read_text(encoding="utf-8")
        artifacts.append(SourceArtifact(
            artifact_id=role, kind=kind, relative_path=relative,
            media_type="text/html" if role == "page" else "application/json",
            sha256=record["sha256"],
        ))
    product = json.loads(raw["product"])
    cart = json.loads(raw["cart_currency"])
    currency = cart.get("currency")
    if currency != report.get("observed_cart_currency") or currency != "GBP":
        raise ValueError("UK GBP commerce evidence is unresolved; verify the source market")
    if report.get("requested_market") != "GB":
        raise ValueError("this Ondine live bridge requires a GB capture")
    if not product.get("id") or not product.get("variants"):
        raise ValueError("source product identity or variants are missing")
    page = records["page"]
    final = urlsplit(page["final_url"])
    canonical = urlunsplit((final.scheme, final.netloc, final.path.rstrip("/"), "", ""))
    ajax = ShopifyAjaxAdapter().extract(product, captured_at, "product", currency)
    dom = JsonLdDomAdapter().extract_html(raw["page"], captured_at, "page", page["final_url"])
    gaps = [SourceAcquisitionGap(
        code="LIVE_SOURCE_REVIEW_PENDING", severity=GapSeverity.BLOCKING,
        detail="Assistant must check UK market, visible price/options, all sections and sizing, "
               "source-gallery order and downloaded image hashes against this product. "
               "Complete missing evidence and resolve conflicts before finalizing.",
    )]
    if any(record.get("redirected") or record["requested_url"] != record["final_url"]
           for record in records.values()):
        gaps.append(SourceAcquisitionGap(
            code="LIVE_REDIRECT_REVIEW_PENDING", severity=GapSeverity.BLOCKING,
            detail="Capture contains a redirect; verify the final market and product identity.",
        ))
    context = ReconcileContext(
        requested_url=page["requested_url"], final_url=page["final_url"],
        canonical_url=canonical, captured_at=captured_at, market="GB", currency=currency,
        consumer_retail_source=False,
        source_class_evidence=SourceClassEvidence(
            consumer_retail_source=False, locator="artifact:page",
            rationale="Raw capture only; public retail product identity awaits assistant review.",
        ),
        artifacts=artifacts, expected_section_roles=[], expected_role_absences=[],
        explicit_absences=[], acquisition_gaps=gaps, declared_conflicts=[],
    )
    capture = reconcile(context, [(EvidenceSource.RENDERED_DOM, dom),
                                 (EvidenceSource.SHOPIFY_AJAX, ajax)], [], [])
    capture.locale = report.get("requested_language")
    capture.structured_product_evidence = {"product_id": str(product["id"])}
    # Raw HTTP DOM is not a browser-rendered capture. Do not label it as one.
    capture.same_session_commerce = {
        "method": report["method"], "browser_rendered": False,
        "product_locator": "artifact:product", "currency_locator": "artifact:cart_currency#/currency",
    }
    for fact in capture.facts:
        if fact.source == EvidenceSource.MANIFEST:
            fact.locator = ("artifact:cart_currency#/currency" if fact.field_path == "currency"
                            else "artifact:capture-report#/artifacts/page/final_url")
    capture.media_manifest_evidence = {"content_files": []}
    return capture


def finalize_live_capture(capture_path: Path, source_root: Path) -> ReplayResult:
    """Validate the reviewed capture and real files, then build its pinned envelope."""
    capture = SourceCapture.model_validate_json(capture_path.read_text(encoding="utf-8"))
    seen_ids = set()
    for artifact in capture.artifacts:
        if artifact.artifact_id in seen_ids:
            raise ValueError("duplicate source artifact ID: %s" % artifact.artifact_id)
        seen_ids.add(artifact.artifact_id)
        _verified_file(source_root, artifact.relative_path, artifact.sha256)
    if (capture.same_session_commerce or {}).get("method") in {
        "SCRAPLING_GET_SAME_COOKIE_SESSION", "HTTP_GET_SAME_COOKIE_SESSION"
    }:
        report_artifact = next((item for item in capture.artifacts
                                if item.artifact_id == "capture-report"), None)
        if report_artifact is None:
            raise ValueError("live review must preserve its original capture report")
        original = prepare_live_capture(
            evidence_path(source_root, report_artifact.relative_path), source_root)
        reviewed_conflicts = {item.conflict_id: item for item in capture.conflicts}
        for conflict in original.conflicts:
            reviewed = reviewed_conflicts.get(conflict.conflict_id)
            if reviewed is None or (reviewed.code, reviewed.field_path,
                                    [value.model_dump(mode="json") for value in reviewed.values]) != (
                    conflict.code, conflict.field_path,
                    [value.model_dump(mode="json") for value in conflict.values]):
                raise ValueError("preserve original conflict evidence: %s" % conflict.conflict_id)
            if reviewed.state.value == "RESOLVED" and reviewed.rationale == conflict.rationale:
                raise ValueError("record the evidence and reason resolving conflict: %s" % conflict.conflict_id)
    issues = validate_source_capture(capture)
    if issues:
        raise ValueError("source review is incomplete: " + "; ".join(
            "%s (%s)" % (issue.code, issue.field_path) for issue in issues))
    files = (capture.media_manifest_evidence or {}).get("content_files", [])
    verified_media = set()
    for record in files:
        _verified_file(source_root, record["relative_path"], record["sha256"])
        verified_media.add((record["url"], record["sha256"]))
    for media in capture.rendered_media + capture.structured_media:
        if (media.url, media.content_sha256) not in verified_media:
            raise ValueError("source media lacks a verified local file: %s" % media.media_id)
    return ReplayResult(source_capture=capture, determinism_sha256=model_sha256(capture),
                        valid=True, issues=[])


def write_new_json(path: Path, value) -> None:
    """Never overwrite previous capture evidence or an existing valid envelope."""
    with path.open("xb") as output:
        output.write(canonical_json_bytes(value) + b"\n")
