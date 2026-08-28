import datetime
import calendar
from api.db import get_db_connection

class RecordModel:
    @staticmethod
    def get_weekly_records(user_id=1, reference_date=None):
        if not reference_date or reference_date == "today":
            ref_dt = datetime.date.today()
        else:
            try:
                ref_dt = datetime.datetime.strptime(reference_date[:10], "%Y-%m-%d").date()
            except Exception:
                ref_dt = datetime.date.today()

        # Find Monday of this week
        start_date = ref_dt - datetime.timedelta(days=ref_dt.weekday())
        end_date = start_date + datetime.timedelta(days=6)

        dates = [start_date + datetime.timedelta(days=i) for i in range(7)]
        date_strs = [d.isoformat() for d in dates]

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT original_date, status, COUNT(*) as cnt 
                FROM tasks 
                WHERE user_id = %s AND original_date >= %s AND original_date <= %s
                GROUP BY original_date, status;
            """, (user_id, start_date.isoformat(), end_date.isoformat()))
            task_rows = cur.fetchall()

            cur.execute("""
                SELECT record_date, xp_earned, focus_time 
                FROM daily_records 
                WHERE user_id = %s AND record_date >= %s AND record_date <= %s;
            """, (user_id, start_date.isoformat(), end_date.isoformat()))
            daily_rows = cur.fetchall()
        conn.close()

        # Organize by date
        tasks_by_date = {d: {"complete": 0, "pending": 0, "missed": 0} for d in date_strs}
        for row in task_rows:
            d_str = row["original_date"]
            if isinstance(d_str, (datetime.date, datetime.datetime)):
                d_str = d_str.strftime("%Y-%m-%d")
            st = row["status"]
            if d_str in tasks_by_date and st in tasks_by_date[d_str]:
                tasks_by_date[d_str][st] = row.get("cnt", 0)

        daily_by_date = {d: {"xp_earned": 0, "focus_time": 0} for d in date_strs}
        for row in daily_rows:
            d_str = row["record_date"]
            if isinstance(d_str, (datetime.date, datetime.datetime)):
                d_str = d_str.strftime("%Y-%m-%d")
            if d_str in daily_by_date:
                daily_by_date[d_str]["xp_earned"] = row.get("xp_earned", 0)
                daily_by_date[d_str]["focus_time"] = row.get("focus_time", 0)

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        full_day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        days_data = []
        best_day = None
        max_completed = -1
        total_week_completed = 0
        total_week_xp = 0

        today_str = datetime.date.today().isoformat()

        for idx, d_dt in enumerate(dates):
            d_str = d_dt.isoformat()
            completed = tasks_by_date[d_str]["complete"]
            missed = tasks_by_date[d_str]["missed"]
            pending = tasks_by_date[d_str]["pending"]
            xp = daily_by_date[d_str]["xp_earned"]
            focus = daily_by_date[d_str]["focus_time"]

            total_week_completed += completed
            total_week_xp += xp

            if completed > max_completed:
                max_completed = completed
                best_day = {
                    "date": d_str,
                    "day_name": day_names[idx],
                    "full_day_name": full_day_names[idx],
                    "tasks_completed": completed
                }

            days_data.append({
                "date": d_str,
                "day_name": day_names[idx],
                "full_day_name": full_day_names[idx],
                "is_today": (d_str == today_str),
                "tasks_completed": completed,
                "tasks_missed": missed,
                "tasks_pending": pending,
                "xp_earned": xp,
                "focus_time": focus
            })

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "prev_week": (start_date - datetime.timedelta(days=7)).isoformat(),
            "next_week": (start_date + datetime.timedelta(days=7)).isoformat(),
            "days": days_data,
            "best_day": best_day if max_completed > 0 else (days_data[0] if days_data else None),
            "total_completed": total_week_completed,
            "total_xp": total_week_xp
        }

    @staticmethod
    def get_monthly_records(user_id=1, year_month=None):
        if not year_month:
            today = datetime.date.today()
            year = today.year
            month = today.month
        else:
            parts = year_month.split("-")
            year = int(parts[0])
            month = int(parts[1])

        num_days = calendar.monthrange(year, month)[1]
        start_date = datetime.date(year, month, 1)
        end_date = datetime.date(year, month, num_days)

        date_strs = [datetime.date(year, month, day).isoformat() for day in range(1, num_days + 1)]

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT original_date, status, COUNT(*) as cnt 
                FROM tasks 
                WHERE user_id = %s AND original_date >= %s AND original_date <= %s
                GROUP BY original_date, status;
            """, (user_id, start_date.isoformat(), end_date.isoformat()))
            task_rows = cur.fetchall()

            cur.execute("""
                SELECT record_date, xp_earned, focus_time 
                FROM daily_records 
                WHERE user_id = %s AND record_date >= %s AND record_date <= %s;
            """, (user_id, start_date.isoformat(), end_date.isoformat()))
            daily_rows = cur.fetchall()
        conn.close()

        tasks_map = {d: {"complete": 0, "pending": 0, "missed": 0} for d in date_strs}
        for row in task_rows:
            d_str = row["original_date"]
            if isinstance(d_str, (datetime.date, datetime.datetime)):
                d_str = d_str.strftime("%Y-%m-%d")
            st = row["status"]
            if d_str in tasks_map and st in tasks_map[d_str]:
                tasks_map[d_str][st] = row.get("cnt", 0)

        daily_map = {d: {"xp_earned": 0, "focus_time": 0} for d in date_strs}
        for row in daily_rows:
            d_str = row["record_date"]
            if isinstance(d_str, (datetime.date, datetime.datetime)):
                d_str = d_str.strftime("%Y-%m-%d")
            if d_str in daily_map:
                daily_map[d_str]["xp_earned"] = row.get("xp_earned", 0)
                daily_map[d_str]["focus_time"] = row.get("focus_time", 0)

        days = []
        total_completed = 0
        total_xp = 0
        most_productive_date = None
        most_productive_count = -1

        today_str = datetime.date.today().isoformat()

        for day in range(1, num_days + 1):
            d_str = datetime.date(year, month, day).isoformat()
            comp = tasks_map[d_str]["complete"]
            total_completed += comp
            total_xp += daily_map[d_str]["xp_earned"]

            if comp > most_productive_count:
                most_productive_count = comp
                most_productive_date = d_str

            # Intensity calculation: 0 = 0, 1 = 1-2, 2 = 3-4, 3 = 5-7, 4 = 8+
            if comp == 0:
                intensity = 0
            elif comp <= 2:
                intensity = 1
            elif comp <= 4:
                intensity = 2
            elif comp <= 7:
                intensity = 3
            else:
                intensity = 4

            days.append({
                "day": day,
                "date": d_str,
                "is_today": (d_str == today_str),
                "completed": comp,
                "pending": tasks_map[d_str]["pending"],
                "missed": tasks_map[d_str]["missed"],
                "xp_earned": daily_map[d_str]["xp_earned"],
                "intensity": intensity
            })

        # Calculate previous / next month strings
        prev_dt = start_date - datetime.timedelta(days=1)
        prev_month_str = f"{prev_dt.year:04d}-{prev_dt.month:02d}"

        next_dt = end_date + datetime.timedelta(days=1)
        next_month_str = f"{next_dt.year:04d}-{next_dt.month:02d}"

        return {
            "year": year,
            "month": f"{year:04d}-{month:02d}",
            "month_name": calendar.month_name[month],
            "prev_month": prev_month_str,
            "next_month": next_month_str,
            "days": days,
            "summary": {
                "total_completed": total_completed,
                "total_xp": total_xp,
                "avg_daily": round(total_completed / num_days, 1),
                "most_productive_date": most_productive_date,
                "most_productive_count": most_productive_count if most_productive_count > 0 else 0
            }
        }

    @staticmethod
    def get_yearly_records(user_id=1, year=None):
        if not year:
            year = datetime.date.today().year
        else:
            year = int(year)

        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year, 12, 31)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT original_date, COUNT(*) as cnt 
                FROM tasks 
                WHERE user_id = %s AND status = 'complete' 
                  AND original_date >= %s AND original_date <= %s
                GROUP BY original_date;
            """, (user_id, start_date.isoformat(), end_date.isoformat()))
            completed_rows = cur.fetchall()

            cur.execute("""
                SELECT 
                    SUM(tasks_completed) as total_completed,
                    SUM(xp_earned) as total_xp,
                    SUM(focus_time) as total_focus
                FROM daily_records 
                WHERE user_id = %s AND record_date >= %s AND record_date <= %s;
            """, (user_id, start_date.isoformat(), end_date.isoformat()))
            summary_row = cur.fetchone()

            cur.execute("SELECT COUNT(*) as cnt FROM badges WHERE user_id = %s;", (user_id,))
            badge_cnt_row = cur.fetchone()
            badges_count = badge_cnt_row.get("cnt", 0) if badge_cnt_row else 0
        conn.close()

        completed_map = {}
        for row in completed_rows:
            d_str = row["original_date"]
            if isinstance(d_str, (datetime.date, datetime.datetime)):
                d_str = d_str.strftime("%Y-%m-%d")
            completed_map[d_str] = row.get("cnt", 0)

        # 365/366 day heatmap data
        heatmap_days = []
        curr_dt = start_date
        while curr_dt <= end_date:
            d_str = curr_dt.isoformat()
            comp = completed_map.get(d_str, 0)
            if comp == 0: intensity = 0
            elif comp <= 2: intensity = 1
            elif comp <= 4: intensity = 2
            elif comp <= 7: intensity = 3
            else: intensity = 4

            heatmap_days.append({
                "date": d_str,
                "completed": comp,
                "intensity": intensity
            })
            curr_dt += datetime.timedelta(days=1)

        # Monthly aggregate trend for chart
        monthly_labels = [calendar.month_abbr[m] for m in range(1, 13)]
        monthly_counts = [0] * 12

        for d_str, count in completed_map.items():
            try:
                m = int(d_str.split("-")[1]) - 1
                if 0 <= m < 12:
                    monthly_counts[m] += count
            except Exception:
                pass

        total_comp = summary_row.get("total_completed", 0) if summary_row and summary_row.get("total_completed") is not None else sum(monthly_counts)
        total_xp = summary_row.get("total_xp", 0) if summary_row and summary_row.get("total_xp") is not None else 0
        total_focus = summary_row.get("total_focus", 0) if summary_row and summary_row.get("total_focus") is not None else 0

        return {
            "year": year,
            "prev_year": year - 1,
            "next_year": year + 1,
            "stats": {
                "total_completed": total_comp,
                "total_xp": total_xp,
                "total_focus_time_minutes": total_focus,
                "badges_unlocked": badges_count
            },
            "heatmap": heatmap_days,
            "trend": {
                "labels": monthly_labels,
                "data": monthly_counts
            }
        }
