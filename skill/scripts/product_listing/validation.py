"""Machine-enforced Phase 1 source capture stops."""

from typing import List, Set, Tuple

from product_listing.models import (
    ConflictSeverity,
    ConflictState,
    FactConflictState,
    GapSeverity,
    SectionRole,
    SourceCapture,
    ValidationIssue,
)


FAIL_CLOSED_ACQUISITION_GAP_CODES = frozenset({"LINKED_SIBLING_PDP_UNOPENED"})


def _issue(code: str, path: str, message: str) -> ValidationIssue:
    return ValidationIssue(code=code, field_path=path, message=message, blocking=True)


def validate_source_capture(capture: SourceCapture) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    if not capture.consumer_retail_source or not capture.source_class_evidence.consumer_retail_source:
        issues.append(
            _issue(
                "INVALID_SOURCE_CLASS",
                "consumer_retail_source",
                "source is not a public consumer retail product page",
            )
        )
    if not capture.title:
        issues.append(_issue("MISSING_CRITICAL_FACT", "title", "source title is missing"))
    if capture.current_price is None:
        issues.append(
            _issue("MISSING_CRITICAL_FACT", "current_price", "customer-paid source price is missing")
        )
    if not capture.variants:
        issues.append(
            _issue("MISSING_CRITICAL_FACT", "variants", "exact source variant structure is missing")
        )
    if not capture.rendered_media or not capture.structured_media:
        issues.append(
            _issue(
                "MISSING_CRITICAL_FACT",
                "media",
                "both rendered and structured source media orders are required",
            )
        )

    for conflict in capture.conflicts:
        if conflict.severity == ConflictSeverity.BLOCKING and conflict.state == ConflictState.UNRESOLVED:
            issues.append(
                _issue(
                    conflict.code,
                    conflict.field_path,
                    "%s: %s blocks %s" % (
                        conflict.code,
                        conflict.rationale,
                        ", ".join(conflict.blocked_output_ids),
                    ),
                )
            )

    for gap in capture.acquisition_gaps:
        if (
            gap.severity == GapSeverity.BLOCKING
            or gap.code in FAIL_CLOSED_ACQUISITION_GAP_CODES
        ):
            issues.append(
                _issue(
                    gap.code,
                    "acquisition_gaps",
                    gap.detail or "blocking acquisition evidence is missing",
                )
            )

    option_names = [option.name for option in capture.options]
    option_positions = [option.position for option in capture.options]
    if len(capture.options) > 3:
        issues.append(_issue("OPTION_LIMIT_EXCEEDED", "options", "source has more than three dimensions"))
    if option_positions != list(range(1, len(option_positions) + 1)):
        issues.append(
            _issue(
                "VARIANT_STRUCTURE_INVALID",
                "options",
                "option positions must be contiguous and ordered",
            )
        )
    if len(option_names) != len(set(option_names)):
        issues.append(_issue("VARIANT_STRUCTURE_INVALID", "options", "option names must be unique"))
    for index, option in enumerate(capture.options):
        if len(option.values) != len(set(option.values)):
            issues.append(
                _issue(
                    "VARIANT_STRUCTURE_INVALID",
                    "options[%s].values" % index,
                    "option values must be unique and ordered",
                )
            )

    combinations: Set[Tuple[str, ...]] = set()
    observed_values = {name: set() for name in option_names}
    for index, variant in enumerate(capture.variants):
        names = [item.option_name for item in variant.option_values]
        if names != option_names:
            issues.append(
                _issue(
                    "VARIANT_STRUCTURE_INVALID",
                    "variants[%s].option_values" % index,
                    "variant values must match the exact ordered source dimensions",
                )
            )
            continue
        combination = tuple(item.value for item in variant.option_values)
        for item, option in zip(variant.option_values, capture.options):
            if item.value not in option.values:
                issues.append(
                    _issue(
                        "VARIANT_STRUCTURE_INVALID",
                        "variants[%s].option_values" % index,
                        "variant value is absent from the ordered source option values",
                    )
                )
            observed_values[item.option_name].add(item.value)
        if combination in combinations:
            issues.append(
                _issue(
                    "VARIANT_STRUCTURE_INVALID",
                    "variants[%s]" % index,
                    "duplicate source variant combination",
                )
            )
        combinations.add(combination)
    for option in capture.options:
        missing_values = set(option.values) - observed_values[option.name]
        if missing_values:
            issues.append(
                _issue(
                    "VARIANT_STRUCTURE_INVALID",
                    "options.%s" % option.name,
                    "source option values lack captured real combinations: %s"
                    % ", ".join(sorted(missing_values)),
                )
            )

    captured_roles = {section.role for section in capture.sections}
    if capture.source_model_evidence:
        captured_roles.add(SectionRole.SOURCE_MODEL_EVIDENCE)
    absent_roles = {absence.role for absence in capture.expected_role_absences}
    for role in capture.expected_section_roles:
        if role not in captured_roles and role not in absent_roles:
            issues.append(
                _issue(
                    "EXPECTED_ROLE_UNACCOUNTED",
                    "expected_section_roles",
                    "%s is neither captured nor explicitly absent" % role.value,
                )
            )

    table_by_id = {
        table.table_id: table
        for section in capture.sections
        for table in section.tables
    }
    for table_id in capture.size_guide_table_ids:
        table = table_by_id[table_id]
        if table.role != SectionRole.SIZE_GUIDE:
            issues.append(
                _issue(
                    "SIZE_GUIDE_INVALID",
                    "size_guide_table_ids",
                    "%s is not tagged SIZE_GUIDE" % table_id,
                )
            )
        if not table.headings or not table.rows:
            issues.append(
                _issue(
                    "SIZE_GUIDE_INVALID",
                    "sections.tables.%s" % table_id,
                    "size guide requires headings and rows",
                )
            )
        for row in table.rows:
            source_columns = [cell.source_column for cell in row.cells]
            if source_columns != sorted(source_columns) or len(source_columns) != len(set(source_columns)):
                issues.append(
                    _issue(
                        "SIZE_GUIDE_INVALID",
                        "sections.tables.%s.rows[%s]" % (table_id, row.order - 1),
                        "size-guide source columns must be unique and ordered",
                    )
                )

    for collection_name, media in (
        ("rendered_media", capture.rendered_media),
        ("structured_media", capture.structured_media),
    ):
        relation_ids = {relation.relation_id for relation in capture.colour_relations}
        for index, item in enumerate(media):
            if item.colour_relation_id and item.colour_relation_id not in relation_ids:
                issues.append(
                    _issue(
                        "MEDIA_RELATION_INVALID",
                        "%s[%s].colour_relation_id" % (collection_name, index),
                        "media colour relation is not captured",
                    )
                )

    for fact in capture.facts:
        if fact.conflict_state == FactConflictState.UNRESOLVED and fact.composer_input_eligible:
            issues.append(
                _issue(
                    "CONFLICTED_FACT_EXPOSED",
                    "facts.%s" % fact.fact_id,
                    "unresolved facts cannot be composer inputs",
                )
            )

    return issues
