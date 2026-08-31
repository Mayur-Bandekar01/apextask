import datetime
import json

try:
    from api.db import get_db_connection
    from api.models.user import UserModel
    from api.models.badge import BadgeModel
    from api.models.challenge import ChallengeModel
except ImportError:
    from db import get_db_connection
    from models.user import UserModel
    from models.badge import BadgeModel
    from models.challenge import ChallengeModel

XP_MAP = {
    "low": 10,
    "medium": 25,
    "high": 50
}

class TaskModel:
    @staticmethod
    def get_task_by_id(task_id, user_id=1):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.*, 
                       (SELECT COUNT(*) FROM task_logs tl WHERE tl.task_id = t.id) as log_count
                FROM tasks t 
                WHERE t.id = %s AND t.user_id = %s;
            """, (task_id, user_id))
            task = cur.fetchone()
        conn.close()
        return TaskModel._format_task(task)

    @staticmethod
    def get_tasks_for_today(user_id=1, date_str=None):
        today = date_str if date_str else datetime.date.today().isoformat()
        return TaskModel.get_tasks_by_date(user_id, today)

    @staticmethod
    def get_tasks_by_date(user_id, date_str):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.*, 
                       (SELECT COUNT(*) FROM task_logs tl WHERE tl.task_id = t.id) as log_count
                FROM tasks t
                WHERE t.user_id = %s AND t.original_date = %s
                ORDER BY 
                    t.is_boss DESC,
                    CASE t.priority 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        WHEN 'low' THEN 3 
                        ELSE 4 
                    END,
                    t.created_at ASC;
            """, (user_id, date_str))
            tasks = cur.fetchall()
        conn.close()
        return [TaskModel._format_task(t) for t in tasks]

    @staticmethod
    def create_task(user_id, title, notes="", priority="medium", deadline=None, original_date=None, tags="", is_boss=False, subtasks=None):
        if not original_date:
            original_date = datetime.date.today().isoformat()

        is_boss_int = 1 if is_boss else 0
        boss_max_hp = 100 if is_boss else 0
        boss_hp = 100 if is_boss else 0

        # Subtasks default formatting
        if subtasks and isinstance(subtasks, list):
            subtasks_str = json.dumps(subtasks)
        elif is_boss:
            subtasks_str = json.dumps([
                {"title": "Phase 1: Deep Research & Blueprint", "completed": False},
                {"title": "Phase 2: Core Execution & Implementation", "completed": False},
                {"title": "Phase 3: Final Polish & Strike", "completed": False}
            ])
        else:
            subtasks_str = json.dumps([])

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tasks (user_id, title, notes, priority, status, original_date, deadline, rollover_count, tags, is_boss, boss_hp, boss_max_hp, subtasks)
                VALUES (%s, %s, %s, %s, 'pending', %s, %s, 0, %s, %s, %s, %s, %s);
            """, (user_id, title, notes or '', priority.lower(), original_date, deadline or None, tags or '', is_boss_int, boss_hp, boss_max_hp, subtasks_str))
            
            task_id = cur.lastrowid

            # Create initial lifecycle log
            boss_tag = " [BOSS BATTLE SPAWNED 👑]" if is_boss else ""
            log_msg = f"Created task with {priority.upper()} priority{boss_tag} (Target: {original_date})"
            cur.execute("""
                INSERT INTO task_logs (task_id, change_description)
                VALUES (%s, %s);
            """, (task_id, log_msg))

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        return TaskModel.get_task_by_id(task_id, user_id)

    @staticmethod
    def update_task(task_id, user_id, title, notes="", priority="medium", deadline=None, original_date=None, tags=None, subtasks=None):
        old_task = TaskModel.get_task_by_id(task_id, user_id)
        if not old_task:
            return None

        changes = []
        if old_task.get("title") != title:
            changes.append(f"Title changed from '{old_task.get('title')}' to '{title}'")
        if (old_task.get("notes") or "") != (notes or ""):
            changes.append("Notes updated")
        if old_task.get("priority") != priority.lower():
            changes.append(f"Priority changed from {old_task.get('priority')} to {priority.lower()}")
        if old_task.get("deadline") != deadline:
            changes.append(f"Deadline updated to {deadline or 'None'}")
        if original_date and old_task.get("original_date") != original_date:
            changes.append(f"Execution date updated to {original_date}")
        if tags is not None and old_task.get("tags") != tags:
            changes.append(f"Tags updated to '{tags}'")
        if subtasks is not None:
            changes.append("Subtasks updated")

        if not changes:
            changes.append("Task details refreshed")

        change_log_str = "; ".join(changes)

        # Format subtasks
        if subtasks is not None:
            if isinstance(subtasks, list):
                subtasks_str = json.dumps(subtasks)
            elif isinstance(subtasks, str):
                subtasks_str = subtasks
            else:
                subtasks_str = json.dumps([])
        else:
            subtasks_str = None

        new_original_date = original_date if original_date else old_task.get("original_date")

        conn = get_db_connection()
        with conn.cursor() as cur:
            if subtasks_str is not None:
                cur.execute("""
                    UPDATE tasks 
                    SET title = %s, notes = %s, priority = %s, deadline = %s, original_date = %s, tags = COALESCE(%s, tags), subtasks = %s
                    WHERE id = %s AND user_id = %s;
                """, (title, notes or '', priority.lower(), deadline or None, new_original_date, tags, subtasks_str, task_id, user_id))
            else:
                cur.execute("""
                    UPDATE tasks 
                    SET title = %s, notes = %s, priority = %s, deadline = %s, original_date = %s, tags = COALESCE(%s, tags)
                    WHERE id = %s AND user_id = %s;
                """, (title, notes or '', priority.lower(), deadline or None, new_original_date, tags, task_id, user_id))

            cur.execute("""
                INSERT INTO task_logs (task_id, change_description)
                VALUES (%s, %s);
            """, (task_id, change_log_str))

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        return TaskModel.get_task_by_id(task_id, user_id)

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

        # 3x XP multiplier for Boss Battle Tasks!
        is_boss = bool(task.get("is_boss"))
        if is_boss:
            base_xp = base_xp * 3

        xp_delta = base_xp if new_status == "complete" else -base_xp
        today = datetime.date.today().isoformat()

        # Update subtasks to all completed if completing boss
        subtasks = task.get("subtasks") or []
        if is_boss and new_status == "complete":
            for s in subtasks:
                s["completed"] = True
        subtasks_json = json.dumps(subtasks)
        boss_hp = 0 if new_status == "complete" and is_boss else (100 if is_boss else 0)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks 
                SET status = %s, subtasks = %s, boss_hp = %s
                WHERE id = %s AND user_id = %s;
            """, (new_status, subtasks_json, boss_hp, task_id, user_id))

            boss_tag = " [👑 3X BOSS BOUNTY CLAIMED!]" if is_boss and new_status == "complete" else ""
            log_msg = f"Marked completed (+XP awarded){boss_tag}" if new_status == "complete" else "Reopened task (XP adjusted)"
            cur.execute("""
                INSERT INTO task_logs (task_id, change_description)
                VALUES (%s, %s);
            """, (task_id, log_msg))

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        # Update User XP
        xp_result = UserModel.modify_xp(user_id, xp_delta, reason=f"Task {new_status}: {task.get('title')}")

        # Update Streak if completed
        streak_gained, streak_lost, current_streak = (False, False, 0)
        if new_status == "complete":
            streak_gained, streak_lost, current_streak = UserModel.check_and_update_streak(user_id)
            ChallengeModel.increment_progress(user_id, priority, task.get("rollover_count", 0) > 0)
        else:
            user = UserModel.get_user(user_id)
            current_streak = user.get("streak", 0) if user else 0

        # Update Daily Record
        TaskModel._update_daily_record(user_id, today, delta_completed=(1 if new_status == "complete" else -1), delta_xp=xp_delta)

        # Check badges if completed
        new_badges = []
        if new_status == "complete":
            profile = UserModel.get_profile(user_id)
            total_completed = profile.get("total_completed", 1) if profile else 1
            new_badges = BadgeModel.evaluate_task_completion_badges(
                user_id=user_id,
                task=task,
                streak=current_streak,
                total_completed=total_completed
            )

        updated_profile = UserModel.get_profile(user_id)

        return {
            "task_id": task_id,
            "status": new_status,
            "is_boss": is_boss,
            "xp_delta": xp_delta,
            "xp_result": xp_result,
            "streak_gained": streak_gained,
            "streak_lost": streak_lost,
            "current_streak": current_streak,
            "new_badges": new_badges,
            "profile": updated_profile
        }

    @staticmethod
    def damage_boss_subtask(task_id, subtask_index, user_id=1):
        task = TaskModel.get_task_by_id(task_id, user_id)
        if not task or not task.get('is_boss'):
            return None

        subtasks = task.get('subtasks') or []
        if subtask_index < 0 or subtask_index >= len(subtasks):
            return None

        # Toggle subtask state
        subtasks[subtask_index]['completed'] = not subtasks[subtask_index].get('completed', False)
        
        # Calculate damage & remaining HP
        total_subtasks = max(1, len(subtasks))
        completed_subtasks = sum(1 for s in subtasks if s.get('completed'))
        damage_percent = int((completed_subtasks / total_subtasks) * 100)
        new_hp = max(0, 100 - damage_percent)
        
        is_defeated = (new_hp <= 0 or completed_subtasks == total_subtasks)
        new_status = "complete" if is_defeated else "pending"
        
        subtasks_json = json.dumps(subtasks)
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks 
                SET subtasks = %s, boss_hp = %s, status = %s 
                WHERE id = %s AND user_id = %s;
            """, (subtasks_json, new_hp, new_status, task_id, user_id))
            
            action_desc = f"Struck Boss! Dealt damage to phase {subtask_index+1} (HP: {new_hp}/100)"
            if is_defeated:
                action_desc = "⚔️ BOSS DEFEATED! 3x XP multiplier unleashed & Mystery Chest ready!"
            cur.execute("""
                INSERT INTO task_logs (task_id, change_description)
                VALUES (%s, %s);
            """, (task_id, action_desc))
            
            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()
        
        # Award subtask strike XP (+25 XP per strike)
        strike_xp = 25
        if is_defeated:
            # 3x XP boss bounty (+150 XP)
            strike_xp += 150
            
        xp_result = UserModel.modify_xp(user_id, strike_xp, reason=f"Boss Strike on: {task.get('title')}")
        if is_defeated:
            ChallengeModel.increment_progress(user_id, "high", False)
            
        return {
            "task_id": task_id,
            "boss_hp": new_hp,
            "is_defeated": is_defeated,
            "subtasks": subtasks,
            "status": new_status,
            "xp_awarded": strike_xp,
            "xp_result": xp_result,
            "profile": UserModel.get_profile(user_id)
        }

    @staticmethod
    def toggle_normal_subtask(task_id, subtask_index, user_id=1):
        task = TaskModel.get_task_by_id(task_id, user_id)
        if not task:
            return None

        subtasks = task.get('subtasks') or []
        if subtask_index < 0 or subtask_index >= len(subtasks):
            return None

        st = subtasks[subtask_index]
        is_done = not (st.get('is_done') or st.get('completed') or False)
        st['is_done'] = is_done
        st['completed'] = is_done

        subtasks_json = json.dumps(subtasks)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks 
                SET subtasks = %s 
                WHERE id = %s AND user_id = %s;
            """, (subtasks_json, task_id, user_id))

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        return {
            "task_id": task_id,
            "subtask_index": subtask_index,
            "is_done": is_done,
            "subtasks": subtasks
        }

    @staticmethod
    def rollover_tasks(user_id=1):
        today = datetime.date.today().isoformat()
        conn = get_db_connection()

        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, original_date, rollover_count 
                FROM tasks 
                WHERE user_id = %s AND status = 'pending' AND original_date < %s;
            """, (user_id, today))
            pending_past_tasks = cur.fetchall()

            rolled_task_ids = []
            for t in pending_past_tasks:
                tid = t["id"]
                new_count = (t.get("rollover_count") or 0) + 1
                cur.execute("""
                    UPDATE tasks 
                    SET original_date = %s, rollover_count = %s 
                    WHERE id = %s;
                """, (today, new_count, tid))

                cur.execute("""
                    INSERT INTO task_logs (task_id, change_description)
                    VALUES (%s, %s);
                """, (tid, f"Auto-rolled over to {today} (Rollover #{new_count})"))

                rolled_task_ids.append(tid)

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        return {
            "rolled_count": len(rolled_task_ids),
            "rolled_task_ids": rolled_task_ids,
            "target_date": today
        }

    @staticmethod
    def get_shame_summary(user_id=1):
        """Returns a summary of missed tasks for the shame board login popup and history tab."""
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        today_str = today.isoformat()
        yesterday_str = yesterday.isoformat()

        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Tasks that were pending yesterday (not rolled over yet — these are truly missed)
            cur.execute("""
                SELECT id, title, priority, rollover_count
                FROM tasks
                WHERE user_id = %s
                  AND status = 'pending'
                  AND original_date < %s
                ORDER BY original_date ASC, priority DESC;
            """, (user_id, today_str))
            missed_tasks_raw = cur.fetchall()

            # 2. Yesterday's daily record (completed count)
            cur.execute("""
                SELECT tasks_completed, tasks_missed, xp_earned
                FROM daily_records
                WHERE user_id = %s AND record_date = %s;
            """, (user_id, yesterday_str))
            yesterday_record = cur.fetchone()

            # 3. Historical shame log: only days with actual missed tasks
            cur.execute("""
                SELECT record_date, tasks_completed, tasks_missed, xp_earned
                FROM daily_records
                WHERE user_id = %s
                  AND tasks_missed > 0
                ORDER BY record_date DESC
                LIMIT 30;
            """, (user_id,))
            shame_history_raw = cur.fetchall()

        conn.close()

        yesterday_completed = (yesterday_record.get('tasks_completed', 0) if yesterday_record else 0)
        yesterday_missed = len(missed_tasks_raw)
        total_yesterday = yesterday_completed + yesterday_missed
        completion_rate = int((yesterday_completed / total_yesterday * 100)) if total_yesterday > 0 else 100

        missed_titles = []
        for t in missed_tasks_raw:
            title = t.get('title', 'Untitled Task')
            priority = t.get('priority', 'medium')
            rollover = t.get('rollover_count', 0)
            missed_titles.append({
                'title': title,
                'priority': priority,
                'rollover_count': rollover
            })

        shame_history = []
        for rec in shame_history_raw:
            rd = rec.get('record_date')
            rd_str = rd.isoformat() if isinstance(rd, (datetime.date, datetime.datetime)) else str(rd) if rd else None
            shame_history.append({
                'date': rd_str,
                'tasks_completed': rec.get('tasks_completed', 0),
                'tasks_missed': rec.get('tasks_missed', 0),
                'xp_earned': rec.get('xp_earned', 0)
            })

        # Determine shame level message
        if completion_rate == 100 and yesterday_missed == 0:
            shame_level = 'clean'
            shame_message = '🏆 Zero Shame! You crushed it yesterday.'
        elif completion_rate >= 75:
            shame_level = 'mild'
            shame_message = '😬 Almost there. A few missions slipped through.'
        elif completion_rate >= 40:
            shame_level = 'moderate'
            shame_message = '⚠️ Rough day. Half your missions were abandoned.'
        else:
            shame_level = 'severe'
            shame_message = '☠️ Total meltdown. Your discipline needs a serious reboot.'

        has_shame = yesterday_missed > 0

        return {
            'has_shame': has_shame,
            'yesterday_date': yesterday_str,
            'yesterday_completed': yesterday_completed,
            'yesterday_missed': yesterday_missed,
            'completion_rate': completion_rate,
            'shame_level': shame_level,
            'shame_message': shame_message,
            'missed_tasks': missed_titles,
            'shame_history': shame_history
        }

    @staticmethod
    def get_missed_tasks(user_id=1):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.*, 
                       (SELECT COUNT(*) FROM task_logs tl WHERE tl.task_id = t.id) as log_count
                FROM tasks t
                WHERE t.user_id = %s 
                  AND (
                      t.status = 'missed' 
                      OR (t.status = 'pending' AND t.deadline IS NOT NULL AND t.deadline < CURRENT_TIMESTAMP)
                  )
                ORDER BY t.deadline ASC, t.original_date ASC;
            """, (user_id,))
            tasks = cur.fetchall()
        conn.close()

        now = datetime.datetime.now()
        formatted_tasks = []
        for t in tasks:
            f = TaskModel._format_task(t)
            deadline = f.get("deadline_raw")
            if deadline and isinstance(deadline, (datetime.datetime, datetime.date)):
                deadline_dt = deadline if isinstance(deadline, datetime.datetime) else datetime.datetime.combine(deadline, datetime.time.min)
                days_overdue = max(1, (now - deadline_dt).days)
            else:
                orig = f.get("original_date")
                if orig:
                    try:
                        orig_dt = datetime.datetime.strptime(orig[:10], "%Y-%m-%d")
                        days_overdue = max(1, (now - orig_dt).days)
                    except Exception:
                        days_overdue = 1
                else:
                    days_overdue = 1

            f["days_overdue"] = days_overdue
            formatted_tasks.append(f)

        return formatted_tasks

    @staticmethod
    def get_task_logs(task_id, user_id=1):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tl.* 
                FROM task_logs tl
                JOIN tasks t ON t.id = tl.task_id
                WHERE tl.task_id = %s AND t.user_id = %s
                ORDER BY tl.changed_at DESC;
            """, (task_id, user_id))
            logs = cur.fetchall()
        conn.close()

        formatted_logs = []
        for l in logs:
            dt = l.get("changed_at")
            dt_str = dt.isoformat() if isinstance(dt, (datetime.datetime, datetime.date)) else str(dt) if dt else None
            formatted_logs.append({
                "id": l["id"],
                "task_id": l["task_id"],
                "change_description": l["change_description"],
                "changed_at_str": dt_str
            })
        return formatted_logs

    @staticmethod
    def _update_daily_record(user_id, record_date, delta_completed=0, delta_xp=0):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM daily_records WHERE user_id = %s AND record_date = %s;", (user_id, record_date))
            rec = cur.fetchone()

            if rec:
                new_completed = max(0, rec.get("tasks_completed", 0) + delta_completed)
                new_xp = max(0, rec.get("xp_earned", 0) + delta_xp)
                cur.execute("""
                    UPDATE daily_records 
                    SET tasks_completed = %s, xp_earned = %s 
                    WHERE id = %s;
                """, (new_completed, new_xp, rec["id"]))
            else:
                new_completed = max(0, delta_completed)
                new_xp = max(0, delta_xp)
                cur.execute("""
                    INSERT INTO daily_records (user_id, record_date, tasks_completed, tasks_missed, xp_earned, focus_time)
                    VALUES (%s, %s, %s, 0, %s, 0);
                """, (user_id, record_date, new_completed, new_xp))

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

    @staticmethod
    def _format_task(task):
        if not task:
            return None

        t = dict(task)
        deadline = t.get("deadline")
        created_at = t.get("created_at")
        updated_at = t.get("updated_at")

        t["deadline_raw"] = deadline
        t["deadline"] = deadline.isoformat() if isinstance(deadline, (datetime.datetime, datetime.date)) else str(deadline) if deadline else None
        t["created_at_str"] = created_at.isoformat() if isinstance(created_at, (datetime.datetime, datetime.date)) else str(created_at) if created_at else None
        t["updated_at_str"] = updated_at.isoformat() if isinstance(updated_at, (datetime.datetime, datetime.date)) else str(updated_at) if updated_at else None

        orig_date = t.get("original_date")
        if isinstance(orig_date, (datetime.date, datetime.datetime)):
            t["original_date"] = orig_date.strftime("%Y-%m-%d")
        else:
            t["original_date"] = str(orig_date) if orig_date else None

        # Parse subtasks
        subtasks_raw = t.get("subtasks")
        if isinstance(subtasks_raw, str) and subtasks_raw.strip():
            try:
                t["subtasks"] = json.loads(subtasks_raw)
            except Exception:
                t["subtasks"] = []
        elif isinstance(subtasks_raw, list):
            t["subtasks"] = subtasks_raw
        else:
            t["subtasks"] = []

        t["is_boss"] = bool(t.get("is_boss"))
        t["boss_hp"] = t.get("boss_hp", 100) if t["is_boss"] else 0
        t["boss_max_hp"] = t.get("boss_max_hp", 100) if t["is_boss"] else 0
        t["tags"] = t.get("tags") or ""

        # Calculate days pending
        if t.get("status") == "pending" and t.get("original_date"):
            try:
                task_dt = datetime.datetime.strptime(t["original_date"][:10], "%Y-%m-%d").date()
                today = datetime.date.today()
                t["days_pending"] = max(0, (today - task_dt).days)
            except Exception:
                t["days_pending"] = 0
        else:
            t["days_pending"] = 0

        return t
