import datetime
from api.db import get_db_connection, get_engine_name

def calculate_level_info(total_xp):
    if total_xp < 0:
        total_xp = 0
    level = 1
    accumulated_xp = 0
    needed_for_next = 100

    while True:
        level_cost = int(100 * (1.5 ** (level - 1)))
        if total_xp < accumulated_xp + level_cost:
            current_level_xp = total_xp - accumulated_xp
            needed_for_next = level_cost
            break
        accumulated_xp += level_cost
        level += 1

    progress_percent = min(100, max(0, int((current_level_xp / needed_for_next) * 100)))
    xp_to_next = needed_for_next - current_level_xp

    return {
        "level": level,
        "current_level_xp": current_level_xp,
        "needed_for_next": needed_for_next,
        "xp_to_next": xp_to_next,
        "progress_percent": progress_percent,
        "total_xp": total_xp
    }

class UserModel:
    @staticmethod
    def get_user(user_id=1):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
            user = cur.fetchone()
        conn.close()
        return user

    @staticmethod
    def get_user_by_username(username):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s LIMIT 1;", (username,))
            user = cur.fetchone()
        conn.close()
        return user

    @staticmethod
    def get_profile(user_id=1):
        user = UserModel.get_user(user_id)
        if not user:
            # If user not found, try getting first user
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users ORDER BY id ASC LIMIT 1;")
                user = cur.fetchone()
            conn.close()
            if not user:
                return None

        level_info = calculate_level_info(user.get("xp", 0))

        # Check badges count
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT badge_name, earned_at FROM badges WHERE user_id = %s ORDER BY earned_at DESC;", (user["id"],))
            badges = cur.fetchall()

            # Count total completed tasks
            cur.execute("SELECT COUNT(*) as completed_count FROM tasks WHERE user_id = %s AND status = 'complete';", (user["id"],))
            completed_row = cur.fetchone()
            total_completed = completed_row.get("completed_count", 0) if completed_row else 0

            # Count missed tasks
            cur.execute("SELECT COUNT(*) as missed_count FROM tasks WHERE user_id = %s AND (status = 'missed' OR (status = 'pending' AND deadline IS NOT NULL AND deadline < CURRENT_TIMESTAMP));", (user["id"],))
            missed_row = cur.fetchone()
            total_missed = missed_row.get("missed_count", 0) if missed_row else 0
        conn.close()

        # Dynamic title progression if not in Slacker Mode
        title = user.get("title", "Productivity Architect")
        if title != "😴 Slacker Mode":
            lvl = level_info["level"]
            if lvl >= 20:
                title = "⚡ Grandmaster of Execution"
            elif lvl >= 15:
                title = "🔥 Productivity Titan"
            elif lvl >= 10:
                title = "🎯 Master Strategist"
            elif lvl >= 5:
                title = "🚀 Focus Champion"
            elif lvl >= 3:
                title = "✨ Task Crusher"
            elif lvl >= 2:
                title = "🌱 Momentum Builder"
            else:
                title = "🌟 Productivity Architect"

        level_at_risk = False
        if level_info["current_level_xp"] < 0 or user.get("xp", 0) < 0:
            level_at_risk = True

        return {
            "id": user["id"],
            "username": user["username"],
            "title": title,
            "xp": user["xp"],
            "level": level_info["level"],
            "current_level_xp": level_info["current_level_xp"],
            "needed_for_next": level_info["needed_for_next"],
            "xp_to_next": level_info["xp_to_next"],
            "progress_percent": level_info["progress_percent"],
            "streak": user.get("streak", 0),
            "badge_count": len(badges),
            "total_completed": total_completed,
            "total_missed": total_missed,
            "level_at_risk": level_at_risk,
            "db_engine": get_engine_name()
        }

    @staticmethod
    def modify_xp(user_id, amount, reason=""):
        user = UserModel.get_user(user_id)
        if not user:
            return None

        current_xp = user.get("xp", 0)
        old_level_info = calculate_level_info(current_xp)

        new_xp = max(0, current_xp + amount)
        new_level_info = calculate_level_info(new_xp)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET xp = %s WHERE id = %s;", (new_xp, user_id))
            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        leveled_up = new_level_info["level"] > old_level_info["level"]
        leveled_down = new_level_info["level"] < old_level_info["level"]

        return {
            "old_xp": current_xp,
            "new_xp": new_xp,
            "delta": amount,
            "level": new_level_info["level"],
            "leveled_up": leveled_up,
            "leveled_down": leveled_down,
            "reason": reason
        }

    @staticmethod
    def check_and_update_streak(user_id=1):
        today = datetime.date.today()
        conn = get_db_connection()
        streak_lost = False
        streak_gained = False

        with conn.cursor() as cur:
            cur.execute("SELECT last_active, streak, title FROM users WHERE id = %s;", (user_id,))
            user = cur.fetchone()
            if not user:
                conn.close()
                return False, False, 0

            last_active_raw = user.get("last_active")
            streak = user.get("streak", 0) or 0
            title = user.get("title", "Productivity Architect")

            if last_active_raw:
                if isinstance(last_active_raw, str):
                    last_active = datetime.datetime.strptime(last_active_raw[:10], "%Y-%m-%d").date()
                elif isinstance(last_active_raw, datetime.datetime):
                    last_active = last_active_raw.date()
                else:
                    last_active = last_active_raw

                delta = (today - last_active).days
                if delta == 0:
                    if title == "😴 Slacker Mode":
                        title = "Productivity Architect"
                        cur.execute("UPDATE users SET title = %s WHERE id = %s;", (title, user_id))
                elif delta == 1:
                    streak += 1
                    streak_gained = True
                    if title == "😴 Slacker Mode":
                        title = "Productivity Architect"
                    cur.execute("UPDATE users SET streak = %s, last_active = %s, title = %s WHERE id = %s;", (streak, today.isoformat(), title, user_id))
                else:
                    streak_lost = True
                    streak = 1
                    if delta >= 3:
                        title = "😴 Slacker Mode"
                    else:
                        title = "Productivity Architect"
                    cur.execute("UPDATE users SET streak = %s, last_active = %s, title = %s WHERE id = %s;", (streak, today.isoformat(), title, user_id))
            else:
                streak = 1
                streak_gained = True
                cur.execute("UPDATE users SET streak = 1, last_active = %s, title = 'Productivity Architect' WHERE id = %s;", (today.isoformat(), user_id))

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        return streak_gained, streak_lost, streak

    @staticmethod
    def reset_progress(user_id=1):
        conn = get_db_connection()
        today = datetime.date.today().isoformat()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users 
                SET xp = 0, streak = 0, 
                    title = 'Productivity Architect', last_active = %s
                WHERE id = %s;
            """, (today, user_id))

            cur.execute("DELETE FROM badges WHERE user_id = %s;", (user_id,))
            cur.execute("DELETE FROM daily_records WHERE user_id = %s;", (user_id,))

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        return UserModel.get_profile(user_id)
