from app import app

if __name__ == "__main__":
    # Bind to 0.0.0.0 for container environments and use PORT if provided
    import os
    port = int(os.getenv("PORT", "3001"))
    app.run(host="0.0.0.0", port=port)
