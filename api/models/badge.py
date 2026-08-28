import datetime
from api.db import get_db_connection

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
        "description": "A full month of relentless execution.",
        "icon": "fa-dragon",
        "tier": "legendary"
    },
    "Century Club": {
        "title": "Century Club",
        "description": "Conquered 100 total lifetime tasks.",
        "icon": "fa-trophy",
        "tier": "legendary"
    }
}

class BadgeModel:
    @staticmethod
    def get_user_badges(user_id=1):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT badge_name, earned_at FROM badges WHERE user_id = %s ORDER BY earned_at ASC;", (user_id,))
            earned_rows = cur.fetchall()
        conn.close()

        earned_dict = {row["badge_name"]: row["earned_at"] for row in earned_rows}

        badges_list = []
        for badge_name, info in ALL_BADGES.items():
            unlocked = badge_name in earned_dict
            earned_at = earned_dict.get(badge_name)
            earned_at_str = earned_at.isoformat() if isinstance(earned_at, (datetime.date, datetime.datetime)) else str(earned_at) if earned_at else None

            badges_list.append({
                "badge_name": badge_name,
                "title": info["title"],
                "description": info["description"],
                "icon": info["icon"],
                "tier": info["tier"],
                "unlocked": unlocked,
                "earned_at": earned_at_str
            })

        return badges_list

    @staticmethod
    def award_badge(user_id, badge_name):
        if badge_name not in ALL_BADGES:
            return None

        conn = get_db_connection()
        already_earned = False
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM badges WHERE user_id = %s AND badge_name = %s;", (user_id, badge_name))
            if cur.fetchone():
                already_earned = True
            else:
                cur.execute("INSERT INTO badges (user_id, badge_name) VALUES (%s, %s);", (user_id, badge_name))
                if hasattr(conn, 'commit'):
                    conn.commit()
        conn.close()

        if already_earned:
            return None

        info = ALL_BADGES[badge_name]
        return {
            "badge_name": badge_name,
            "title": info["title"],
            "description": info["description"],
            "icon": info["icon"],
            "tier": info["tier"]
        }

    @staticmethod
    def evaluate_task_completion_badges(user_id, task, streak, total_completed):
        new_badges = []

        # 1. First Step
        if total_completed >= 1:
            b = BadgeModel.award_badge(user_id, "First Step")
            if b: new_badges.append(b)

        # 2. High Flyer
        if (task.get("priority") or "").lower() == "high":
            b = BadgeModel.award_badge(user_id, "High Flyer")
            if b: new_badges.append(b)

        # 3. Tenacious
        if (task.get("rollover_count") or 0) > 0:
            b = BadgeModel.award_badge(user_id, "Tenacious")
            if b: new_badges.append(b)

        # 4. Time based: Night Owl / Early Bird
        now_hour = datetime.datetime.now().hour
        if now_hour >= 22 or now_hour < 4:
            b = BadgeModel.award_badge(user_id, "Night Owl")
            if b: new_badges.append(b)
        elif 5 <= now_hour < 8:
            b = BadgeModel.award_badge(user_id, "Early Bird")
            if b: new_badges.append(b)

        # 5. Productivity Beast (5+ completed today)
        today = datetime.date.today().isoformat()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM tasks WHERE user_id = %s AND status = 'complete' AND original_date = %s;", (user_id, today))
            row = cur.fetchone()
            today_completed = row.get("cnt", 0) if row else 0
        conn.close()

        if today_completed >= 5:
            b = BadgeModel.award_badge(user_id, "Productivity Beast")
            if b: new_badges.append(b)

        # 6. Streak Badges
        if streak >= 30:
            b = BadgeModel.award_badge(user_id, "30-Day Streak")
            if b: new_badges.append(b)
        elif streak >= 14:
            b = BadgeModel.award_badge(user_id, "14-Day Streak")
            if b: new_badges.append(b)
        elif streak >= 7:
            b = BadgeModel.award_badge(user_id, "7-Day Streak")
            if b: new_badges.append(b)
        elif streak >= 3:
            b = BadgeModel.award_badge(user_id, "3-Day Streak")
            if b: new_badges.append(b)

        # 7. Century Club
        if total_completed >= 100:
            b = BadgeModel.award_badge(user_id, "Century Club")
            if b: new_badges.append(b)

        return new_badges
