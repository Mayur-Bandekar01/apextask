import datetime
import functools
import jwt
import bcrypt
from flask import Blueprint, request, jsonify, g

try:
    from api.config import Config
    from api.models.user import UserModel
except ImportError:
    from config import Config
    from models.user import UserModel

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def verify_password(plain_password, stored_password_or_hash):
    """Compares plain password against stored bcrypt hash or fallback plain string."""
    if not stored_password_or_hash or not plain_password:
        return False

    stored = stored_password_or_hash.strip()
    # Check if stored password is a bcrypt hash
    if stored.startswith('$2b$') or stored.startswith('$2a$') or stored.startswith('$2y$'):
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), stored.encode('utf-8'))
        except Exception:
            return False
    # Direct comparison for plain text configuration
    return plain_password == stored

def create_jwt_token(user):
    """Generates signed JWT token with 7-day expiration."""
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=Config.JWT_EXPIRY_DAYS)
    payload = {
        "user_id": user["id"],
        "username": user["username"],
        "exp": exp,
        "iat": datetime.datetime.now(datetime.timezone.utc)
    }
    token = jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")
    return token

def decode_jwt_token(token):
    """Decodes and validates JWT token."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def require_auth(f):
    """Decorator to enforce single-user JWT authentication on API routes."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = None

        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        elif request.args.get('token'):
            token = request.args.get('token').strip()

        if not token:
            return jsonify({"success": False, "error": "Authentication token missing"}), 401

        payload = decode_jwt_token(token)
        if not payload:
            return jsonify({"success": False, "error": "Invalid or expired token"}), 401

        g.user_id = payload.get("user_id", 1)
        g.username = payload.get("username", Config.APP_USERNAME)

        return f(*args, **kwargs)
    return decorated

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required"}), 400

    # Validate against configured single user credentials
    if username.lower() != Config.APP_USERNAME.lower() or not verify_password(password, Config.APP_PASSWORD):
        return jsonify({"success": False, "error": "Invalid username or password"}), 401

    # Fetch or ensure user profile exists in database
    user = UserModel.get_user_by_username(Config.APP_USERNAME)
    if not user:
        # Fallback to user ID 1
        user = UserModel.get_user(1)

    if not user:
        user = {"id": 1, "username": Config.APP_USERNAME}

    token = create_jwt_token(user)
    profile = UserModel.get_profile(user["id"])

    return jsonify({
        "success": True,
        "message": "Login successful",
        "token": token,
        "expires_in_days": Config.JWT_EXPIRY_DAYS,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "profile": profile
        }
    })

@auth_bp.route('/verify', methods=['GET'])
@require_auth
def verify_token():
    user_id = getattr(g, 'user_id', 1)
    profile = UserModel.get_profile(user_id)
    return jsonify({
        "success": True,
        "valid": True,
        "user_id": user_id,
        "username": getattr(g, 'username', Config.APP_USERNAME),
        "profile": profile
    })
