from flask import Blueprint, request, jsonify
from backend.models.task import TaskModel

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@tasks_bp.route('/today', methods=['GET'])
def get_today_tasks():
    user_id = request.args.get('user_id', 1, type=int)
    tasks = TaskModel.get_tasks_for_today(user_id)
    return jsonify({"success": True, "tasks": tasks, "count": len(tasks)})

@tasks_bp.route('/<date_str>', methods=['GET'])
def get_tasks_by_date(date_str):
    user_id = request.args.get('user_id', 1, type=int)
    if date_str.isdigit():
        task = TaskModel.get_task_by_id(int(date_str), user_id)
        if task:
            return jsonify({"success": True, "task": task})
        return jsonify({"success": False, "error": "Task not found"}), 404

    tasks = TaskModel.get_tasks_by_date(user_id, date_str)
    return jsonify({"success": True, "date": date_str, "tasks": tasks, "count": len(tasks)})

@tasks_bp.route('', methods=['POST'])
def add_task():
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({"success": False, "error": "Task title is required"}), 400

    user_id = data.get('user_id', 1)
    notes = data.get('notes', '')
    priority = data.get('priority', 'medium').lower()
    deadline = data.get('deadline')
    original_date = data.get('original_date')
    subtasks = data.get('subtasks')

    task = TaskModel.create_task(
        user_id=user_id,
        title=title,
        notes=notes,
        priority=priority,
        deadline=deadline,
        original_date=original_date,
        subtasks=subtasks
    )
    return jsonify({"success": True, "task": task, "message": "Task created successfully"}), 201

@tasks_bp.route('/<int:task_id>', methods=['PUT'])
def edit_task(task_id):
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({"success": False, "error": "Task title is required"}), 400

    user_id = data.get('user_id', 1)
    notes = data.get('notes', '')
    priority = data.get('priority', 'medium').lower()
    deadline = data.get('deadline')
    subtasks = data.get('subtasks')

    task = TaskModel.update_task(
        task_id=task_id,
        user_id=user_id,
        title=title,
        notes=notes,
        priority=priority,
        deadline=deadline,
        subtasks=subtasks
    )
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404

    return jsonify({"success": True, "task": task, "message": "Task updated successfully"})

@tasks_bp.route('/subtasks/<int:subtask_id>', methods=['PATCH', 'PUT'])
def update_subtask_route(subtask_id):
    data = request.get_json(silent=True) or {}
    is_done = data.get('is_done')
    subtask = TaskModel.toggle_subtask(subtask_id, is_done=is_done)
    if not subtask:
        return jsonify({"success": False, "error": "Subtask not found"}), 404
    return jsonify({"success": True, "subtask": subtask, "message": "Subtask updated successfully"})

@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    user_id = request.args.get('user_id', 1, type=int)
    success = TaskModel.delete_task(task_id, user_id)
    if not success:
        return jsonify({"success": False, "error": "Task not found"}), 404

    return jsonify({"success": True, "message": "Task deleted successfully"})

@tasks_bp.route('/<int:task_id>/complete', methods=['PUT'])
def complete_task(task_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 1)
    result = TaskModel.toggle_complete(task_id, user_id)
    if not result:
        return jsonify({"success": False, "error": "Task not found"}), 404

    return jsonify({
        "success": True,
        "result": result,
        "message": f"Task marked as {result['status']}"
    })

@tasks_bp.route('/<int:task_id>/logs', methods=['GET'])
def get_task_logs(task_id):
    user_id = request.args.get('user_id', 1, type=int)
    logs = TaskModel.get_task_logs(task_id, user_id)
    return jsonify({"success": True, "task_id": task_id, "logs": logs, "count": len(logs)})

@tasks_bp.route('/rollover', methods=['POST'])
def auto_rollover():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 1)
    result = TaskModel.rollover_tasks(user_id)
    return jsonify({
        "success": True,
        "rollover": result,
        "message": f"Rolled over {result['rolled_count']} incomplete tasks to today"
    })

@tasks_bp.route('/missed', methods=['GET'])
def get_missed_tasks():
    user_id = request.args.get('user_id', 1, type=int)
    missed_tasks = TaskModel.get_missed_tasks(user_id)
    return jsonify({"success": True, "tasks": missed_tasks, "count": len(missed_tasks)})
