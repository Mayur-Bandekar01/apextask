import os
import sys
from pathlib import Path

# Ensure root directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

from api.config import Config
from api.db import init_db, get_engine_name
from api.auth import auth_bp
from api.tasks import tasks_bp
from api.records import records_bp
from api.gamification import gamification_bp

# Define frontend static directory
frontend_dir = root_dir / 'frontend'

def create_app():
    app = Flask(__name__, static_folder=str(frontend_dir), static_url_path='')
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    CORS(app)

    # Initialize Database Schema & default user
    try:
        init_db()
    except Exception as e:
        print(f"[INIT DB WARNING] {e}")

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(gamification_bp)

    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/app')
    def main_app():
        return send_from_directory(app.static_folder, 'app.html')

    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({
            "status": "healthy",
            "service": "Ultimate To-Do Vercel Serverless API",
            "auth_user": Config.APP_USERNAME,
            "database_engine": get_engine_name()
        })

    # Serve static assets for local dev
    @app.route('/<path:path>')
    def static_files(path):
        if path.startswith('api/'):
            return jsonify({"success": False, "error": f"API endpoint not found: /{path}"}), 404
        file_path = Path(app.static_folder) / path
        if file_path.exists() and file_path.is_file():
            return send_from_directory(app.static_folder, path)
        if path == 'app':
            return send_from_directory(app.static_folder, 'app.html')
        return send_from_directory(app.static_folder, 'index.html')

    # Global error handlers
    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith('/api/'):
            return jsonify({"success": False, "error": "Bad request format"}), 400
        return e

    @app.errorhandler(401)
    def unauthorized(e):
        if request.path.startswith('/api/'):
            return jsonify({"success": False, "error": "Unauthorized or session expired"}), 401
        return send_from_directory(app.static_folder, 'index.html')

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({"success": False, "error": f"Route not found: {request.path}"}), 404
        return send_from_directory(app.static_folder, 'index.html')

    @app.errorhandler(500)
    def server_error(e):
        if request.path.startswith('/api/'):
            return jsonify({"success": False, "error": "Internal server error"}), 500
        return e

    return app

# Vercel entry point
app = create_app()

if __name__ == '__main__':
    port = Config.PORT
    print(f"[SERVER] Ultimate To-Do App running on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=False)
