#!/usr/bin/env python3
"""PostToolUse hook: run the offline bib sync after Claude edits a .tex or .bib file.

Silent outside acl-paper projects and when nothing needs reporting. Never
fails the tool call: errors are reported to Claude as context instead.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paperkit import config, sync  # noqa: E402


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if Path(file_path).suffix not in {".tex", ".bib"}:
        return
    root = config.find_root(Path(file_path).parent if file_path else payload.get("cwd"))
    if root is None:
        return
    try:
        messages = sync.run(root, config.load(root)).messages()
    except Exception as exc:  # report, never block the edit
        messages = [f"⚠️ acl-paper bib sync failed: {exc}"]
    if messages:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n".join(messages),
            }
        }))


if __name__ == "__main__":
    main()
