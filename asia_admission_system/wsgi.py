"""
WSGI entry point for Gunicorn on Render
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

try:
    # Import and run the Flask app
    from app.app import app
    print("[WSGI] Flask app loaded successfully", flush=True)
except Exception as e:
    print(f"[WSGI ERROR] Failed to load Flask app: {e}", flush=True)
    raise

if __name__ == "__main__":
    app.run()
