from flask import Blueprint, jsonify, request, g

try:
    from api.auth import require_auth
    from api.models.challenge import ChallengeModel
except ImportError:
    from auth import require_auth
    from models.challenge import ChallengeModel

challenges_bp = Blueprint('challenges', __name__)

@challenges_bp.route('/challenges', methods=['GET'])
@require_auth
def get_challenges():
    try:
        user_id = getattr(g, 'user_id', 1)
        challenges = ChallengeModel.get_user_challenges(user_id)
        return jsonify({
            "success": True,
            "challenges": challenges
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@challenges_bp.route('/challenges/<int:challenge_id>/claim', methods=['POST'])
@require_auth
def claim_challenge(challenge_id):
    try:
        user_id = getattr(g, 'user_id', 1)
        result = ChallengeModel.claim_reward(challenge_id, user_id)
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

