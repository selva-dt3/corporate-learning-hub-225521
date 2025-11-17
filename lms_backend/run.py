from app import create_app

if __name__ == "__main__":
    """
    Development runner.

    Binds to 0.0.0.0 and uses PORT or FLASK_RUN_PORT env var if provided (default 3001).
    In containerized environments, ensure only one instance binds to the same port.
    Prefer a WSGI server (e.g., gunicorn) in production, using wsgi:application.

    Note: Kavia preview expects backend at 3001; default accordingly.
    """
    import os

    # Prefer PORT, then FLASK_RUN_PORT, default to 3001
    port = int(os.getenv("PORT") or os.getenv("FLASK_RUN_PORT") or "3001")
    app = create_app()
    # Explicit bind for dev to ensure 0.0.0.0:3001
    app.run(host="0.0.0.0", port=port)
