import io
import csv
import json
import datetime
from flask import Blueprint, jsonify, request, Response, g

try:
    from api.auth import require_auth
    from api.db import get_db_connection
    from api.models.task import TaskModel
except ImportError:
    from auth import require_auth
    from db import get_db_connection
    from models.task import TaskModel

export_import_bp = Blueprint('export_import', __name__)

@export_import_bp.route('/tasks/export', methods=['GET'])
@require_auth
def export_tasks():
    user_id = getattr(g, 'user_id', 1)
    format_type = request.args.get('format', 'json').lower()
    
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, title, notes, priority, status, original_date, deadline, rollover_count, is_boss, boss_hp, boss_max_hp, tags, created_at
            FROM tasks
            WHERE user_id = %s
            ORDER BY original_date DESC, id DESC;
        """, (user_id,))
        tasks = cur.fetchall()
    conn.close()

    formatted_tasks = []
    for t in tasks:
        item = dict(t)
        if isinstance(item.get('original_date'), (datetime.date, datetime.datetime)):
            item['original_date'] = item['original_date'].strftime('%Y-%m-%d')
        if isinstance(item.get('deadline'), (datetime.date, datetime.datetime)):
            item['deadline'] = item['deadline'].isoformat()
        if isinstance(item.get('created_at'), (datetime.date, datetime.datetime)):
            item['created_at'] = item['created_at'].isoformat()
        formatted_tasks.append(item)

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    if format_type == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Title', 'Notes', 'Priority', 'Status', 'Date', 'Deadline', 'Rollovers', 'Tags', 'IsBoss'])
        for t in formatted_tasks:
            writer.writerow([
                t.get('id', ''),
                t.get('title', ''),
                t.get('notes', ''),
                t.get('priority', 'medium'),
                t.get('status', 'pending'),
                t.get('original_date', ''),
                t.get('deadline', ''),
                t.get('rollover_count', 0),
                t.get('tags', ''),
                1 if t.get('is_boss') else 0
            ])
        
        csv_data = output.getvalue()
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=apextask_export_{timestamp}.csv'}
        )

    # Default JSON Export
    json_data = json.dumps({
        "app": "APEXTASK Ultimate Productivity Suite",
        "exported_at": datetime.datetime.now().isoformat(),
        "total_tasks": len(formatted_tasks),
        "tasks": formatted_tasks
    }, indent=2)

    return Response(
        json_data,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename=apextask_export_{timestamp}.json'}
    )


@export_import_bp.route('/tasks/import', methods=['POST'])
@require_auth
def import_tasks():
    user_id = getattr(g, 'user_id', 1)
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded. Please upload a JSON or CSV file."}), 400

    file = request.files['file']
    filename = file.filename.lower()

    if not (filename.endswith('.json') or filename.endswith('.csv')):
        return jsonify({"success": False, "error": "Unsupported file format. Please upload .json or .csv"}), 400

    imported_count = 0
    today_str = datetime.date.today().isoformat()

    try:
        content = file.read().decode('utf-8')
        tasks_to_insert = []

        if filename.endswith('.json'):
            parsed = json.loads(content)
            task_list = parsed.get('tasks', parsed) if isinstance(parsed, dict) else parsed
            if not isinstance(task_list, list):
                return jsonify({"success": False, "error": "Invalid JSON task format"}), 400

            for t in task_list:
                if not isinstance(t, dict) or not t.get('title'):
                    continue
                tasks_to_insert.append({
                    "title": str(t.get('title')).strip(),
                    "notes": str(t.get('notes', '')),
                    "priority": str(t.get('priority', 'medium')).lower() if str(t.get('priority', '')).lower() in ('low', 'medium', 'high') else 'medium',
                    "original_date": str(t.get('original_date', today_str))[:10],
                    "deadline": t.get('deadline'),
                    "tags": str(t.get('tags', ''))
                })

        elif filename.endswith('.csv'):
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                title = row.get('Title') or row.get('title') or row.get('TITLE')
                if not title:
                    continue
                notes = row.get('Notes') or row.get('notes') or ''
                priority = (row.get('Priority') or row.get('priority') or 'medium').lower()
                date_val = row.get('Date') or row.get('date') or today_str
                tags = row.get('Tags') or row.get('tags') or ''

                tasks_to_insert.append({
                    "title": title.strip(),
                    "notes": notes,
                    "priority": priority if priority in ('low', 'medium', 'high') else 'medium',
                    "original_date": date_val[:10],
                    "deadline": None,
                    "tags": tags
                })

        conn = get_db_connection()
        with conn.cursor() as cur:
            for task in tasks_to_insert:
                cur.execute("""
                    INSERT INTO tasks (user_id, title, notes, priority, status, original_date, tags, rollover_count)
                    VALUES (%s, %s, %s, %s, 'pending', %s, %s, 0);
                """, (user_id, task['title'], task['notes'], task['priority'], task['original_date'], task['tags']))
                imported_count += 1

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "imported_count": imported_count,
            "message": f"Successfully imported {imported_count} tasks into your workspace!"
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to parse or import tasks: {str(e)}"}), 500
