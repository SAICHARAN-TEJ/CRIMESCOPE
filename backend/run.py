"""CrimeScope backend startup entrypoint."""

import os
import sys

# Ensure UTF-8 console output on Windows.
if sys.platform == 'win32':
    # Set environment variables so Python uses UTF-8.
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    # Reconfigure stdio stream encoding.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root directory to import path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config


def main():
    """Run backend service."""
    # Validate required configuration.
    errors = Config.validate()
    if errors:
        print("Configuration error:")
        for err in errors:
            print(f"  - {err}")
        print("\nPlease check your .env configuration")
        sys.exit(1)
    
    # Create app.
    app = create_app()
    
    # Read runtime configuration.
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = Config.DEBUG
    
    # Start service.
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    main()

