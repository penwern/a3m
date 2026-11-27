"""Generate preview data: python -m a3m.fpr [--source path] [--output path]."""

import argparse
import json
from pathlib import Path

from a3m.fpr.registry import FPR
from a3m.fpr.registry import JSONBackend
from a3m.fpr.serialization import registry_json
from a3m.fpr.serialization import registry_response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, help="Use a fixture instead of the bundled FPR"
    )
    parser.add_argument(
        "--output", type=Path, help="Write JSON to a file instead of stdout"
    )
    args = parser.parse_args()
    backend = JSONBackend(args.source.read_bytes()) if args.source else FPR.backend
    if not isinstance(backend, JSONBackend):
        parser.error("Registry export currently requires a JSON backend")
    content = (
        json.dumps(
            registry_json(registry_response(backend)),
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    if args.output:
        args.output.write_text(content, encoding="utf-8", newline="\n")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
