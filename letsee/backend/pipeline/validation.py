"""Validation that API findings and links point to exact parsed source messages."""
from .parsing import parse_messages, _extract_links

class EvidenceValidationError(ValueError):
    pass

def validate_analysis_evidence(response: dict, original_text: str) -> None:
    source_by_id={message["id"]: message for message in parse_messages(original_text)}
    categories=response.get("categories")
    if not isinstance(categories, dict) or set(categories) != {"URGENT", "IMPORTANT", "FYI"}:
        raise EvidenceValidationError("Analysis response has invalid priority categories")
    for priority, findings in categories.items():
        if not isinstance(findings, list):
            raise EvidenceValidationError("Analysis category must be a list")
        for finding in findings:
            if finding.get("priority") != priority:
                raise EvidenceValidationError("Finding is in the wrong priority category")
            sources=finding.get("sources")
            if not isinstance(sources, list) or not sources:
                raise EvidenceValidationError("Every finding must include a source message")
            allowed_urls=set()
            for source in sources:
                original=source_by_id.get(source.get("id"))
                if original is None or any(source.get(field) != original.get(field) for field in ("timestamp", "sender", "text")):
                    raise EvidenceValidationError("Finding contains a source that is not in the supplied conversation")
                allowed_urls.update(link["url"] for link in _extract_links(original["text"]))
            for link in finding.get("links", []):
                if link.get("url") not in allowed_urls:
                    raise EvidenceValidationError("Finding contains a URL that is not in its source messages")
