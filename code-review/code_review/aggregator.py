from __future__ import annotations

from typing import Any

from code_review.contracts import AnalyzerOutput
from code_review.severity import map_severity

_CWE_TAXONOMY_REF = {"name": "CWE", "index": 0, "guid": "FFC64C90-42B6-44CE-8BEB-F6B7DAE649E4"}


def _get_uri(result: dict[str, Any]) -> str | None:
    locs = result.get("locations", [])
    if not locs:
        return None
    pl: dict[str, Any] = locs[0].get("physicalLocation", {})
    uri: str | None = pl.get("artifactLocation", {}).get("uri")
    return uri


def _get_line(result: dict[str, Any]) -> int | None:
    locs = result.get("locations", [])
    if not locs:
        return None
    line: int | None = (
        locs[0].get("physicalLocation", {}).get("region", {}).get("startLine")
    )
    return line


def _get_cwe(result: dict[str, Any]) -> str | None:
    for taxon in result.get("taxa", []):
        tid: str = taxon.get("id", "")
        if tid.startswith("CWE"):
            return tid
    return None


def _level_rank(level: str) -> int:
    return {"error": 3, "warning": 2, "note": 1, "none": 0}.get(level, 0)


def _higher_level(a: str, b: str) -> str:
    return a if _level_rank(a) >= _level_rank(b) else b


def _merge_key(result: dict[str, Any]) -> tuple[str, int, str] | None:
    uri = _get_uri(result)
    line = _get_line(result)
    cwe = _get_cwe(result)
    if uri is None or line is None or cwe is None:
        return None
    return (uri, line, cwe)


def _normalise_taxa(result: dict[str, Any]) -> dict[str, Any]:
    """Move CWE ids from free-form tags into taxa; remove from tags."""
    result = dict(result)
    props = dict(result.get("properties", {}))
    tags: list[str] = list(props.get("tags", []))
    cwe_from_tags = [t for t in tags if str(t).startswith("CWE")]
    if cwe_from_tags:
        tags = [t for t in tags if not str(t).startswith("CWE")]
        props["tags"] = tags
        taxa: list[dict[str, Any]] = list(result.get("taxa", []))
        existing_cwe_ids = {t.get("id") for t in taxa}
        for cwe in cwe_from_tags:
            if cwe not in existing_cwe_ids:
                taxa.append({"id": cwe, "toolComponent": {"name": "CWE"}})
        result["taxa"] = taxa
    result["properties"] = props
    return result


def _apply_sdlc_severity(result: dict[str, Any]) -> dict[str, Any]:
    result = dict(result)
    props = dict(result.get("properties", {}))
    level = result.get("level", "none")
    props_sev = props.get("severity")
    props["sdlc_severity"] = map_severity(level, props_sev)
    result["properties"] = props
    return result


def aggregate(
    outputs: list[AnalyzerOutput],
    line_tolerance: int = 3,
) -> dict[str, Any]:
    """Merge multiple per-analyzer AnalyzerOutputs into one consolidated SARIF.

    Dedup key: (uri, CWE).  Findings within line_tolerance lines of an
    existing entry with the same key are merged; lower line number wins.
    Findings without a CWE are never merged.
    """
    has_cwe = False
    merged: list[dict[str, Any]] = []  # (key | None, result, sources, original_lines)
    merge_meta: list[dict[str, Any]] = []  # parallel list of merge state
    analyzer_errors: list[dict[str, Any]] = []

    for output in outputs:
        if output.status == "error":
            analyzer_errors.append({"error": output.error, "status": output.status})
            continue

        runs = output.sarif.get("runs", [])
        tool_name = "unknown"
        if runs:
            tool_name = runs[0].get("tool", {}).get("driver", {}).get("name", "unknown")

        for run in runs:
            for raw_result in run.get("results", []):
                result = _normalise_taxa(raw_result)
                key = _merge_key(result)

                if key is not None:
                    has_cwe = True
                    uri, line, cwe = key
                    found = False
                    for i, meta in enumerate(merge_meta):
                        if meta["key"] is None:
                            continue
                        mk_uri, mk_line, mk_cwe = meta["key"]
                        same_cwe = mk_uri == uri and mk_cwe == cwe
                        if same_cwe and abs(line - mk_line) <= line_tolerance:
                            # merge: lower line wins
                            winning_line = min(line, mk_line)
                            orig = dict(meta.get("original_locations", {}))
                            orig[tool_name] = line
                            loc = merged[i]["locations"][0]["physicalLocation"]["region"]
                            loc["startLine"] = winning_line
                            old_level = merged[i]["level"]
                            new_level = result.get("level", "none")
                            merged[i]["level"] = _higher_level(old_level, new_level)
                            props = dict(merged[i].get("properties", {}))
                            sources: list[str] = list(props.get("sources", []))
                            if tool_name not in sources:
                                sources.append(tool_name)
                            props["sources"] = sources
                            props["original_locations"] = orig
                            merged[i]["properties"] = props
                            meta["key"] = (uri, winning_line, cwe)
                            meta["original_locations"] = orig
                            found = True
                            break
                    if not found:
                        entry = dict(result)
                        entry_props = dict(entry.get("properties", {}))
                        entry_props["sources"] = [tool_name]
                        entry["properties"] = entry_props
                        merged.append(entry)
                        merge_meta.append({
                            "key": (uri, line, cwe),
                            "original_locations": {tool_name: line},
                        })
                else:
                    # no CWE — never merge, just append
                    entry = dict(result)
                    entry_props = dict(entry.get("properties", {}))
                    entry_props["sources"] = [tool_name]
                    entry["properties"] = entry_props
                    merged.append(entry)
                    merge_meta.append({"key": None, "original_locations": {}})

    # apply sdlc_severity to all results
    merged = [_apply_sdlc_severity(r) for r in merged]

    supported_taxonomies = [_CWE_TAXONOMY_REF] if has_cwe else []

    sarif_run: dict[str, Any] = {
        "tool": {
            "driver": {
                "name": "code-review-aggregator",
                "rules": [],
                "supportedTaxonomies": supported_taxonomies,
            }
        },
        "results": merged,
    }

    doc: dict[str, Any] = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [sarif_run],
    }
    if analyzer_errors:
        doc["properties"] = {"analyzer_errors": analyzer_errors}

    return doc
