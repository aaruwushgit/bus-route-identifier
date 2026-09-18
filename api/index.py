import sys
from pathlib import Path

# Add project root directory to sys.path so modules (config, routes, etc.) are found
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from web_app import app


class VercelPathFix:
    """
    WSGI middleware ensuring proper URL routing on Vercel serverless deployments.
    Handles rewrites where Vercel sets PATH_INFO to /api/index or /api/index.py,
    or stores the actual client requested URI in HTTP_X_FORWARDED_URI / HTTP_X_MATCHED_PATH.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        forwarded_uri = (environ.get("HTTP_X_FORWARDED_URI") or "").split("?")[0]
        matched_path = (environ.get("HTTP_X_MATCHED_PATH") or "").split("?")[0]
        path_info = (environ.get("PATH_INFO") or "").split("?")[0]

        target = None
        # If client requested a real route (e.g. /api/config, /api/identify, /api/benchmark)
        if forwarded_uri and not forwarded_uri.startswith(("/api/index", "/api/index.py")):
            target = forwarded_uri
        elif matched_path and not matched_path.startswith(("/api/index", "/api/index.py")):
            target = matched_path
        # If PATH_INFO or forwarded path points to the serverless function entrypoint itself, route to root /
        elif path_info in ("/api/index", "/api/index.py", "/api/index/", "/api/index.py/") or forwarded_uri == "/":
            target = "/"

        if target:
            environ["PATH_INFO"] = target

        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathFix(app.wsgi_app)
