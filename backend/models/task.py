import datetime
from backend.db import get_db_connection
from backend.models.user import UserModel
from backend.models.badge import BadgeModel

XP_MAP = {
    'low': 10,
    'medium': 25,
    'high': 50
}

PENALTY_MAP = {
    'low': -5,
    'medium': -15,
    'high': -30
}

class TaskModel:
    @staticmethod
    def _get_subtasks(cur, task_id):
        cur.execute("SELECT id, task_id, title, is_done, order_index FROM subtasks WHERE task_id = %s ORDER BY order_index ASC, id ASC;", (task_id,))
        rows = cur.fetchall() or []
        subtasks = []
        for r in rows:
            subtasks.append({
                "id": r["id"],
                "task_id": r["task_id"],
                "title": r["title"],
                "is_done": bool(r.get("is_done", 0)),
                "order_index": r.get("order_index", 0)
            })
        return subtasks

    @staticmethod
    def get_tasks_for_today(user_id=1):
        today = datetime.date.today().isoformat()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM tasks 
                WHERE user_id = %s AND (original_date = %s OR (status = 'pending' AND rollover_count > 0))
                ORDER BY 
                    CASE status WHEN 'pending' THEN 1 WHEN 'complete' THEN 2 ELSE 3 END,
                    CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                    deadline ASC,
                    id DESC;
            """, (user_id, today))
            tasks = cur.fetchall()

            for t in tasks:
                orig_date = str(t.get("original_date") or "")
                if orig_date:
                    try:
                        d_orig = datetime.datetime.strptime(orig_date[:10], "%Y-%m-%d").date()
                        t["days_pending"] = max(0, (datetime.date.today() - d_orig).days)
                    except Exception:
                        t["days_pending"] = t.get("rollover_count", 0)
                else:
                    t["days_pending"] = t.get("rollover_count", 0)

                if t.get("deadline"):
                    t["deadline_str"] = str(t["deadline"])
                else:
                    t["deadline_str"] = None

                cur.execute("SELECT COUNT(*) as log_count FROM task_logs WHERE task_id = %s;", (t["id"],))
                lc = cur.fetchone()
                t["log_count"] = lc.get("log_count", 0) if lc else 0
                t["subtasks"] = TaskModel._get_subtasks(cur, t["id"])

        conn.close()
        return tasks

    @staticmethod
    def get_tasks_by_date(user_id, date_str):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM tasks 
                WHERE user_id = %s AND original_date = %s
                ORDER BY 
                    CASE status WHEN 'pending' THEN 1 WHEN 'complete' THEN 2 ELSE 3 END,
                    CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                    id DESC;
            """, (user_id, date_str))
            tasks = cur.fetchall()

            for t in tasks:
                orig_date = str(t.get("original_date") or "")
                if orig_date:
                    try:
                        d_orig = datetime.datetime.strptime(orig_date[:10], "%Y-%m-%d").date()
                        d_target = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                        t["days_pending"] = max(0, (d_target - d_orig).days)
                    except Exception:
                        t["days_pending"] = t.get("rollover_count", 0)
                else:
                    t["days_pending"] = t.get("rollover_count", 0)

                if t.get("deadline"):
                    t["deadline_str"] = str(t["deadline"])
                else:
                    t["deadline_str"] = None

                cur.execute("SELECT COUNT(*) as log_count FROM task_logs WHERE task_id = %s;", (t["id"],))
                lc = cur.fetchone()
                t["log_count"] = lc.get("log_count", 0) if lc else 0
                t["subtasks"] = TaskModel._get_subtasks(cur, t["id"])

        conn.close()
        return tasks

    @staticmethod
    def create_task(user_id, title, notes="", priority="medium", deadline=None, original_date=None, subtasks=None):
        if not original_date:
            original_date = datetime.date.today().isoformat()
        if priority not in ['low', 'medium', 'high']:
            priority = 'medium'

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tasks (user_id, title, notes, priority, status, original_date, deadline, rollover_count)
                VALUES (%s, %s, %s, %s, 'pending', %s, %s, 0);
            """, (user_id, title, notes, priority, original_date, deadline or None))
            task_id = cur.lastrowid

            if subtasks and isinstance(subtasks, list):
                for idx, st in enumerate(subtasks):
                    st_title = (st.get('title') or '').strip() if isinstance(st, dict) else str(st).strip()
                    if st_title:
                        is_done = 1 if (isinstance(st, dict) and st.get('is_done')) else 0
                        order_idx = st.get('order_index', idx) if isinstance(st, dict) else idx
                        cur.execute("""
                            INSERT INTO subtasks (task_id, title, is_done, order_index)
                            VALUES (%s, %s, %s, %s);
                        """, (task_id, st_title, is_done, order_idx))

            cur.execute("""
                INSERT INTO task_logs (task_id, change_description)
                VALUES (%s, %s);
            """, (task_id, f"Created task with {priority.upper()} priority (Target: {original_date})"))

            if hasattr(conn, 'commit'):
                conn.commit()

        conn.close()
        return TaskModel.get_task_by_id(task_id, user_id)

    @staticmethod
    def get_task_by_id(task_id, user_id=1):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks WHERE id = %s AND user_id = %s;", (task_id, user_id))
            task = cur.fetchone()
            if task:
                if task.get("deadline"):
                    task["deadline_str"] = str(task["deadline"])
                task["subtasks"] = TaskModel._get_subtasks(cur, task["id"])
        conn.close()
        return task

    @staticmethod
    def update_task(task_id, user_id, title, notes, priority, deadline, subtasks=None):
        existing = TaskModel.get_task_by_id(task_id, user_id)
        if not existing:
            return None

        changes = []
        if existing["title"] != title:
            changes.append(f"Title changed to '{title}'")
        if (existing["priority"] or "").lower() != priority.lower():
            changes.append(f"Priority changed from {existing.get('priority')} to {priority}")
        if (existing.get("notes") or "") != (notes or ""):
            changes.append("Notes updated")
        if str(existing.get("deadline") or "") != str(deadline or ""):
            changes.append(f"Deadline set to {deadline or 'None'}")

        if not changes:
            changes.append("Task details refreshed")

        change_log_str = "; ".join(changes)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks 
                SET title = %s, notes = %s, priority = %s, deadline = %s
                WHERE id = %s AND user_id = %s;
            """, (title, notes, priority, deadline or None, task_id, user_id))

            if subtasks is not None and isinstance(subtasks, list):
                cur.execute("DELETE FROM subtasks WHERE task_id = %s;", (task_id,))
                for idx, st in enumerate(subtasks):
                    st_title = (st.get('title') or '').strip() if isinstance(st, dict) else str(st).strip()
                    if st_title:
                        is_done = 1 if (isinstance(st, dict) and st.get('is_done')) else 0
                        order_idx = st.get('order_index', idx) if isinstance(st, dict) else idx
                        cur.execute("""
                            INSERT INTO subtasks (task_id, title, is_done, order_index)
                            VALUES (%s, %s, %s, %s);
                        """, (task_id, st_title, is_done, order_idx))

            cur.execute("""
                INSERT INTO task_logs (task_id, change_description)
                VALUES (%s, %s);
            """, (task_id, change_log_str))

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        return TaskModel.get_task_by_id(task_id, user_id)

    @staticmethod
    def toggle_subtask(subtask_id, is_done=None):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM subtasks WHERE id = %s;", (subtask_id,))
            st = cur.fetchone()
            if not st:
                conn.close()
                return None

            if is_done is None:
                new_done = 0 if st.get("is_done") else 1
            else:
                new_done = 1 if is_done else 0

            cur.execute("UPDATE subtasks SET is_done = %s WHERE id = %s;", (new_done, subtask_id))
            if hasattr(conn, 'commit'):
                conn.commit()

            cur.execute("SELECT id, task_id, title, is_done, order_index FROM subtasks WHERE id = %s;", (subtask_id,))
            updated = cur.fetchone()
            if updated:
                updated["is_done"] = bool(updated.get("is_done"))
        conn.close()
        return updated

    @staticmethod
    def delete_task(task_id, user_id=1):
        task = TaskModel.get_task_by_id(task_id, user_id)
        if not task:
            return False

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM task_logs WHERE task_id = %s;", (task_id,))
            cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s;", (task_id, user_id))
            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()
        return True

    @staticmethod
    def toggle_complete(task_id, user_id=1):
        task = TaskModel.get_task_by_id(task_id, user_id)
        if not task:
            return None

        current_status = task.get("status", "pending")
        new_status = "complete" if current_status != "complete" else "pending"
        priority = (task.get("priority") or "medium").lower()
        base_xp = XP_MAP.get(priority, 25)

        xp_delta = base_xp if new_status == "complete" else -base_xp
        today = datetime.date.today().isoformat()
        orig_date = str(task.get("original_date") or today)[:10]

        conn = get_db_connection()
        today_completed_count = 0
        with conn.cursor() as cur:
            cur.execute("UPDATE tasks SET status = %s WHERE id = %s AND user_id = %s;", (new_status, task_id, user_id))

            action_desc = f"Marked as {new_status.upper()} ({'+' if xp_delta > 0 else ''}{xp_delta} XP)"
            cur.execute("INSERT INTO task_logs (task_id, change_description) VALUES (%s, %s);", (task_id, action_desc))

            # Upsert daily record cleanly
            cur.execute("SELECT id, tasks_completed, xp_earned FROM daily_records WHERE user_id = %s AND record_date = %s;", (user_id, orig_date))
            rec = cur.fetchone()
            if rec:
                new_c = max(0, (rec.get("tasks_completed") or 0) + (1 if new_status == "complete" else -1))
                new_xp = max(0, (rec.get("xp_earned") or 0) + xp_delta)
                cur.execute("UPDATE daily_records SET tasks_completed = %s, xp_earned = %s WHERE id = %s;", (new_c, new_xp, rec["id"]))
            else:
                cur.execute("""
                    INSERT INTO daily_records (user_id, record_date, tasks_completed, tasks_missed, xp_earned, focus_time)
                    VALUES (%s, %s, %s, 0, %s, 25);
                """, (user_id, orig_date, 1 if new_status == "complete" else 0, max(0, xp_delta)))

            cur.execute("SELECT COUNT(*) as completed_today FROM tasks WHERE user_id = %s AND status = 'complete' AND original_date = %s;", (user_id, today))
            row = cur.fetchone()
            today_completed_count = row.get("completed_today", 0) if row else 1

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        xp_result = UserModel.modify_xp(user_id, xp_delta, reason=f"Task: {task['title']}")
        streak_gained, streak_lost, current_streak = UserModel.check_and_update_streak(user_id)

        new_badges = []
        if new_status == "complete":
            new_badges = BadgeModel.evaluate_task_completion_badges(user_id, task, today_completed_count, current_streak)

        updated_task = TaskModel.get_task_by_id(task_id, user_id)
        user_profile = UserModel.get_profile(user_id)

        return {
            "task": updated_task,
            "status": new_status,
            "xp_delta": xp_delta,
            "xp_result": xp_result,
            "new_badges": new_badges,
            "streak_gained": streak_gained,
            "streak_lost": streak_lost,
            "current_streak": current_streak,
            "profile": user_profile
        }

    @staticmethod
    def rollover_tasks(user_id=1):
        today = datetime.date.today().isoformat()
        conn = get_db_connection()
        rolled_tasks = []

        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, rollover_count, original_date, priority FROM tasks
                WHERE user_id = %s AND status = 'pending' AND original_date < %s;
            """, (user_id, today))
            to_roll = cur.fetchall()

            for t in to_roll:
                new_count = (t.get("rollover_count") or 0) + 1
                cur.execute("""
                    UPDATE tasks 
                    SET rollover_count = %s 
                    WHERE id = %s;
                """, (new_count, t["id"]))

                cur.execute("""
                    INSERT INTO task_logs (task_id, change_description)
                    VALUES (%s, %s);
                """, (t["id"], f"🔁 Auto-rolled over to {today} (Rollover #{new_count})"))

                rolled_tasks.append(t["id"])

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        return {
            "rolled_count": len(rolled_tasks),
            "rolled_task_ids": rolled_tasks,
            "today": today
        }

    @staticmethod
    def get_task_logs(task_id, user_id=1):
        task = TaskModel.get_task_by_id(task_id, user_id)
        if not task:
            return []

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, task_id, change_description, changed_at 
                FROM task_logs 
                WHERE task_id = %s 
                ORDER BY changed_at DESC, id DESC;
            """, (task_id,))
            logs = cur.fetchall()
            for l in logs:
                l["changed_at_str"] = str(l.get("changed_at") or "")
        conn.close()
        return logs

    @staticmethod
    def get_missed_tasks(user_id=1):
        today = datetime.date.today().isoformat()
        now_dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        tasks_to_penalize = []
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM tasks 
                WHERE user_id = %s 
                  AND (status = 'missed' OR (status = 'pending' AND deadline IS NOT NULL AND deadline < %s))
                ORDER BY deadline ASC, id DESC;
            """, (user_id, now_dt))
            missed_tasks = cur.fetchall()

            for t in missed_tasks:
                if t.get("status") == "pending":
                    cur.execute("UPDATE tasks SET status = 'missed' WHERE id = %s;", (t["id"],))
                    penalty = PENALTY_MAP.get((t.get("priority") or "medium").lower(), -15)
                    cur.execute("INSERT INTO task_logs (task_id, change_description) VALUES (%s, %s);", 
                                (t["id"], f"⚠️ Marked as MISSED due to expired deadline ({penalty} XP)"))
                    t["status"] = "missed"
                    tasks_to_penalize.append((penalty, t["title"]))

                if t.get("deadline"):
                    t["deadline_str"] = str(t["deadline"])
                else:
                    t["deadline_str"] = None

                orig_date = str(t.get("original_date") or "")
                if orig_date:
                    try:
                        d_orig = datetime.datetime.strptime(orig_date[:10], "%Y-%m-%d").date()
                        t["days_overdue"] = max(1, (datetime.date.today() - d_orig).days)
                    except Exception:
                        t["days_overdue"] = 1
                else:
                    t["days_overdue"] = 1

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        for penalty, title in tasks_to_penalize:
            UserModel.modify_xp(user_id, penalty, reason=f"Missed Deadline: {title}")

        return missed_tasks
