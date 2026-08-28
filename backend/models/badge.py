import datetime
from backend.db import get_db_connection

ALL_BADGES = {
    "First Step": {
        "title": "First Step",
        "description": "Completed your first task.",
        "icon": "fa-shoe-prints",
        "tier": "bronze"
    },
    "High Flyer": {
        "title": "High Flyer",
        "description": "Crushed a High Priority task.",
        "icon": "fa-bolt",
        "tier": "gold"
    },
    "Productivity Beast": {
        "title": "Productivity Beast",
        "description": "Completed 5 or more tasks in a single day.",
        "icon": "fa-fire-flame-curved",
        "tier": "gold"
    },
    "Night Owl": {
        "title": "Night Owl",
        "description": "Completed a task between 10 PM and 4 AM.",
        "icon": "fa-moon",
        "tier": "silver"
    },
    "Early Bird": {
        "title": "Early Bird",
        "description": "Completed a task between 5 AM and 8 AM.",
        "icon": "fa-sun",
        "tier": "silver"
    },
    "Tenacious": {
        "title": "Tenacious",
        "description": "Completed a task that was rolled over from a previous day.",
        "icon": "fa-shield-halved",
        "tier": "gold"
    },
    "3-Day Streak": {
        "title": "3-Day Streak",
        "description": "Maintained a 3-day completion streak.",
        "icon": "fa-award",
        "tier": "bronze"
    },
    "7-Day Streak": {
        "title": "7-Day Streak",
        "description": "Maintained an unbroken 7-day productivity streak.",
        "icon": "fa-crown",
        "tier": "gold"
    },
    "14-Day Streak": {
        "title": "14-Day Streak",
        "description": "Two solid weeks of unstoppable momentum.",
        "icon": "fa-gem",
        "tier": "platinum"
    },
    "30-Day Streak": {
        "title": "30-Day Streak",
        "description": "A full month of relentless consistency.",
        "icon": "fa-dragon",
        "tier": "legendary"
    },
    "Perfectionist": {
        "title": "Perfectionist",
        "description": "Completed 100% of all scheduled tasks in a day.",
        "icon": "fa-circle-check",
        "tier": "platinum"
    }
}

class BadgeModel:
    @staticmethod
    def get_user_badges(user_id=1):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT badge_name, earned_at FROM badges WHERE user_id = %s ORDER BY earned_at DESC;", (user_id,))
            earned = cur.fetchall()
        conn.close()

        earned_map = {b["badge_name"]: b["earned_at"] for b in earned}
        badges_list = []
        for name, meta in ALL_BADGES.items():
            is_unlocked = name in earned_map
            badges_list.append({
                "name": name,
                "title": meta["title"],
                "description": meta["description"],
                "icon": meta["icon"],
                "tier": meta["tier"],
                "unlocked": is_unlocked,
                "earned_at": str(earned_map.get(name) or "")
            })
        return badges_list

    @staticmethod
    def award_badge(user_id, badge_name):
        if badge_name not in ALL_BADGES:
            return None
        conn = get_db_connection()
        awarded = False
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM badges WHERE user_id = %s AND badge_name = %s;", (user_id, badge_name))
            if not cur.fetchone():
                cur.execute("INSERT INTO badges (user_id, badge_name) VALUES (%s, %s);", (user_id, badge_name))
                if hasattr(conn, 'commit'):
                    conn.commit()
                awarded = True
        conn.close()
        if awarded:
            return ALL_BADGES[badge_name]
        return None

    @staticmethod
    def evaluate_task_completion_badges(user_id, task, today_completed_count, streak_count):
        new_badges = []

        # 1. First Task Done
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = %s AND status = 'complete';", (user_id,))
            row = cur.fetchone()
            total_completed = row.get("c", 0) if row else 1
        conn.close()

        if total_completed >= 1:
            b = BadgeModel.award_badge(user_id, "First Step")
            if b: new_badges.append(b)

        # 2. High Flyer (High priority)
        if task.get("priority") == "high":
            b = BadgeModel.award_badge(user_id, "High Flyer")
            if b: new_badges.append(b)

        # 3. Rolled over task complete
        if (task.get("rollover_count") or 0) > 0:
            b = BadgeModel.award_badge(user_id, "Tenacious")
            if b: new_badges.append(b)

        # 4. 5 Tasks in a Day
        if today_completed_count >= 5:
            b = BadgeModel.award_badge(user_id, "Productivity Beast")
            if b: new_badges.append(b)

        # 5. Time-based (Night Owl / Early Bird)
        now_hour = datetime.datetime.now().hour
        if now_hour >= 22 or now_hour < 4:
            b = BadgeModel.award_badge(user_id, "Night Owl")
            if b: new_badges.append(b)
        elif 5 <= now_hour < 8:
            b = BadgeModel.award_badge(user_id, "Early Bird")
            if b: new_badges.append(b)

        # 6. Streak badges
        if streak_count >= 3:
            b = BadgeModel.award_badge(user_id, "3-Day Streak")
            if b: new_badges.append(b)
        if streak_count >= 7:
            b = BadgeModel.award_badge(user_id, "7-Day Streak")
            if b: new_badges.append(b)
        if streak_count >= 14:
            b = BadgeModel.award_badge(user_id, "14-Day Streak")
            if b: new_badges.append(b)
        if streak_count >= 30:
            b = BadgeModel.award_badge(user_id, "30-Day Streak")
            if b: new_badges.append(b)

        return new_badges
