import random
from flask import Blueprint, request, jsonify
from backend.models.user import UserModel
from backend.models.badge import BadgeModel, ALL_BADGES

gamification_bp = Blueprint('gamification', __name__, url_prefix='/api')

CHEST_REWARDS = [
    {"type": "xp", "value": 50, "title": "50 Bonus XP", "icon": "fa-gem", "desc": "A burst of crystallized productivity!"},
    {"type": "xp", "value": 100, "title": "100 Grand XP", "icon": "fa-crown", "desc": "A golden bounty of sheer momentum!"},
    {"type": "xp", "value": 150, "title": "150 Legendary XP", "icon": "fa-dragon", "desc": "Mythical energy empowers your focus!"},
    {"type": "title", "value": "🔮 Time Lord", "title": "New Title: 🔮 Time Lord", "icon": "fa-clock", "desc": "You have bent time to your disciplined will!"},
    {"type": "title", "value": "⚔️ Task Slayer", "title": "New Title: ⚔️ Task Slayer", "icon": "fa-shield", "desc": "No to-do item stands a chance against you!"},
    {"type": "title", "value": "🌌 Apex Achiever", "title": "New Title: 🌌 Apex Achiever", "icon": "fa-meteor", "desc": "You operate in a league of your own!"}
]

@gamification_bp.route('/user/profile', methods=['GET'])
def get_user_profile():
    user_id = request.args.get('user_id', 1, type=int)
    profile = UserModel.get_profile(user_id)
    if not profile:
        return jsonify({"success": False, "error": "User not found"}), 404
    return jsonify({"success": True, "profile": profile})

@gamification_bp.route('/user/xp', methods=['POST'])
def modify_user_xp():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 1)
    amount = data.get('amount', 0)
    reason = data.get('reason', 'Direct adjustment')

    result = UserModel.modify_xp(user_id, amount, reason)
    if not result:
        return jsonify({"success": False, "error": "User not found"}), 404

    return jsonify({"success": True, "result": result})

@gamification_bp.route('/user/reset', methods=['POST'])
def reset_user_progress():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 1)
    profile = UserModel.reset_progress(user_id)
    return jsonify({
        "success": True,
        "message": "All levels, XP, streaks, and milestones/badges have been reset.",
        "profile": profile
    })

@gamification_bp.route('/user/badges', methods=['GET'])
def get_badges():
    user_id = request.args.get('user_id', 1, type=int)
    badges = BadgeModel.get_user_badges(user_id)
    return jsonify({"success": True, "badges": badges, "total_badges": len(badges)})

@gamification_bp.route('/user/badges', methods=['POST'])
def award_badge():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 1)
    badge_name = data.get('badge_name')
    if not badge_name:
        return jsonify({"success": False, "error": "badge_name is required"}), 400

    awarded = BadgeModel.award_badge(user_id, badge_name)
    if not awarded:
        return jsonify({"success": False, "message": "Badge already unlocked or invalid"}), 200

    profile = UserModel.get_profile(user_id)
    return jsonify({"success": True, "badge": awarded, "profile": profile, "message": f"Awarded badge: {badge_name}"})

@gamification_bp.route('/rewards/chest', methods=['POST'])
def open_reward_chest():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 1)

    profile = UserModel.get_profile(user_id)
    if not profile:
        return jsonify({"success": False, "error": "User not found"}), 404

    reward = random.choice(CHEST_REWARDS)

    if reward["type"] == "xp":
        UserModel.modify_xp(user_id, reward["value"], reason="Mystery Chest Reward")
    elif reward["type"] == "title":
        UserModel.modify_xp(user_id, 25, reason="Mystery Chest Title")

    updated_profile = UserModel.get_profile(user_id)
    return jsonify({
        "success": True,
        "reward": reward,
        "profile": updated_profile
    })
