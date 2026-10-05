"""Point d'entrée `python -m remporte`."""

from __future__ import annotations

import sys

from remporte.cli import main

if __name__ == "__main__":
    sys.exit(main())
