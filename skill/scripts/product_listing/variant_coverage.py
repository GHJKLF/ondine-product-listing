"""Hash-pinned, offline validation of a colour-family's real variant rows."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable
from urllib.parse import urldefrag, urljoin, urlparse

from lxml import etree, html


_COLOUR_NAMES = {"colour", "color"}


@dataclass
class _Error:
    code: str
    message: str
    path: str = "$"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "path": self.path}


def _xpath(page_html: str, expression: str) -> list[Any]:
    """Run the manifest's exact XPath against its hash-pinned selector HTML."""
    if not isinstance(expression, str) or not expression:
        raise ValueError("selector XPath is required")
    result = html.fromstring(page_html).xpath(expression)
    if not isinstance(result, list):
        raise ValueError("selector XPath must resolve elements, not a scalar value")
    if any(not hasattr(node, "xpath") for node in result):
        raise ValueError("selector XPath must resolve elements, not scalar values")
    return result


def _normal_url(base_url: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("URL is required")
    return urldefrag(urljoin(base_url, value.strip())).url


def _url_handle(url: str) -> str | None:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) >= 2 and parts[-2] == "products" and parts[-1]:
        return parts[-1]
    return None


def _safe_path(raw: Any, roots: list[Path], errors: list[_Error], path: str) -> Path | None:
    if not isinstance(raw, str) or not raw:
        errors.append(_Error("PATH_INVALID", "path is required", path))
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = roots[0] / candidate
    resolved = candidate.resolve()
    if not any(resolved.is_relative_to(root) for root in roots):
        errors.append(_Error("PATH_OUTSIDE_ALLOWED_ROOT", "path escapes the manifest folder and explicit source root", path))
        return None
    if not resolved.is_file():
        errors.append(_Error("ARTIFACT_MISSING", "artifact is missing: %s" % raw, path))
        return None
    return resolved


