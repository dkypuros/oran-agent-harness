"""5G_O-RAN_SIM trace timeline viewer static server.

Conforms to:
  harness-unique presentation layer, no upstream spec
Bibliography refs: n/a

Serves the trace_view/index.html dashboard plus the shared_trace/*.jsonl files
under one HTTP origin so fetch() in the page can read the JSONL relative path.

Run with:
  python 5G_O-RAN_SIM/dashboard/trace_view/serve.py
or override the port:
  TRACE_VIEWER_PORT=9000 python 5G_O-RAN_SIM/dashboard/trace_view/serve.py

Then open http://localhost:8095/dashboard/trace_view/index.html in a browser.
"""

from __future__ import annotations

import http.server
import os
import socketserver
import sys
from pathlib import Path

_SIM_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_PORT = 8095


def main(argv: list[str] | None = None) -> int:
    port = int(os.environ.get("TRACE_VIEWER_PORT", _DEFAULT_PORT))
    os.chdir(_SIM_ROOT)
    handler = http.server.SimpleHTTPRequestHandler

    with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
        print(f"5G_O-RAN_SIM trace viewer serving from {_SIM_ROOT}")
        print(f"open http://localhost:{port}/dashboard/trace_view/index.html")
        print("Ctrl-C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
