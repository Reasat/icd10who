"""Render a Jinja2 template with YAML or JSON data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jinja2 import Template


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: render_template.py <template.j2> <data.yml|json> <output>")

    template_path, data_path, output_path = sys.argv[1:4]
    template = Template(Path(template_path).read_text())
    data_file = Path(data_path)

    if data_file.suffix in {".yml", ".yaml"}:
        context = yaml.safe_load(data_file.read_text()) or {}
        rendered = template.render(**context)
    else:
        payload = json.loads(data_file.read_text())
        rendered = template.render(metrics=payload)

    Path(output_path).write_text(rendered)


if __name__ == "__main__":
    main()
