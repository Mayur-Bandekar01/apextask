import datetime
import calendar
from backend.db import get_db_connection

class RecordModel:
    @staticmethod
    def get_weekly_records(user_id, date_str=None):
        if not date_str or date_str == "today":
            target_date = datetime.date.today()
        else:
            try:
                target_date = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            except Exception:
                target_date = datetime.date.today()

        start_of_week = target_date - datetime.timedelta(days=target_date.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=6)

        conn = get_db_connection()
        days_data = []
        best_day = None
        max_completed = -1
        total_week_completed = 0
        total_week_xp = 0

        with conn.cursor() as cur:
            for i in range(7):
                day = start_of_week + datetime.timedelta(days=i)
                day_str = day.isoformat()

                cur.execute("""
                    SELECT 
                        COUNT(CASE WHEN status = 'complete' THEN 1 END) as completed,
                        COUNT(CASE WHEN status = 'missed' THEN 1 END) as missed,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending
                    FROM tasks 
                    WHERE user_id = %s AND original_date = %s;
                """, (user_id, day_str))
                task_stats = cur.fetchone() or {"completed": 0, "missed": 0, "pending": 0}

                cur.execute("""
                    SELECT tasks_completed, tasks_missed, xp_earned, focus_time 
                    FROM daily_records 
                    WHERE user_id = %s AND record_date = %s;
                """, (user_id, day_str))
                rec = cur.fetchone()

                completed = max(task_stats.get("completed", 0), rec.get("tasks_completed", 0) if rec else 0)
                missed = max(task_stats.get("missed", 0), rec.get("tasks_missed", 0) if rec else 0)
                xp = rec.get("xp_earned", 0) if rec else (completed * 25)
                focus_time = rec.get("focus_time", 0) if rec else (completed * 25)

                total_week_completed += completed
                total_week_xp += xp

                day_info = {
                    "date": day_str,
                    "day_name": day.strftime("%a"),
                    "full_day_name": day.strftime("%A"),
                    "is_today": day == datetime.date.today(),
                    "tasks_completed": completed,
                    "tasks_missed": missed,
                    "tasks_pending": task_stats.get("pending", 0),
                    "xp_earned": xp,
                    "focus_time": focus_time
                }
                days_data.append(day_info)

                if completed > max_completed:
                    max_completed = completed
                    best_day = day_info

        conn.close()

        prev_week = (start_of_week - datetime.timedelta(days=7)).isoformat()
        next_week = (start_of_week + datetime.timedelta(days=7)).isoformat()

        return {
            "start_date": start_of_week.isoformat(),
            "end_date": end_of_week.isoformat(),
            "prev_week": prev_week,
            "next_week": next_week,
            "days": days_data,
            "best_day": best_day if max_completed > 0 else (days_data[0] if days_data else None),
            "total_completed": total_week_completed,
            "total_xp": total_week_xp
        }

    @staticmethod
    def get_monthly_records(user_id, month_str=None):
        if not month_str:
            today = datetime.date.today()
            year = today.year
            month = today.month
        else:
            try:
                parts = month_str.split("-")
                year = int(parts[0])
                month = int(parts[1])
            except Exception:
                today = datetime.date.today()
                year = today.year
                month = today.month

        num_days = calendar.monthrange(year, month)[1]
        start_date = datetime.date(year, month, 1)
        end_date = datetime.date(year, month, num_days)

        conn = get_db_connection()
        heatmap_days = []
        total_completed = 0
        most_productive_count = 0
        most_productive_date = None

        with conn.cursor() as cur:
            cur.execute("""
                SELECT original_date, status, COUNT(*) as count 
                FROM tasks 
                WHERE user_id = %s AND original_date >= %s AND original_date <= %s 
                GROUP BY original_date, status;
            """, (user_id, start_date.isoformat(), end_date.isoformat()))
            task_rows = cur.fetchall()

            date_map = {}
            for r in task_rows:
                d = str(r.get("original_date") or "")[:10]
                if d not in date_map:
                    date_map[d] = {"complete": 0, "pending": 0, "missed": 0}
                st = r.get("status", "pending")
                date_map[d][st] = date_map[d].get(st, 0) + r.get("count", 0)

            for d in range(1, num_days + 1):
                cur_date = datetime.date(year, month, d)
                cur_date_str = cur_date.isoformat()
                stats = date_map.get(cur_date_str, {"complete": 0, "pending": 0, "missed": 0})
                c = stats.get("complete", 0)
                total_completed += c

                if c == 0:
                    intensity = 0
                elif c <= 2:
                    intensity = 1
                elif c <= 4:
                    intensity = 2
                elif c <= 7:
                    intensity = 3
                else:
                    intensity = 4

                if c > most_productive_count:
                    most_productive_count = c
                    most_productive_date = cur_date_str

                heatmap_days.append({
                    "date": cur_date_str,
                    "day": d,
                    "weekday": cur_date.weekday(),
                    "completed": c,
                    "pending": stats.get("pending", 0),
                    "missed": stats.get("missed", 0),
                    "intensity": intensity,
                    "is_today": cur_date == datetime.date.today()
                })

        conn.close()

        prev_m = datetime.date(year, month, 1) - datetime.timedelta(days=1)
        next_m = end_date + datetime.timedelta(days=1)
        prev_month_str = f"{prev_m.year:04d}-{prev_m.month:02d}"
        next_month_str = f"{next_m.year:04d}-{next_m.month:02d}"

        avg_daily = round(total_completed / num_days, 1)

        return {
            "month": f"{year:04d}-{month:02d}",
            "month_name": calendar.month_name[month],
            "year": year,
            "prev_month": prev_month_str,
            "next_month": next_month_str,
            "days": heatmap_days,
            "summary": {
                "total_completed": total_completed,
                "avg_daily": avg_daily,
                "most_productive_date": most_productive_date or start_date.isoformat(),
                "most_productive_count": most_productive_count
            }
        }

    @staticmethod
    def get_yearly_records(user_id, year_str=None):
        if not year_str:
            year = datetime.date.today().year
        else:
            try:
                year = int(year_str)
            except Exception:
                year = datetime.date.today().year

        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year, 12, 31)

        conn = get_db_connection()
        monthly_trend = [0] * 12
        total_yearly_completed = 0
        total_focus_time = 0
        total_xp = 0

        with conn.cursor() as cur:
            cur.execute("""
                SELECT original_date, status, COUNT(*) as count 
                FROM tasks 
                WHERE user_id = %s AND original_date >= %s AND original_date <= %s
                GROUP BY original_date, status;
            """, (user_id, start_date.isoformat(), end_date.isoformat()))
            rows = cur.fetchall()

            day_counts = {}
            for r in rows:
                if r.get("status") == "complete":
                    d_str = str(r.get("original_date") or "")[:10]
                    cnt = r.get("count", 0)
                    day_counts[d_str] = day_counts.get(d_str, 0) + cnt
                    total_yearly_completed += cnt
                    try:
                        m_idx = int(d_str[5:7]) - 1
                        monthly_trend[m_idx] += cnt
                    except Exception:
                        pass

            cur.execute("""
                SELECT SUM(xp_earned) as total_xp, SUM(focus_time) as total_focus 
                FROM daily_records 
                WHERE user_id = %s AND record_date >= %s AND record_date <= %s;
            """, (user_id, start_date.isoformat(), end_date.isoformat()))
            rec_sums = cur.fetchone()
            if rec_sums:
                total_xp = rec_sums.get("total_xp") or (total_yearly_completed * 25)
                total_focus_time = rec_sums.get("total_focus") or (total_yearly_completed * 25)

            cur.execute("SELECT COUNT(*) as badge_count FROM badges WHERE user_id = %s;", (user_id,))
            b_row = cur.fetchone()
            badge_count = b_row.get("badge_count", 0) if b_row else 0

        conn.close()

        heatmap_days = []
        cur_d = start_date
        while cur_d <= end_date:
            cur_d_str = cur_d.isoformat()
            c = day_counts.get(cur_d_str, 0)
            if c == 0:
                intensity = 0
            elif c <= 2:
                intensity = 1
            elif c <= 4:
                intensity = 2
            elif c <= 7:
                intensity = 3
            else:
                intensity = 4

            heatmap_days.append({
                "date": cur_d_str,
                "month": cur_d.month,
                "day": cur_d.day,
                "weekday": cur_d.weekday(),
                "week_number": cur_d.isocalendar()[1],
                "completed": c,
                "intensity": intensity
            })
            cur_d += datetime.timedelta(days=1)

        months_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        return {
            "year": year,
            "prev_year": year - 1,
            "next_year": year + 1,
            "heatmap": heatmap_days,
            "trend": {
                "labels": months_labels,
                "data": monthly_trend
            },
            "stats": {
                "total_completed": total_yearly_completed,
                "total_focus_time_minutes": total_focus_time,
                "total_xp": total_xp,
                "badges_unlocked": badge_count
            }
        }
