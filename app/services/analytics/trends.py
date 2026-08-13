from datetime import datetime, timedelta
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

    def _get_midpoint(self, d1, d2):
        dt1, dt2 = datetime.strptime(d1, "%Y-%m-%d"), datetime.strptime(d2, "%Y-%m-%d")
        return (dt1 + timedelta(days=(dt2 - dt1).days // 2)).strftime("%Y-%m-%d")



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
