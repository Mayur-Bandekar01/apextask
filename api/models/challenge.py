import datetime
import json

try:
    from api.db import get_db_connection
    from api.models.user import UserModel
except ImportError:
    from db import get_db_connection
    from models.user import UserModel

DEFAULT_DAILY_CHALLENGES = [
    {
        "title": "Triple Strike",
        "description": "Complete any 3 productivity missions today",
        "target_count": 3,
        "xp_reward": 50,
        "action_type": "complete_any"
    },
    {
        "title": "High-Stakes Execution",
        "description": "Conquer at least 1 High Priority mission",
        "target_count": 1,
        "xp_reward": 75,
        "action_type": "complete_high"
    },
    {
        "title": "Zero Procrastination",
        "description": "Redeem or finish 1 rolled-over pending mission",
        "target_count": 1,
        "xp_reward": 60,
        "action_type": "complete_rollover"
    }
]

DEFAULT_WEEKLY_CHALLENGES = [
    {
        "title": "Weekly Marathon",
        "description": "Conquer 15 missions throughout this week",
        "target_count": 15,
        "xp_reward": 200,
        "action_type": "complete_any"
    },
    {
        "title": "Apex Consistency",
        "description": "Complete at least 5 high-priority missions this week",
        "target_count": 5,
        "xp_reward": 250,
        "action_type": "complete_high"
    }
]

class ChallengeModel:
    @staticmethod
    def get_user_challenges(user_id=1):
        today = datetime.date.today()
        today_str = today.isoformat()
        # End of week (Sunday)
        days_ahead = 6 - today.weekday()
        week_end = (today + datetime.timedelta(days=days_ahead)).isoformat()

        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check existing daily challenges
            cur.execute("""
                SELECT * FROM challenges 
                WHERE user_id = %s AND challenge_type = 'daily' AND expires_at = %s;
            """, (user_id, today_str))
            daily = cur.fetchall()

            if not daily:
                for c in DEFAULT_DAILY_CHALLENGES:
                    cur.execute("""
                        INSERT INTO challenges (user_id, challenge_type, title, description, target_count, current_count, xp_reward, is_completed, is_claimed, expires_at)
                        VALUES (%s, 'daily', %s, %s, %s, 0, %s, 0, 0, %s);
                    """, (user_id, c["title"], c["description"], c["target_count"], c["xp_reward"], today_str))

            # Check existing weekly challenges
            cur.execute("""
                SELECT * FROM challenges 
                WHERE user_id = %s AND challenge_type = 'weekly' AND expires_at >= %s;
            """, (user_id, today_str))
            weekly = cur.fetchall()

            if not weekly:
                for c in DEFAULT_WEEKLY_CHALLENGES:
                    cur.execute("""
                        INSERT INTO challenges (user_id, challenge_type, title, description, target_count, current_count, xp_reward, is_completed, is_claimed, expires_at)
                        VALUES (%s, 'weekly', %s, %s, %s, 0, %s, 0, 0, %s);
                    """, (user_id, c["title"], c["description"], c["target_count"], c["xp_reward"], week_end))

            if hasattr(conn, 'commit'):
                conn.commit()

            # Retrieve active challenges
            cur.execute("""
                SELECT * FROM challenges 
                WHERE user_id = %s AND expires_at >= %s 
                ORDER BY challenge_type ASC, id ASC;
            """, (user_id, today_str))
            all_challenges = cur.fetchall()

        conn.close()

        formatted = []
        for ch in all_challenges:
            item = dict(ch)
            item['progress_percent'] = min(100, int((item.get('current_count', 0) / max(1, item.get('target_count', 1))) * 100))
            if item.get('expires_at'):
                item['expires_at'] = str(item['expires_at'])
            if item.get('created_at'):
                item['created_at'] = str(item['created_at'])
            formatted.append(item)
        return formatted

    @staticmethod
    def increment_progress(user_id=1, priority="medium", is_rollover=False):
        today_str = datetime.date.today().isoformat()
        conn = get_db_connection()

        with conn.cursor() as cur:
            # Increment daily complete_any
            cur.execute("""
                UPDATE challenges 
                SET current_count = current_count + 1,
                    is_completed = CASE WHEN current_count + 1 >= target_count THEN 1 ELSE 0 END
                WHERE user_id = %s AND expires_at >= %s AND is_claimed = 0;
            """, (user_id, today_str))

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

    @staticmethod
    def claim_reward(challenge_id, user_id=1):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM challenges 
                WHERE id = %s AND user_id = %s;
            """, (challenge_id, user_id))
            ch = cur.fetchone()

            if not ch:
                conn.close()
                return {"success": False, "error": "Challenge not found"}

            if ch.get('is_claimed'):
                conn.close()
                return {"success": False, "error": "Challenge reward already claimed"}

            if ch.get('current_count', 0) < ch.get('target_count', 1):
                conn.close()
                return {"success": False, "error": "Challenge target not yet reached"}

            xp_reward = ch.get('xp_reward', 50)

            cur.execute("""
                UPDATE challenges 
                SET is_claimed = 1, is_completed = 1 
                WHERE id = %s;
            """, (challenge_id,))

            if hasattr(conn, 'commit'):
                conn.commit()
        conn.close()

        xp_res = UserModel.modify_xp(user_id, xp_reward, reason=f"Completed Challenge: {ch.get('title')}")
        profile = UserModel.get_profile(user_id)

        return {
            "success": True,
            "xp_reward": xp_reward,
            "xp_result": xp_res,
            "profile": profile
        }
