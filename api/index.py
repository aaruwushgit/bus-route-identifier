import sys
from pathlib import Path

# Add project root directory to sys.path so modules (config, routes, etc.) are found
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import os
import traceback
from urllib.parse import parse_qs, urlencode, unquote

# Cached references
_flask_app = None
_init_error = None


def _get_flask_app():
    global _flask_app, _init_error
    if _flask_app is None and _init_error is None:
        try:
            from web_app import app as fa
            _flask_app = fa
        except Exception:
            _init_error = traceback.format_exc()
    return _flask_app, _init_error


def app(environ, start_response):
    """
    Standard WSGI entrypoint for Vercel Serverless Functions.
    Catches all import or runtime initialization errors and returns
    actionable diagnostics instead of silent FUNCTION_INVOCATION_FAILED errors.
    """
    query_string = environ.get("QUERY_STRING", "")
    qs = parse_qs(query_string, keep_blank_values=True)

    flask_instance, init_err = _get_flask_app()
    if init_err:
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
        return [("VERCEL INITIALIZATION ERROR:\n\n" + init_err).encode("utf-8")]

    target = None

    # 1. Check explicit __path__ parameter injected by vercel.json rewrite
    if "__path__" in qs and qs["__path__"]:
        raw = qs.pop("__path__")[0]
        if raw and raw not in ("/api/index", "/api/index.py"):
            target = raw
        environ["QUERY_STRING"] = urlencode(qs, doseq=True)

    # 2. Check x-now-route-matches if available
    if not target or target in ("/api/index", "/api/index.py"):
        route_matches = environ.get("HTTP_X_NOW_ROUTE_MATCHES", "")
        if route_matches:
            rm_qs = parse_qs(route_matches)
            for k in ("1", "0", "path"):
                if k in rm_qs and rm_qs[k]:
                    val = unquote(rm_qs[k][0])
                    if val and not val.startswith(("/api/index", "/api/index.py")):
                        target = "/" + val.lstrip("/")
                        break

    # 3. Check HTTP_X_FORWARDED_URI or HTTP_X_MATCHED_PATH
    if not target or target in ("/api/index", "/api/index.py"):
        forwarded = (environ.get("HTTP_X_FORWARDED_URI") or "").split("?")[0]
        matched = (environ.get("HTTP_X_MATCHED_PATH") or "").split("?")[0]
        if forwarded and not forwarded.startswith(("/api/index", "/api/index.py")):
            target = forwarded
        elif matched and not matched.startswith(("/api/index", "/api/index.py")):
            target = matched

    # 4. Fallback: normalize entrypoint itself or root-like paths to /
    path_info = (environ.get("PATH_INFO") or "").split("?")[0]
    if not target:
        if path_info in ("/api/index", "/api/index.py", "/api/index/", "/api/index.py/"):
            target = "/"
        else:
            target = path_info

    if not target.startswith("/"):
        target = "/" + target

    environ["PATH_INFO"] = target

    try:
        return flask_instance(environ, start_response)
    except Exception:
        err = traceback.format_exc()
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
        return [("VERCEL DISPATCH ERROR:\n\n" + err).encode("utf-8")]
