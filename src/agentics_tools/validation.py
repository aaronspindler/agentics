"""Validate packaged references without requiring a particular repository layout."""

from __future__ import annotations

import posixpath
import re
from urllib.parse import unquote, urlsplit

from .catalog import Catalog


def validate(catalog: Catalog):
    errors = []
    for key in catalog.items:
        bundle = catalog.bundle(key)
        for name, (contents, _) in bundle.items():
            if not name.endswith(".md"):
                continue
            text = contents.decode()
            for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
                target = match.group(1).split(" ", 1)[0].strip("<>")
                parts = urlsplit(target)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parts.path)))
                if resolved not in bundle and not any(p.startswith(resolved + "/") for p in bundle):
                    errors.append(f"{key}/{name}: missing bundled link {target}")
        if key.startswith("agent:"):
            import tomllib
            data = tomllib.loads(next(iter(bundle.values()))[0].decode())
            if "model" in data or "model_reasoning_effort" in data:
                errors.append(f"{key}: shared agents must inherit model settings")
    if errors:
        raise ValueError("\n".join(errors))
