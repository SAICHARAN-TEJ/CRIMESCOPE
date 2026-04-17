"""CrimeScope backend Flask application factory."""

import os
import warnings

# Suppress multiprocessing resource_tracker warnings from third-party libs.
# This should be set before other imports.
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request

try:
    from flask_cors import CORS
except Exception:  # pragma: no cover - optional dependency fallback
    CORS = None

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configure JSON encoding and keep non-ASCII characters readable.
    # Use config key to avoid relying on provider-specific attributes.
    app.config['JSON_AS_ASCII'] = False
    
    # Set up logging.
    logger = setup_logger('crimescope')
    
    # Only print startup logs in the reloader child process in debug mode.
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("CrimeScope Backend Starting...")
        logger.info("=" * 50)
    
    # Enable CORS when flask-cors is available.
    if CORS is not None:
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    elif should_log_startup:
        logger.warning("flask-cors is not installed; CORS middleware is disabled")
    
    # Register simulation cleanup only when runner dependencies are available.
    try:
        from .services.simulation_runner import SimulationRunner

        SimulationRunner.register_cleanup()
        if should_log_startup:
            logger.info("Registered simulation process cleanup function")
    except Exception as exc:  # pragma: no cover - dependency/env dependent
        if should_log_startup:
            logger.warning("Simulation cleanup registration skipped: %s", exc)
    
    # Request logging middleware.
    @app.before_request
    def log_request():
        logger = get_logger('crimescope.request')
        logger.debug(f"request: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"Request body: {request.get_json(silent=True)}")
    
    @app.after_request
    def log_response(response):
        logger = get_logger('crimescope.request')
        logger.debug(f"response: {response.status_code}")
        return response
    
    # Register blueprints.
    from .api import graph_bp, simulation_bp, report_bp, crimescope_bp, system_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(crimescope_bp, url_prefix='/api/crimescope')
    app.register_blueprint(system_bp, url_prefix='/api/system')
    
    # Health check endpoint.
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'CrimeScope Backend'}
    
    if should_log_startup:
        logger.info("CrimeScope Backend startup completed")
    
    return app

