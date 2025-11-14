from app import create_app

if __name__ == "__main__":
    """
    Development runner.

    Binds to 0.0.0.0 and uses PORT env var if provided (default 3011).
    In containerized environments, ensure only one instance binds to the same port.
    Prefer a WSGI server (e.g., gunicorn) in production, using wsgi:application.

    Note: Preview environments may run the service on port 3001 externally even if internal default is 3011.
    """
    import os

    port = int(os.getenv("PORT", "3011"))
    app = create_app()
    app.run(host="0.0.0.0", port=port)
