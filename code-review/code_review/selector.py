"""Review-selection resolution logic.

Pure, stateless functions — no I/O, no CLI dependencies.  The CLI feeds
capabilities.json analyzer entries + user flags; this module returns which
analyzer IDs to run plus any warning messages.

Resolution precedence is specified in s5-review-selection-scheme.md.
This module deliberately does not duplicate the spec; it implements it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_DEPTH_ORDER: dict[str, int] = {"quick": 0, "full": 1}


@dataclass
class SelectionResult:
    analyzers: list[str]
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def resolve_review_selection(
    analyzer_entries: list[dict[str, Any]],
    review: list[str],
    depth: str,
    scope: str,
    diff_languages: frozenset[str] | None = None,
    disabled: set[str] | None = None,
    depth_explicit: bool = False,
) -> SelectionResult:
    """Resolve --review / --depth to a sorted list of analyzer IDs.

    Parameters
    ----------
    analyzer_entries:
        The ``analyzers`` list from capabilities.json; each entry must have
        ``id``, ``domain``, ``subcategory``, ``tier``, ``languages``, and
        optionally ``scope_restriction``.
    review:
        Already normalised (lowercase) and deduplicated list of domain or
        subcategory names the caller requested.  Empty means "no --review".
    depth:
        ``"quick"`` or ``"full"``.
    scope:
        ``"per-task"`` or ``"story-level"``.
    diff_languages:
        Set of language names present in the diff.  ``None`` means no filter.
    disabled:
        Analyzer IDs disabled by config.  These are silently excluded.
    depth_explicit:
        ``True`` when the caller actually passed ``--depth`` (not the default).
        Used to decide whether to emit the "depth ignored" warning for
        subcategory-only selections.
    """
    disabled = disabled or set()

    domains: set[str] = {a["domain"] for a in analyzer_entries}
    subcategories: set[str] = {a["subcategory"] for a in analyzer_entries}
    valid_names = domains | subcategories

    # Validate --review values immediately
    unknown = [v for v in review if v not in valid_names]
    if unknown:
        return SelectionResult(
            analyzers=[],
            error=(
                f"Unknown --review value(s): {', '.join(repr(v) for v in unknown)}. "
                f"Valid domains: {', '.join(sorted(domains))}. "
                f"Valid subcategories: {', '.join(sorted(subcategories))}."
            ),
        )

    warnings: list[str] = []
    review_domains = [v for v in review if v in domains]
    review_subcats = [v for v in review if v in subcategories]

    # Warn if user named only subcategories and passed an explicit --depth
    if review_subcats and not review_domains and depth_explicit:
        subcat_display = ", ".join(f"--review {v}" for v in review_subcats)
        warnings.append(
            f"--depth {depth} is ignored when a subcategory is named "
            f"({subcat_display}); subcategory selection is depth-independent."
        )

    # --- Step 1: build candidate IDs before filtering ---

    if not review:
        # Standalone depth: every analyzer at tier <= depth
        candidate_ids: set[str] = {
            a["id"]
            for a in analyzer_entries
            if _DEPTH_ORDER[a["tier"]] <= _DEPTH_ORDER[depth]
        }
    else:
        # Expand domains at active depth
        domain_ids: set[str] = set()
        for dv in review_domains:
            for a in analyzer_entries:
                if a["domain"] == dv and _DEPTH_ORDER[a["tier"]] <= _DEPTH_ORDER[depth]:
                    domain_ids.add(a["id"])

        # Add subcategory IDs; check for redundancy against domain expansion
        subcat_ids: set[str] = set()
        for sv in review_subcats:
            sv_ids = {a["id"] for a in analyzer_entries if a["subcategory"] == sv}
            if sv_ids and sv_ids <= domain_ids:
                # This subcategory adds nothing — find the including domain for the message
                including_domain = next(
                    (
                        a["domain"]
                        for a in analyzer_entries
                        if a["subcategory"] == sv
                        and _DEPTH_ORDER[a["tier"]] <= _DEPTH_ORDER[depth]
                    ),
                    None,
                )
                if including_domain:
                    warnings.append(
                        f"--review {sv} is redundant: subcategory '{sv}' is already "
                        f"included by --review {including_domain} at --depth {depth}."
                    )
            else:
                subcat_ids |= sv_ids

        candidate_ids = domain_ids | subcat_ids

    # --- Step 2: catch domain@depth = empty (specific error) ---
    for dv in review_domains:
        tier_match = [
            a for a in analyzer_entries
            if a["domain"] == dv and _DEPTH_ORDER[a["tier"]] <= _DEPTH_ORDER[depth]
        ]
        if not tier_match:
            return SelectionResult(
                analyzers=[],
                error=(
                    f"domain '{dv}' has no {depth}-tier analyzers; use --depth full"
                ),
            )

    # --- Step 3: scope filter ---
    scope_excluded: set[str] = set()
    scope_allowed: set[str] = set()
    for a in analyzer_entries:
        if a["id"] not in candidate_ids:
            continue
        restriction = a.get("scope_restriction")
        if restriction and restriction != scope:
            scope_excluded.add(a["id"])
        else:
            scope_allowed.add(a["id"])

    # Error when an explicit request resolves exclusively to story-level-only analyzers
    if scope_excluded and not scope_allowed:
        req_scope = next(
            a["scope_restriction"]
            for a in analyzer_entries
            if a["id"] in scope_excluded
        )
        excluded_names = ", ".join(sorted(scope_excluded))
        return SelectionResult(
            analyzers=[],
            error=(
                f"Analyzer(s) {excluded_names} require --scope {req_scope}; "
                f"use --scope {req_scope} to include them."
            ),
        )

    # --- Step 4: language filter ---
    if diff_languages is not None:
        result_ids: set[str] = {
            a["id"]
            for a in analyzer_entries
            if a["id"] in scope_allowed
            and (not a["languages"] or frozenset(a["languages"]) & diff_languages)
        }
    else:
        result_ids = scope_allowed

    # --- Step 5: disabled filter ---
    result_ids -= disabled

    return SelectionResult(analyzers=sorted(result_ids), warnings=warnings)
