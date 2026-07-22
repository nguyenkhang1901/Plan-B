"""
WSGI entry point for Gunicorn on Render
"""
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the Flask app
from app.app import app

if __name__ == "__main__":
    app.run()
