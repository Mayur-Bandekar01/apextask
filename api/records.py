import datetime
from flask import Blueprint, request, jsonify, g
from api.models.record import RecordModel
from api.auth import require_auth

records_bp = Blueprint('records', __name__, url_prefix='/api/records')

@records_bp.route('/weekly', methods=['GET'])
@require_auth
def get_weekly_records():
    user_id = getattr(g, 'user_id', 1)
    ref_date = request.args.get('date', 'today')
    records = RecordModel.get_weekly_records(user_id, ref_date)
    return jsonify({"success": True, "records": records})

@records_bp.route('/monthly', methods=['GET'])
@require_auth
def get_monthly_records():
    user_id = getattr(g, 'user_id', 1)
    month = request.args.get('month')
    records = RecordModel.get_monthly_records(user_id, month)
    return jsonify({"success": True, "records": records})

@records_bp.route('/yearly', methods=['GET'])
@require_auth
def get_yearly_records():
    user_id = getattr(g, 'user_id', 1)
    year = request.args.get('year')
    records = RecordModel.get_yearly_records(user_id, year)
    return jsonify({"success": True, "records": records})
