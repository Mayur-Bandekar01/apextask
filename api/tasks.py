from flask import Blueprint, request, jsonify, g

try:
    from api.models.task import TaskModel
    from api.auth import require_auth
except ImportError:
    from models.task import TaskModel
    from auth import require_auth

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@tasks_bp.route('/today', methods=['GET'])
@require_auth
def get_today_tasks():
    user_id = getattr(g, 'user_id', 1)
    tasks = TaskModel.get_tasks_for_today(user_id)
    return jsonify({"success": True, "tasks": tasks, "count": len(tasks)})

@tasks_bp.route('/<date_str>', methods=['GET'])
@require_auth
def get_tasks_by_date(date_str):
    user_id = getattr(g, 'user_id', 1)
    if date_str.isdigit():
        task = TaskModel.get_task_by_id(int(date_str), user_id)
        if task:
            return jsonify({"success": True, "task": task})
        return jsonify({"success": False, "error": "Task not found"}), 404

    tasks = TaskModel.get_tasks_by_date(user_id, date_str)
    return jsonify({"success": True, "date": date_str, "tasks": tasks, "count": len(tasks)})

@tasks_bp.route('', methods=['POST'])
@require_auth
def add_task():
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({"success": False, "error": "Task title is required"}), 400

    user_id = getattr(g, 'user_id', 1)
    notes = data.get('notes', '')
    priority = data.get('priority', 'medium').lower()
    deadline = data.get('deadline')
    original_date = data.get('original_date')

    task = TaskModel.create_task(
        user_id=user_id,
        title=title,
        notes=notes,
        priority=priority,
        deadline=deadline,
        original_date=original_date
    )
    return jsonify({"success": True, "task": task, "message": "Task created successfully"}), 201

@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@require_auth
def edit_task(task_id):
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({"success": False, "error": "Task title is required"}), 400

    user_id = getattr(g, 'user_id', 1)
    notes = data.get('notes', '')
    priority = data.get('priority', 'medium').lower()
    deadline = data.get('deadline')

    task = TaskModel.update_task(
        task_id=task_id,
        user_id=user_id,
        title=title,
        notes=notes,
        priority=priority,
        deadline=deadline
    )
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404

    return jsonify({"success": True, "task": task, "message": "Task updated successfully"})

@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@require_auth
def delete_task(task_id):
    user_id = getattr(g, 'user_id', 1)
    success = TaskModel.delete_task(task_id, user_id)
    if not success:
        return jsonify({"success": False, "error": "Task not found"}), 404

    return jsonify({"success": True, "message": "Task deleted successfully"})

@tasks_bp.route('/<int:task_id>/complete', methods=['PUT'])
@require_auth
def complete_task(task_id):
    user_id = getattr(g, 'user_id', 1)
    result = TaskModel.toggle_complete(task_id, user_id)
    if not result:
        return jsonify({"success": False, "error": "Task not found"}), 404

    return jsonify({
        "success": True,
        "result": result,
        "message": f"Task marked as {result['status']}"
    })

@tasks_bp.route('/<int:task_id>/logs', methods=['GET'])
@require_auth
def get_task_logs(task_id):
    user_id = getattr(g, 'user_id', 1)
    logs = TaskModel.get_task_logs(task_id, user_id)
    return jsonify({"success": True, "task_id": task_id, "logs": logs, "count": len(logs)})

@tasks_bp.route('/rollover', methods=['POST'])
@require_auth
def auto_rollover():
    user_id = getattr(g, 'user_id', 1)
    result = TaskModel.rollover_tasks(user_id)
    return jsonify({
        "success": True,
        "rollover": result,
        "message": f"Rolled over {result['rolled_count']} incomplete tasks to today"
    })

@tasks_bp.route('/missed', methods=['GET'])
@require_auth
def get_missed_tasks():
    user_id = getattr(g, 'user_id', 1)
    missed_tasks = TaskModel.get_missed_tasks(user_id)
    return jsonify({"success": True, "tasks": missed_tasks, "count": len(missed_tasks)})
