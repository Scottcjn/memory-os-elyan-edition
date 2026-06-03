"""
Shared YAML frontmatter parser for fabric markdown entries.

Used by fabric-retrieve.py and export-training.py to avoid
duplicate parse_entry implementations (D01, D09).

The primary parser is yaml.safe_load(). A manual fallback handles
malformed YAML — it splits on ": " which can fail on URLs, but
this path is only reached when yaml.safe_load() throws.
"""

import re


def _strip_generated_obsidian_sections(body: str) -> str:
    """Strip Obsidian-generated sections that add noise to extraction."""
    body = re.sub(
        r"(?m)^## Generated LLM Prompts and Descriptions\n\n.*?(?=\n## |\Z)",
        "",
        body,
        flags=re.DOTALL,
    )
    body = re.sub(
        r"(?m)^## Conversation Log\n\n.*?(?=\n## |\Z)",
        "",
        body,
        flags=re.DOTALL,
    )
    return body.strip()


def parse_entry(filepath):
    """Parse a fabric markdown entry into a dict.

    Returns a dict with keys from YAML frontmatter plus:
      - body / _body: cleaned body text (stripped of Obsidian sections)
      - file / _file: filename
      - _full: complete raw file text (for dedup and full-text retrieval)
    
    Both naming conventions are provided for backward compatibility:
    fabric-retrieve.py uses _body/_file, export-training.py uses body/file.
    """
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    meta = {}
    try:
        import yaml
        meta = yaml.safe_load(parts[1]) or {}
    except Exception:
        current_key = None
        for line in parts[1].strip().split("\n"):
            stripped = line.strip()
            if stripped.startswith("- ") and current_key:
                if not isinstance(meta.get(current_key), list):
                    meta[current_key] = []
                meta[current_key].append(stripped[2:].strip().strip("\"'"))
            elif ": " in stripped and not stripped.startswith("-"):
                k, v = stripped.split(": ", 1)
                k = k.strip()
                current_key = k
                if v.startswith("[") and v.endswith("]"):
                    meta[k] = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
                elif v.strip():
                    meta[k] = v.strip()
                else:
                    meta[k] = []
            elif stripped.endswith(":") and not stripped.startswith("-"):
                current_key = stripped[:-1].strip()
                meta[current_key] = []
    body_text = _strip_generated_obsidian_sections(parts[2])
    # Provide both naming conventions
    meta["body"] = body_text
    meta["_body"] = body_text
    meta["file"] = filepath.name
    meta["_file"] = filepath.name
    meta["_full"] = text
    return meta
