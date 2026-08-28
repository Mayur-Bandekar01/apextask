from flask import Blueprint, request, jsonify
from backend.models.record import RecordModel

records_bp = Blueprint('records', __name__, url_prefix='/api/records')

@records_bp.route('/weekly', methods=['GET'])
def get_weekly_records():
    user_id = request.args.get('user_id', 1, type=int)
    date_str = request.args.get('date', 'today')
    data = RecordModel.get_weekly_records(user_id, date_str)
    return jsonify({"success": True, "records": data})

@records_bp.route('/monthly', methods=['GET'])
def get_monthly_records():
    user_id = request.args.get('user_id', 1, type=int)
    month_str = request.args.get('month')
    data = RecordModel.get_monthly_records(user_id, month_str)
    return jsonify({"success": True, "records": data})

@records_bp.route('/yearly', methods=['GET'])
def get_yearly_records():
    user_id = request.args.get('user_id', 1, type=int)
    year_str = request.args.get('year')
    data = RecordModel.get_yearly_records(user_id, year_str)
    return jsonify({"success": True, "records": data})
