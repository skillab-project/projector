from collections import Counter
from datetime import date, datetime, timedelta
from typing import List


class TrendAnalytics:
    def __init__(self, engine, tracker, market):
        self.engine = engine
        self.tracker = tracker
        self.market = market

    async def calculate_trends_from_data(self, all_jobs: List[dict], min_date: str, max_date: str):
        mid = self._get_midpoint(min_date, max_date)
        jobs_a = [j for j in all_jobs if j.get("upload_date", "") <= mid]
        jobs_b = [j for j in all_jobs if j.get("upload_date", "") > mid]

        res_a = await self.market.analyze_market_data(jobs_a)
        res_b = await self.market.analyze_market_data(jobs_b)
        return self._compare_periods(res_a, res_b)

    # --- METODO 2: STANDALONE (CON FETCH) ---
    async def calculate_smart_trends(self, base_filters: dict, min_date: str, max_date: str):
        mid = self._get_midpoint(min_date, max_date)
        f_a = {**base_filters, "min_upload_date": min_date, "max_upload_date": mid}
        f_b = {**base_filters, "min_upload_date": mid, "max_upload_date": max_date}  # Semplificato per brevità

        res_a = await self.market.analyze_market_data(await self.tracker.fetch_all_jobs(f_a))
        if self.engine.stop_requested: return self._stop_trend_res()

        res_b = await self.market.analyze_market_data(await self.tracker.fetch_all_jobs(f_b))
        return self._compare_periods(res_a, res_b)

    async def calculate_temporal_projections_from_data(
            self,
            jobs: List[dict],
            min_date: str,
            max_date: str,
            granularity: str = "monthly",
            forecast_periods: int = 1,
            top_k: int = 10,
    ):
        buckets = self._build_period_buckets(min_date, max_date, granularity)
        period_jobs = {bucket["period"]: 0 for bucket in buckets}
        period_skill_counts = {bucket["period"]: Counter() for bucket in buckets}
        total_skill_counts = Counter()

        for job in jobs:
            period = self._period_label(job.get("upload_date"), granularity)
            if period not in period_jobs:
                continue
            period_jobs[period] += 1
            for skill_id in job.get("skills", []):
                skill_key = str(skill_id).strip()
                if not skill_key:
                    continue
                period_skill_counts[period][skill_key] += 1
                total_skill_counts[skill_key] += 1

        periods = []
        previous_jobs = None
        for bucket in buckets:
            period = bucket["period"]
            job_count = period_jobs[period]
            periods.append({
                **bucket,
                "job_count": job_count,
                "growth_vs_previous": self._growth(previous_jobs, job_count),
            })
            previous_jobs = job_count

        top_skill_ids = [skill_id for skill_id, _ in total_skill_counts.most_common(max(top_k, 1))]
        skills = []
        for skill_id in top_skill_ids:
            counts = [period_skill_counts[bucket["period"]][skill_id] for bucket in buckets]
            total_count = sum(counts)
            latest_count = counts[-1] if counts else 0
            previous_count = counts[-2] if len(counts) > 1 else None
            growth_rate = self._growth(previous_count, latest_count)
            skill_info = self.engine.skill_map.get(
                skill_id,
                {"label": skill_id.split("/")[-1], "is_green": False, "is_digital": False},
            )

            series = []
            previous_skill_count = None
            for bucket, count in zip(buckets, counts):
                job_count = period_jobs[bucket["period"]]
                series.append({
                    "period": bucket["period"],
                    "start_date": bucket["start_date"],
                    "end_date": bucket["end_date"],
                    "count": count,
                    "share": round(count / job_count, 4) if job_count else 0.0,
                    "growth_vs_previous": self._growth(previous_skill_count, count),
                })
                previous_skill_count = count

            skills.append({
                "skill_id": skill_id,
                "name": skill_info["label"],
                "total_count": total_count,
                "latest_count": latest_count,
                "growth_rate": growth_rate,
                "trend_type": self._trend_type(growth_rate),
                "is_green": skill_info.get("is_green", False),
                "is_digital": skill_info.get("is_digital", False),
                "series": series,
                "forecast": self._forecast_skill_counts(
                    counts,
                    buckets[-1]["period"] if buckets else None,
                    granularity,
                    forecast_periods,
                ),
            })

        return {
            "window": {
                "min_date": min_date,
                "max_date": max_date,
            },
            "granularity": granularity,
            "forecast_method": "last_delta_baseline",
            "periods": periods,
            "skills": skills,
        }

    def _get_midpoint(self, d1, d2):
        dt1, dt2 = datetime.strptime(d1, "%Y-%m-%d"), datetime.strptime(d2, "%Y-%m-%d")
        return (dt1 + timedelta(days=(dt2 - dt1).days // 2)).strftime("%Y-%m-%d")

    def _build_period_buckets(self, min_date: str, max_date: str, granularity: str):
        start = date.fromisoformat(min_date)
        end = date.fromisoformat(max_date)
        current = self._period_start(start, granularity)
        buckets = []
        while current <= end:
            period_end = min(self._period_end(current, granularity), end)
            buckets.append({
                "period": self._format_period(current, granularity),
                "start_date": current.isoformat(),
                "end_date": period_end.isoformat(),
            })
            current = self._next_period_start(current, granularity)
        return buckets

    def _period_label(self, raw_date, granularity: str):
        if not raw_date:
            return None
        try:
            parsed = date.fromisoformat(str(raw_date)[:10])
        except ValueError:
            return None
        return self._format_period(self._period_start(parsed, granularity), granularity)

    def _period_start(self, value: date, granularity: str):
        if granularity == "yearly":
            return date(value.year, 1, 1)
        if granularity == "quarterly":
            quarter_month = ((value.month - 1) // 3) * 3 + 1
            return date(value.year, quarter_month, 1)
        return date(value.year, value.month, 1)

    def _period_end(self, value: date, granularity: str):
        return self._next_period_start(value, granularity) - timedelta(days=1)

    def _next_period_start(self, value: date, granularity: str):
        if granularity == "yearly":
            return date(value.year + 1, 1, 1)
        if granularity == "quarterly":
            month = value.month + 3
        else:
            month = value.month + 1
        year = value.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        return date(year, month, 1)

    def _format_period(self, value: date, granularity: str):
        if granularity == "yearly":
            return str(value.year)
        if granularity == "quarterly":
            return f"{value.year}-Q{((value.month - 1) // 3) + 1}"
        return f"{value.year}-{value.month:02d}"

    def _growth(self, previous, current):
        if previous is None:
            return None
        if previous == 0 and current > 0:
            return "new_entry"
        if previous == 0:
            return 0.0
        return round(((current - previous) / previous) * 100, 2)

    def _trend_type(self, growth):
        if growth == "new_entry":
            return "emerging"
        if growth is None or growth == 0:
            return "stable"
        return "emerging" if growth > 0 else "declining"

    def _forecast_skill_counts(self, counts, latest_period, granularity: str, forecast_periods: int):
        if not latest_period:
            return []
        deltas = [current - previous for previous, current in zip(counts, counts[1:])]
        recent_deltas = deltas[-3:]
        average_delta = round(sum(recent_deltas) / len(recent_deltas), 2) if recent_deltas else 0.0
        latest_count = counts[-1] if counts else 0
        forecasts = []
        period_start = self._next_period_start(self._parse_period_start(latest_period, granularity), granularity)
        for step in range(1, max(forecast_periods, 0) + 1):
            projected = max(0.0, latest_count + average_delta * step)
            forecasts.append({
                "period": self._format_period(period_start, granularity),
                "projected_count": round(projected, 2),
                "method": "last_delta_baseline",
            })
            period_start = self._next_period_start(period_start, granularity)
        return forecasts

    def _parse_period_start(self, period: str, granularity: str):
        if granularity == "yearly":
            return date(int(period), 1, 1)
        if granularity == "quarterly":
            year, quarter = period.split("-Q")
            return date(int(year), (int(quarter) - 1) * 3 + 1, 1)
        return date.fromisoformat(f"{period}-01")

    def _compare_periods(self, res_a, res_b):
        """Calcola i delta e arricchisce con Intelligence (Phase 1)."""
        dict_a = {s["skill_id"]: s for s in res_a["rankings"]["skills"]}
        dict_b = {s["skill_id"]: s for s in res_b["rankings"]["skills"]}
        trends = []

        for s_id in set(list(dict_a.keys()) + list(dict_b.keys())):
            v_a = dict_a.get(s_id, {}).get("frequency", 0)
            info_b = dict_b.get(s_id, {})
            v_b = info_b.get("frequency", 0)

            name = info_b.get("name") or dict_a.get(s_id, {}).get("name")
            primary_sector = info_b.get("primary_sector", "N/D")

            if v_a == 0:
                growth, t_type = "new_entry", "emerging"
            elif v_b == 0:
                growth, t_type = -100.0, "declining"
            else:
                growth = round(((v_b - v_a) / v_a) * 100, 2)
                t_type = "emerging" if growth > 0 else "declining" if growth < 0 else "stable"

            trends.append({
                "name": name,
                "growth": growth,
                "trend_type": t_type,
                "primary_sector": primary_sector,
                "is_green": info_b.get("is_green", False),
                "is_digital": info_b.get("is_digital", False)
            })

        trends.sort(key=lambda x: float('inf') if x["growth"] == "new_entry" else x["growth"], reverse=True)
        vol_growth = round(((res_b["total_jobs"] - res_a["total_jobs"]) / res_a["total_jobs"] * 100), 2) if res_a[
                                                                                                                "total_jobs"] > 0 else 0

        return {
            "market_health": {
                "status": "expanding" if vol_growth > 0 else "shrinking",
                "volume_growth_percentage": vol_growth
            },
            "trends": trends
        }
