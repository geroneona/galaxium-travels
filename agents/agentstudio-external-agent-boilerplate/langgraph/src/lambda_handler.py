try:
    from mangum import Mangum  # type: ignore
except ImportError:  # pragma: no cover - optional runtime dependency
    Mangum = None  # type: ignore

# Import the ASGI app created in main.py
try:
    # main.py exposes `app` at module level
    from .main import app  # type: ignore
except Exception:
    # fallback absolute import for execution from package root
    from src.main import app  # type: ignore

# Create a Mangum handler for AWS Lambda if available
handler = Mangum(app) if Mangum is not None else None
