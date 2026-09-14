"""Deterministic, offline originality recomputation for ListingPlan validation."""

import hashlib
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit, urlunsplit

from product_listing.listing_plan_canonical_json import canonical_json_bytes
from product_listing.models import SourceCapture


ALGORITHM_ID = "ondine_copy_guard_v1"
NORMALIZATION_VERSION = "ondine_copy_guard_normalization_v1"
APPROVED_EXEMPTION_RULES = {
    "EXACT_CAPTURED_MATERIAL_NAME",
    "EXACT_CAPTURED_COMPOSITION_VALUE",
    "EXACT_CAPTURED_MEASUREMENT_VALUE",
}
BANNED_TERMS = {"premium", "exclusive", "luxury"}
URGENCY_PATTERNS = (
    r"\bhurry\b",
    r"\blimited time\b",
    r"\blast chance\b",
    r"\bends soon\b",
    r"\bact now\b",
    r"\bselling fast\b",
    r"\bonly\s+\d+\s+left\b",
)
MEDICAL_PATTERNS = (
    r"\bcures?\b",
    r"\btreats?\b",
    r"\bheals?\b",
    r"\bdiagnos(?:e|es|is|tic)\b",
    r"\bmedical\b",
    r"\btherapeutic\b",
)
SECONDARY_CTA_PATTERNS = (
    r"\bshop now\b",
    r"\bbuy now\b",
    r"\border now\b",
    r"\bget yours\b",
    r"\blearn more\b",
    r"\bdiscover more\b",
    r"\badd to (?:bag|cart)\b",
)


class CopyGuardEvidenceError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalize_text(value: str) -> Tuple[str, List[str]]:
    normalized = unicodedata.normalize("NFKD", value).casefold().replace("&", " and ")
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
        and unicodedata.category(character) != "Cf"
    )
    tokens = re.findall(r"[a-z0-9]+", normalized)
    return " ".join(tokens), tokens


def _record(path: str, value: Any) -> Optional[Dict[str, str]]:
    if not isinstance(value, str):
        raise CopyGuardEvidenceError("copy-guard field is not text: %s" % path)
    normalized, _ = normalize_text(value)
    if not normalized:
        return None
    return {"path": path, "normalized": normalized}


