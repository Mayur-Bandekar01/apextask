import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

from backend.config import Config
from backend.db import init_db, get_engine_name
from backend.routes.tasks import tasks_bp
from backend.routes.records import records_bp
from backend.routes.gamification import gamification_bp

# Define frontend static directory
frontend_dir = root_dir / 'frontend'

app = Flask(__name__, static_folder=str(frontend_dir), static_url_path='')
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app)

# Register Blueprints
app.register_blueprint(tasks_bp)
app.register_blueprint(records_bp)
app.register_blueprint(gamification_bp)

@app.after_request
def add_keep_alive_headers(response):
    response.headers['Connection'] = 'keep-alive'
    response.headers['Keep-Alive'] = 'timeout=5, max=100'
    return response

@app.route('/api/subtasks/<int:subtask_id>', methods=['PATCH', 'PUT'])
def api_subtasks_patch(subtask_id):
    from backend.models.task import TaskModel
    data = request.get_json(silent=True) or {}
    is_done = data.get('is_done')
    subtask = TaskModel.toggle_subtask(subtask_id, is_done=is_done)
    if not subtask:
        return jsonify({"success": False, "error": "Subtask not found"}), 404
    return jsonify({"success": True, "subtask": subtask, "message": "Subtask updated successfully"})

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    if path.startswith('api/'):
        return jsonify({"success": False, "error": f"API endpoint not found: /{path}"}), 404
    file_path = Path(app.static_folder) / path
    if file_path.exists() and file_path.is_file():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "Ultimate To-Do API",
        "database_engine": get_engine_name()
    })

# Global error handlers for JSON responses
@app.errorhandler(400)
def bad_request(e):
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "Bad request format"}), 400
    return e

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

def create_app():
    init_db()
    return app

if __name__ == '__main__':
    create_app()
    port = Config.PORT
    print(f"[SERVER] Ultimate To-Do List Server running on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=False)