def _load_json(path: Path, errors: list[_Error], label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(_Error("JSON_INVALID", "%s is not valid JSON: %s" % (label, exc), label))
        return None


def _verify_hash(path: Path, expected: Any, errors: list[_Error], label: str) -> bool:
    actual = sha256(path.read_bytes()).hexdigest()
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        errors.append(_Error("ARTIFACT_HASH_INVALID", "sha256 must be a lowercase 64-character hex digest", label))
        return False
    if actual != expected:
        errors.append(_Error("ARTIFACT_HASH_MISMATCH", "sha256 does not match %s" % path.name, label))
        return False
    return True


def _variant_values(document: dict[str, Any], option_names: list[str], error_path: str, errors: list[_Error]) -> list[tuple[str, ...]]:
    variants = document.get("variants")
    if not isinstance(variants, list) or not variants:
        errors.append(_Error("SOURCE_VARIANTS_INVALID", "source variants must be a non-empty list", error_path + ".variants"))
        return []
    result: list[tuple[str, ...]] = []
    for index, variant in enumerate(variants):
        if not isinstance(variant, dict):
            errors.append(_Error("SOURCE_VARIANTS_INVALID", "variant must be an object", "%s.variants[%s]" % (error_path, index)))
            continue
        values = variant.get("options")
        if not isinstance(values, list):
            values = [variant.get("option%s" % position) for position in range(1, len(option_names) + 1)]
        if len(values) != len(option_names) or any(not isinstance(value, str) or not value for value in values):
            errors.append(_Error("SOURCE_VARIANTS_INVALID", "variant must contain one non-empty value per option", "%s.variants[%s]" % (error_path, index)))
            continue
        result.append(tuple(values))
    return result


def _source_rows(entry: dict[str, Any], document: dict[str, Any], path: str, errors: list[_Error]) -> tuple[list[str], list[dict[str, str]], list[str]]:
    options = document.get("options")
    if not isinstance(options, list) or not options:
        errors.append(_Error("SOURCE_OPTIONS_INVALID", "source options must be a non-empty list", path + ".options"))
        return [], [], []
    names: list[str] = []
    declared: dict[str, set[str]] = {}
    for index, option in enumerate(options):
        if not isinstance(option, dict) or not isinstance(option.get("name"), str) or not option["name"]:
            errors.append(_Error("SOURCE_OPTIONS_INVALID", "option needs a name", "%s.options[%s]" % (path, index)))
            return [], [], []
        name = option["name"]
        values = option.get("values")
        if not isinstance(values, list) or not values or any(not isinstance(value, str) or not value for value in values) or len(values) != len(set(values)):
            errors.append(_Error("SOURCE_OPTIONS_INVALID", "option values must be a non-empty unique string list", "%s.options[%s]" % (path, index)))
            return [], [], []
        if name in names:
            errors.append(_Error("SOURCE_OPTIONS_INVALID", "option names must be unique", path + ".options"))
            return [], [], []
        names.append(name)
        declared[name] = set(values)
    colour_indexes = [index for index, name in enumerate(names) if name.casefold() in _COLOUR_NAMES]
    if len(colour_indexes) > 1:
        errors.append(_Error("SOURCE_OPTIONS_INVALID", "source has more than one colour dimension", path + ".options"))
        return [], [], []
    colour_index = colour_indexes[0] if colour_indexes else None
    non_colour_names = [name for index, name in enumerate(names) if index != colour_index]
    values = _variant_values(document, names, path, errors)
    rows: list[dict[str, str]] = []
    colours: list[str] = []
    singleton = entry.get("colour")
    if colour_index is None:
        if not isinstance(singleton, str) or not singleton.strip():
            errors.append(_Error("SINGLETON_COLOUR_REQUIRED", "size-only source JSON requires a verified source colour", path + ".colour"))
            return non_colour_names, [], []
        colours = [singleton.strip()]
    elif singleton is not None:
        errors.append(_Error("COLOUR_SOURCE_CONFLICT", "colour is only allowed when source JSON has no colour option", path + ".colour"))
        return non_colour_names, [], []
    for variant in values:
        if any(value not in declared[name] for name, value in zip(names, variant)):
            errors.append(_Error("SOURCE_VARIANTS_INVALID", "variant uses a value missing from source options", path + ".variants"))
            continue
        colour_values = [variant[colour_index]] if colour_index is not None else colours
        for colour in colour_values:
            if colour not in colours:
                colours.append(colour)
            row = {"Colour": colour}
            for index, name in enumerate(names):
                if index != colour_index:
                    row[name] = variant[index]
            rows.append(row)
    return non_colour_names, rows, colours


def _row_key(row: dict[str, str], names: list[str]) -> tuple[str, ...]:
    return tuple(row[name] for name in names)


def _ordered_unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def validate_variant_coverage(manifest_path: str | Path, target_path: str | Path) -> dict[str, Any]:
    """Return a deterministic coverage report. Any error makes ``ok`` false."""
    errors: list[_Error] = []
    manifest_file = Path(manifest_path).resolve()
    if not manifest_file.is_file():
        return {"ok": False, "expected": [], "missing": [], "extra": [],
                "errors": [_Error("MANIFEST_MISSING", "manifest is missing", "manifest").as_dict()]}
    manifest = _load_json(manifest_file, errors, "manifest")
    if not isinstance(manifest, dict):
        return {"ok": False, "expected": [], "missing": [], "extra": [], "errors": [error.as_dict() for error in errors]}
    if manifest.get("schema_version") != 1:
        errors.append(_Error("MANIFEST_SCHEMA_INVALID", "schema_version must be 1", "$.schema_version"))
    manifest_root = manifest_file.parent.resolve()
    roots = [manifest_root]
    source_root = manifest.get("source_root")
    if source_root is not None:
        if not isinstance(source_root, str) or not source_root:
            errors.append(_Error("SOURCE_ROOT_INVALID", "source_root must be a non-empty path", "$.source_root"))
        else:
            root = Path(source_root)
            if not root.is_absolute():
                root = manifest_root / root
            root = root.resolve()
            if not root.is_dir():
                errors.append(_Error("SOURCE_ROOT_INVALID", "source_root must exist as a directory", "$.source_root"))
            else:
                roots.append(root)
    selector = manifest.get("selector")
    if not isinstance(selector, dict):
        errors.append(_Error("MANIFEST_SCHEMA_INVALID", "selector object is required", "$.selector"))
        selector = {}
    selector_file = _safe_path(selector.get("html_path"), roots, errors, "$.selector.html_path")
    selector_ok = selector_file is not None and _verify_hash(selector_file, selector.get("sha256"), errors, "$.selector.sha256")
    base_url = manifest.get("base_url")
    if not isinstance(base_url, str) or not base_url:
        errors.append(_Error("MANIFEST_SCHEMA_INVALID", "base_url is required", "$.base_url"))
    discovered: list[str] = []
    if selector_ok and isinstance(base_url, str) and base_url:
        try:
            nodes = _xpath(selector_file.read_text(encoding="utf-8"), selector.get("xpath"))
            if len(nodes) != 1:
                errors.append(_Error("SELECTOR_AMBIGUOUS", "selector XPath must resolve exactly one PDP swatch container", "$.selector.xpath"))
            else:
                discovered = _ordered_unique(_normal_url(base_url, href)
                    for href in nodes[0].xpath(".//a[@href]/@href"))
                if not discovered:
                    errors.append(_Error("SWATCH_URLS_MISSING", "selected PDP swatch container has no product links", "$.selector.xpath"))
        except (ValueError, UnicodeDecodeError, etree.LxmlError) as exc:
            errors.append(_Error("SELECTOR_INVALID", str(exc), "$.selector.xpath"))
    entries = manifest.get("sources")
    if not isinstance(entries, list) or not entries:
        errors.append(_Error("MANIFEST_SCHEMA_INVALID", "sources must be a non-empty list", "$.sources"))
        entries = []
    by_url: dict[str, dict[str, Any]] = {}
    source_payloads: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    for index, entry in enumerate(entries):
        entry_path = "$.sources[%s]" % index
        if not isinstance(entry, dict):
            errors.append(_Error("MANIFEST_SCHEMA_INVALID", "source record must be an object", entry_path))
            continue
        try:
            url = _normal_url(base_url if isinstance(base_url, str) else "", entry.get("url"))
        except ValueError as exc:
            errors.append(_Error("MANIFEST_SCHEMA_INVALID", str(exc), entry_path + ".url"))
            continue
        if url in by_url:
            errors.append(_Error("SOURCE_URL_DUPLICATE", "each source URL may appear once", entry_path + ".url"))
            continue
        by_url[url] = entry
        product_path = _safe_path(entry.get("product_json"), roots, errors, entry_path + ".product_json")
        if product_path is None or not _verify_hash(product_path, entry.get("sha256"), errors, entry_path + ".sha256"):
            continue
        document = _load_json(product_path, errors, entry_path + ".product_json")
        if isinstance(document, dict):
            source_handle = document.get("handle")
            if source_handle is not None:
                expected_handle = _url_handle(url)
                if not isinstance(source_handle, str) or not source_handle or source_handle != expected_handle:
                    errors.append(_Error("SOURCE_URL_HANDLE_MISMATCH", "source JSON handle does not match its captured product URL", entry_path + ".product_json"))
            source_payloads.append((entry, document, entry_path))
    for url in discovered:
        if url not in by_url:
            errors.append(_Error("DISCOVERED_SIBLING_UNCAPTURED", "discovered swatch URL has no source record: %s" % url, "$.sources"))
    for url in by_url:
        if discovered and url not in discovered:
            errors.append(_Error("SOURCE_URL_NOT_DISCOVERED", "source URL is outside the pinned swatch family: %s" % url, "$.sources"))
    non_colour_names: list[str] | None = None
    rows: list[dict[str, str]] = []
    all_colours: list[str] = []
    singleton_owner: dict[str, str] = {}
    size_map = manifest.get("size_label_map", {})
    if not isinstance(size_map, dict) or any(not isinstance(key, str) or not isinstance(value, str) or not key or not value for key, value in size_map.items()):
        errors.append(_Error("SIZE_LABEL_MAP_INVALID", "size_label_map must map non-empty source labels to target labels", "$.size_label_map"))
        size_map = {}
    for entry, document, entry_path in source_payloads:
        source_names, source_rows, source_colours = _source_rows(entry, document, entry_path, errors)
        if non_colour_names is None:
            non_colour_names = source_names
        elif non_colour_names != source_names:
            errors.append(_Error("SOURCE_DIMENSIONS_INCONSISTENT", "source siblings must have the same non-colour option dimensions", entry_path + ".product_json"))
            continue
        singleton = entry.get("colour")
        if isinstance(singleton, str) and singleton.strip():
            colour = singleton.strip()
            owner = singleton_owner.setdefault(colour, _normal_url(base_url, entry["url"]))
            if owner != _normal_url(base_url, entry["url"]):
                errors.append(_Error("COLOUR_SOURCE_CONFLICT", "verified singleton colour belongs to multiple source URLs", entry_path + ".colour"))
        for row in source_rows:
            if "Size" in row and row["Size"] in size_map:
                row["Size"] = size_map[row["Size"]]
            rows.append(row)
        all_colours.extend(source_colours)
    if non_colour_names is None:
        non_colour_names = []
    # A mapping key must occur in raw source evidence. Re-read options instead of guessing from target labels.
    raw_size_values = set()
    for _, document, _ in source_payloads:
        options = document.get("options", [])
        if not isinstance(options, list):
            continue
        for option in options:
            values = option.get("values") if isinstance(option, dict) else None
            if isinstance(option, dict) and option.get("name") == "Size" and isinstance(values, list):
                raw_size_values.update(value for value in values if isinstance(value, str))
    if set(size_map) - raw_size_values:
        errors.append(_Error("SIZE_LABEL_MAP_INVALID", "size_label_map contains a source size absent from captured JSON", "$.size_label_map"))
    effective_size_labels: dict[str, str] = {}
    for raw_label in raw_size_values:
        target_label = size_map.get(raw_label, raw_label)
        prior_raw_label = effective_size_labels.setdefault(target_label, raw_label)
        if prior_raw_label != raw_label:
            errors.append(_Error("SIZE_LABEL_MAP_COLLISION", "size_label_map collapses distinct observed source sizes onto %s" % target_label, "$.size_label_map"))
            break
    all_colours = _ordered_unique(all_colours)
    selection_explicit = "selected_colours" in manifest
    selected = manifest.get("selected_colours", all_colours)
    excluded = manifest.get("excluded_colours", {})
    if not isinstance(selected, list) or any(not isinstance(value, str) or not value for value in selected) or len(selected) != len(set(selected)):
        errors.append(_Error("COLOUR_SELECTION_INVALID", "selected_colours must be a unique string list", "$.selected_colours"))
        selected = []
    if not isinstance(excluded, dict) or any(not isinstance(colour, str) or not colour or not isinstance(reason, str) or not reason.strip() for colour, reason in excluded.items()):
        errors.append(_Error("COLOUR_SELECTION_INVALID", "excluded_colours must map each colour to a non-empty reason", "$.excluded_colours"))
        excluded = {}
    expected_excluded = set(all_colours) - set(selected)
    if set(selected) - set(all_colours) or set(excluded) != expected_excluded:
        errors.append(_Error("COLOUR_SELECTION_INVALID", "selection must include captured colours or explicitly exclude every omitted colour", "$.selected_colours"))
    if selection_explicit and not selected:
        errors.append(_Error("COLOUR_SELECTION_EMPTY", "selected_colours may not exclude the entire captured colour family", "$.selected_colours"))
    names = ["Colour", *non_colour_names]
    expected_rows = _ordered_unique_rows(rows, names, selected)
    if not expected_rows:
        errors.append(_Error("EXPECTED_VARIANTS_EMPTY", "selected colours must retain at least one observed source variant", "$.selected_colours"))
    expected_options = [{"name": name, "values": _ordered_unique(row[name] for row in expected_rows)} for name in names]
    target_file = _safe_path(str(target_path), roots, errors, "target")
    target = _load_json(target_file, errors, "target") if target_file else None
    actual_rows: list[dict[str, str]] = []
    if isinstance(target, dict):
        if target.get("complete") is not True:
            errors.append(_Error("TARGET_READBACK_INCOMPLETE", "target must declare complete: true", "target.complete"))
        if target.get("options") != expected_options:
            errors.append(_Error("TARGET_OPTIONS_MISMATCH", "target options do not exactly match the selected source family", "target.options"))
        variants = target.get("variants")
        if not isinstance(variants, list):
            errors.append(_Error("TARGET_VARIANTS_INVALID", "target variants must be a list", "target.variants"))
        else:
            for index, variant in enumerate(variants):
                row = variant.get("option_values") if isinstance(variant, dict) else None
                if not isinstance(row, dict) or set(row) != set(names) or any(not isinstance(row.get(name), str) for name in names):
                    errors.append(_Error("TARGET_VARIANTS_INVALID", "each target row needs exactly the expected option values", "target.variants[%s]" % index))
                else:
                    actual_rows.append({name: row[name] for name in names})
    expected_keys = {_row_key(row, names) for row in expected_rows}
    actual_keys = [_row_key(row, names) for row in actual_rows]
    duplicates = {key for key in actual_keys if actual_keys.count(key) > 1}
    if duplicates:
        errors.append(_Error("TARGET_VARIANT_DUPLICATE", "target contains duplicate variant rows", "target.variants"))
    actual_key_set = set(actual_keys)
    missing = [row for row in expected_rows if _row_key(row, names) not in actual_key_set]
    extra = [row for row in _ordered_unique_rows(actual_rows, names, None) if _row_key(row, names) not in expected_keys]
    if missing:
        errors.append(_Error("TARGET_VARIANT_MISSING", "target is missing one or more real source rows", "target.variants"))
    if extra:
        errors.append(_Error("TARGET_VARIANT_EXTRA", "target contains a row not observed in source evidence", "target.variants"))
    return {"ok": not errors, "expected": expected_rows, "missing": missing, "extra": extra,
            "errors": [error.as_dict() for error in errors]}


def _ordered_unique_rows(rows: Iterable[dict[str, str]], names: list[str], selected: list[str] | None) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        if selected is not None and row.get("Colour") not in selected:
            continue
        if any(name not in row for name in names):
            continue
        key = _row_key(row, names)
        if key not in seen:
            seen.add(key)
            result.append({name: row[name] for name in names})
    return result