def _safe_artifact_path(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve()
    candidate = (resolved_root / relative_path).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise CopyGuardEvidenceError("source artifact escapes bundle root") from exc
    if not candidate.is_file():
        raise CopyGuardEvidenceError("source artifact is missing: %s" % relative_path)
    return candidate


def _normalized_url(value: str) -> str:
    if value.startswith("//"):
        value = "https:" + value
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    netloc = host
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc = "%s:%s" % (host, port)
    return urlunsplit((scheme, netloc, parsed.path, parsed.query, ""))


class _ImageAltParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: List[Tuple[str, str]] = []
        self.links: List[Optional[str]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        values = {key.lower(): value for key, value in attrs}
        if tag.lower() == "a":
            self.links.append(values.get("href"))
        if tag.lower() != "img":
            return
        src = values.get("src")
        alt = values.get("alt")
        if src is not None and alt is not None:
            self.images.append((_normalized_url(src), alt))
        if alt is not None and self.links:
            href = self.links[-1]
            if href and re.search(r"\.(?:jpe?g|png|webp|avif)$", urlsplit(href).path, re.I):
                self.images.append((_normalized_url(href), alt))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.links:
            self.links.pop()


def _source_html_artifact(capture: SourceCapture):
    for artifact_id in ("rendered-sanitized", "source-page"):
        matches = [item for item in capture.artifacts if item.artifact_id == artifact_id]
        if len(matches) == 1 and matches[0].media_type == "text/html":
            return matches[0]
    raise CopyGuardEvidenceError("hash-pinned source HTML artifact is not registered")


def _rendered_media_alts(capture: SourceCapture, artifact_root: Optional[Path]) -> List[str]:
    media = sorted(
        (item for item in capture.rendered_media if not item.excluded),
        key=lambda item: item.position,
    )
    if not media:
        return []
    if artifact_root is None:
        raise CopyGuardEvidenceError("rendered-media alt resolution requires the signed source bundle")
    artifact = _source_html_artifact(capture)
    path = _safe_artifact_path(artifact_root, artifact.relative_path)
    raw = path.read_bytes()
    if sha256_bytes(raw) != artifact.sha256:
        raise CopyGuardEvidenceError("rendered-sanitized artifact hash mismatch")
    parser = _ImageAltParser()
    parser.feed(raw.decode("utf-8"))
    alt_values: Dict[str, set] = {}
    for url, alt in parser.images:
        alt_values.setdefault(url, set()).add(alt)
    result = []
    for item in media:
        values = alt_values.get(_normalized_url(item.url), set())
        if len(values) != 1:
            raise CopyGuardEvidenceError(
                "rendered-media URL must resolve to exactly one alt value: %s" % item.url
            )
        result.append(next(iter(values)))
    return result


def build_source_field_records(
    capture: SourceCapture,
    artifact_root: Optional[Path],
) -> List[Dict[str, str]]:
    raw_fields: List[Tuple[str, str]] = []
    if capture.title:
        raw_fields.append(("/title", capture.title))
    for index, section in enumerate(sorted(capture.sections, key=lambda item: item.order)):
        raw_fields.append(("/sections/%s/heading" % index, section.heading))
        raw_fields.append(("/sections/%s/raw_text" % index, section.raw_text))
    seo = (capture.structured_product_evidence or {}).get("seo") or {}
    if seo.get("html_title"):
        raw_fields.append(
            ("/structured_product_evidence/seo/html_title", seo["html_title"])
        )
    if seo.get("meta_description"):
        raw_fields.append(
            (
                "/structured_product_evidence/seo/meta_description",
                seo["meta_description"],
            )
        )
    for index, alt in enumerate(_rendered_media_alts(capture, artifact_root)):
        raw_fields.append(
            ("artifact:%s#/product_gallery_media_alt/%s" % (_source_html_artifact(capture).artifact_id, index), alt)
        )
    return [record for path, value in raw_fields if (record := _record(path, value))]


def build_target_field_records(document: Dict[str, Any]) -> List[Dict[str, str]]:
    composition = document["composition"]
    target = document["shopify_target_state"]
    media_plan = document["MediaPlan"]
    raw_fields: List[Tuple[str, str]] = []
    raw_fields.append(("/composition/title/value", composition["title"]["value"]))
    for slot_index, slot in enumerate(composition["description"]["slots"]):
        if "text" in slot:
            raw_fields.append(
                ("/composition/description/slots/%s/text" % slot_index, slot["text"])
            )
        if slot.get("items"):
            for item_index, item in enumerate(slot.get("items") or []):
                raw_fields.append(
                    (
                        "/composition/description/slots/%s/items/%s/text"
                        % (slot_index, item_index),
                        item["text"],
                    )
                )
    snapshot = document.get("store_policy_snapshot")
    for section_index, section in enumerate(composition["below_fold_sections"]):
        raw_fields.append(
            (
                "/composition/below_fold_sections/%s/heading" % section_index,
                section["heading"],
            )
        )
        for item_index, item in enumerate(section.get("items") or []):
            raw_fields.append(
                (
                    "/composition/below_fold_sections/%s/items/%s/text"
                    % (section_index, item_index),
                    item["text"],
                )
            )
        if snapshot and section.get("id") == "delivery":
            raw_fields.append(
                ("/store_policy_snapshot/delivery/content", snapshot["delivery"]["content"])
            )
        if snapshot and section.get("id") == "returns_and_refunds":
            raw_fields.append(
                (
                    "/store_policy_snapshot/returns_and_refunds/content",
                    snapshot["returns_and_refunds"]["content"],
                )
            )
    raw_fields.extend(
        (
            ("/shopify_target_state/seo/page_title", target["seo"]["page_title"]),
            (
                "/shopify_target_state/seo/meta_description",
                target["seo"]["meta_description"],
            ),
        )
    )
    for index, tag in enumerate(target["tags"]):
        raw_fields.append(("/shopify_target_state/tags/%s" % index, tag))
    def collect_rich_text(value: Any, path: str) -> None:
        if not isinstance(value, dict):
            raise CopyGuardEvidenceError("rich-text node is not an object: %s" % path)
        if value.get("type") == "text":
            raw_fields.append((path + "/value", value.get("value")))
        children = value.get("children", [])
        if not isinstance(children, list):
            raise CopyGuardEvidenceError("rich-text children must be a list: %s" % path)
        for index, child in enumerate(children):
            collect_rich_text(child, path + "/children/%s" % index)

    for key, value in sorted(target.get("rich_text_metafields", {}).items()):
        collect_rich_text(value, "/shopify_target_state/rich_text_metafields/" + key)
    if "rich_text_metafields" in target:
        # Current plans also expose these scalar custom fields to customers.
        # Historical fixtures predate the rich-text layout and keep their pins.
        for key, value in sorted(target.get("metafields", {}).items()):
            raw_fields.append(("/shopify_target_state/metafields/" + key, value))
    for index, slot in enumerate(media_plan["slots"]):
        raw_fields.append(("/MediaPlan/slots/%s/filename" % index, slot["filename"]))
        raw_fields.append(("/MediaPlan/slots/%s/alt_text" % index, slot["alt_text"]))
    return [record for path, value in raw_fields if (record := _record(path, value))]


def _json_pointer_value(document: Dict[str, Any], pointer: str) -> Any:
    value: Any = document
    for raw_part in pointer.lstrip("/").split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def _tokens(records: Sequence[Dict[str, str]]) -> List[str]:
    return [token for record in records for token in record["normalized"].split()]


def _three_gram_locations(
    records: Sequence[Dict[str, str]],
) -> Dict[str, List[str]]:
    locations: Dict[str, set] = {}
    for record in records:
        tokens = record["normalized"].split()
        for index in range(max(0, len(tokens) - 2)):
            span = " ".join(tokens[index:index + 3])
            locations.setdefault(span, set()).add(record["path"])
    return {span: sorted(paths) for span, paths in locations.items()}


def _lcs_length(left: Sequence[str], right: Sequence[str]) -> int:
    if len(right) > len(left):
        left, right = right, left
    row = [0] * (len(right) + 1)
    for left_token in left:
        previous = 0
        for index, right_token in enumerate(right, start=1):
            saved = row[index]
            if left_token == right_token:
                row[index] = previous + 1
            else:
                row[index] = max(row[index], row[index - 1])
            previous = saved
    return row[-1]


def _forbidden_hits(records: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    hits: List[Dict[str, str]] = []
    for record in records:
        text = record["normalized"]
        raw_path = record["path"]
        raw_terms = set(text.split())
        if BANNED_TERMS.intersection(raw_terms):
            hits.append({"code": "BANNED_VOICE_TERM", "path": raw_path})
        for code, patterns in (
            ("URGENCY_LANGUAGE", URGENCY_PATTERNS),
            ("MEDICAL_LANGUAGE", MEDICAL_PATTERNS),
            ("SECONDARY_CTA", SECONDARY_CTA_PATTERNS),
        ):
            if any(re.search(pattern, text) for pattern in patterns):
                hits.append({"code": code, "path": raw_path})
        if re.search(r"(?:https?\s+|www\s+|\b[a-z0-9-]+\s+(?:com|co\s+uk|net|org)\b)", text):
            hits.append({"code": "EXTERNAL_URL", "path": raw_path})
    return sorted(hits, key=lambda item: (item["path"], item["code"]))


def build_copy_guard_result(
    document: Dict[str, Any],
    source_capture: SourceCapture,
    source_capture_sha256: str,
    source_artifact_root: Optional[Path] = None,
    exemptions: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    source_records = build_source_field_records(source_capture, source_artifact_root)
    target_records = build_target_field_records(document)
    source_locations = _three_gram_locations(source_records)
    target_locations = _three_gram_locations(target_records)
    shared = set(source_locations).intersection(target_locations)
    accepted_exemptions: List[Dict[str, Any]] = []
    invalid_hits: List[Dict[str, str]] = []
    exempted_spans = set()
    for raw in exemptions or []:
        exemption = {
            "normalized_span": raw.get("normalized_span"),
            "whitelist_rule_id": raw.get("whitelist_rule_id"),
            "source_field_paths": list(raw.get("source_field_paths") or []),
            "target_field_paths": list(raw.get("target_field_paths") or []),
        }
        span = exemption["normalized_span"]
        valid = (
            exemption["whitelist_rule_id"] in APPROVED_EXEMPTION_RULES
            and span in shared
            and exemption["source_field_paths"] == source_locations.get(span)
            and exemption["target_field_paths"] == target_locations.get(span)
        )
        if valid:
            exempted_spans.add(span)
            accepted_exemptions.append(exemption)
        else:
            invalid_hits.append(
                {"code": "INVALID_COPY_GUARD_EXEMPTION", "path": str(span)}
            )
    accepted_exemptions.sort(key=lambda item: item["normalized_span"])
    non_whitelisted = [
        {
            "normalized_span": span,
            "source_field_paths": source_locations[span],
            "target_field_paths": target_locations[span],
        }
        for span in sorted(shared - exempted_spans)
    ]
    source_tokens = _tokens(source_records)
    target_tokens = _tokens(target_records)
    lcs_count = _lcs_length(source_tokens, target_tokens)
    ratio = round(lcs_count / len(target_tokens), 6) if target_tokens else 1.0
    forbidden_hits = _forbidden_hits(target_records) + invalid_hits
    for record in target_records:
        if "!" in str(_json_pointer_value(document, record["path"])):
            forbidden_hits.append({"code": "EXCLAMATION_MARK", "path": record["path"]})
    forbidden_hits = sorted(forbidden_hits, key=lambda item: (item["path"], item["code"]))
    result: Dict[str, Any] = {
        "algorithm_id": ALGORITHM_ID,
        "normalization_version": NORMALIZATION_VERSION,
        "customer_field_paths": [record["path"] for record in target_records],
        "source_field_paths": [record["path"] for record in source_records],
        "source_media_alt_field_count": sum(
            record["path"].startswith("artifact:rendered-sanitized#")
            for record in source_records
        ),
        "source_capture_sha256": source_capture_sha256,
        "source_corpus_sha256": sha256_bytes(canonical_json_bytes(source_records)),
        "target_corpus_sha256": sha256_bytes(canonical_json_bytes(target_records)),
        "report_sha256": "",
        "non_whitelisted_shared_three_grams": non_whitelisted,
        "exemptions": accepted_exemptions,
        "forbidden_customer_hits": forbidden_hits,
        "source_order_lcs": {
            "source_token_count": len(source_tokens),
            "target_token_count": len(target_tokens),
            "lcs_token_count": lcs_count,
            "denominator": "TARGET_TOKEN_COUNT",
            "ratio": ratio,
            "threshold": 0.5,
        },
        "result": (
            "PASS"
            if not non_whitelisted
            and not forbidden_hits
            and target_tokens
            and 2 * lcs_count < len(target_tokens)
            else "FAIL"
        ),
    }
    report_payload = dict(result)
    report_payload.pop("report_sha256")
    result["report_sha256"] = sha256_bytes(canonical_json_bytes(report_payload))
    return result
