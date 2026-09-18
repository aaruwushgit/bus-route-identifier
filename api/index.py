import sys
from pathlib import Path

# Add project root directory to sys.path so modules (config, routes, etc.) are found
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from urllib.parse import parse_qs, urlencode, unquote
try:
    from web_app import app
except Exception as e:
    import traceback
    _init_err = traceback.format_exc()
    from flask import Flask, jsonify
    app = Flask(__name__)
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def emergency_error(path):
        return jsonify({"error": "Vercel Startup Error", "traceback": _init_err}), 500


class VercelPathFix:
    """
    WSGI middleware ensuring proper URL routing on Vercel serverless deployments.
    Extracts the original client requested path from query parameter __path__,
    Vercel headers, or PATH_INFO, and cleans up environ so Flask routes correctly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get("QUERY_STRING", "")
        qs = parse_qs(query_string, keep_blank_values=True)

        target = None

        # 1. Check explicit __path__ parameter injected by vercel.json rewrite
        if "__path__" in qs and qs["__path__"]:
            raw = qs.pop("__path__")[0]
            if raw and raw not in ("/api/index", "/api/index.py"):
                target = raw
            # Clean up QUERY_STRING so Flask and endpoints don't receive internal __path__
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
        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathFix(app.wsgi_app)
