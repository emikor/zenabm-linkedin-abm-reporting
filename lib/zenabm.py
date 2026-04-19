"""
zenabm.py — Comprehensive ZenABM API client

All public methods return plain Python dicts/lists (JSON-serialisable).
Pagination is handled transparently via _get_all_pages().

Format detection note
---------------------
Campaign names embed a format token: '- TLA -', '- Image -', '- Video -',
'- Carousel -', '- Text -'. TLA "clicks" count ALL engagement clicks
(likes, shares, comments, link clicks combined), so TLA CTR (8-11%) is NOT
comparable to Image/Video CTR (link clicks only). Always report them separately.
"""

import re
import statistics
from typing import Optional

import requests

from .config import get_config, setup_check

# ---------------------------------------------------------------------------
# Format detection helpers
# ---------------------------------------------------------------------------

_FORMAT_PATTERNS = [
    (re.compile(r"[-\s]+TLA[-\s]+", re.IGNORECASE), "TLA"),
    (re.compile(r"[-\s]+Image[-\s]+", re.IGNORECASE), "Image"),
    (re.compile(r"[-\s]+Video[-\s]+", re.IGNORECASE), "Video"),
    (re.compile(r"[-\s]+Carousel[-\s]+", re.IGNORECASE), "Carousel"),
    (re.compile(r"[-\s]+Text[-\s]+", re.IGNORECASE), "Text"),
]


def detect_format(campaign_name: str) -> str:
    """
    Detect ad format from campaign name token.
    Returns one of: 'TLA' | 'Image' | 'Video' | 'Carousel' | 'Text' | 'Other'

    TLA (Thought Leadership Ads) clicks = ALL engagement clicks;
    use engagements/impressions as the engagement rate, NOT click CTR.
    """
    for pattern, label in _FORMAT_PATTERNS:
        if pattern.search(campaign_name or ""):
            return label
    return "Other"


# ---------------------------------------------------------------------------
# ZenABMClient
# ---------------------------------------------------------------------------


class ZenABMClient:
    """
    Client for the ZenABM REST API.

    Instantiated with credentials from .env via config.get_config().
    All methods raise requests.HTTPError on API errors.
    """

    def __init__(self):
        cfg = setup_check()
        self.base_url = cfg["base_url"]
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {cfg['token']}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make a GET request and return the parsed JSON body."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = self.session.get(url, params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _get_all_pages(self, path: str, params: dict, data_key: str = "data", page_size: int = 100) -> list:
        """
        Fetch all pages from a paginated endpoint.

        Assumes the API supports pageSize / page (or offset) pagination
        and returns a 'pagination' key with 'totalCount'.
        """
        params = dict(params)
        params["pageSize"] = page_size
        params["page"] = 1

        all_items: list = []

        while True:
            body = self._get(path, params)
            items = body.get(data_key, [])
            all_items.extend(items)

            pagination = body.get("pagination", {})
            total = pagination.get("totalCount", len(all_items))

            if len(all_items) >= total or not items:
                break

            params["page"] = params["page"] + 1

        return all_items

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_overview(self, start: str, end: str) -> dict:
        """
        GET /linkedin-metrics?startDate=&endDate=

        Returns aggregated headline metrics:
          costInUsd, impressions, clicks, engagements
        along with computed CTR, CPC, CPM, engagement_rate.
        """
        body = self._get("/linkedin-metrics", {"startDate": start, "endDate": end})
        data = body.get("data", body)

        impressions = data.get("impressions", 0) or 0
        clicks = data.get("clicks", 0) or 0
        engagements = data.get("engagements", 0) or 0
        spend = data.get("costInUsd", 0) or 0

        return {
            "start": start,
            "end": end,
            "costInUsd": spend,
            "impressions": impressions,
            "clicks": clicks,
            "engagements": engagements,
            "ctr": round(clicks / impressions * 100, 3) if impressions else 0,
            "cpc": round(spend / clicks, 2) if clicks else 0,
            "cpm": round(spend / impressions * 1000, 2) if impressions else 0,
            "engagement_rate": round(engagements / impressions * 100, 3) if impressions else 0,
        }

    def get_wow_metrics(
        self,
        current_start: str,
        current_end: str,
        prev_start: str,
        prev_end: str,
    ) -> dict:
        """
        Fetch /linkedin-metrics for two periods and return both alongside
        percentage changes for each metric.

        Returns:
          {
            "current": {...overview metrics...},
            "previous": {...overview metrics...},
            "changes": {metric_name: pct_change_float, ...}
          }
        """
        current = self.get_overview(current_start, current_end)
        previous = self.get_overview(prev_start, prev_end)

        def pct_change(new_val, old_val):
            if not old_val:
                return None  # undefined — avoid divide-by-zero
            return round((new_val - old_val) / old_val * 100, 1)

        metrics = ["costInUsd", "impressions", "clicks", "engagements", "ctr", "cpc", "cpm", "engagement_rate"]
        changes = {m: pct_change(current[m], previous[m]) for m in metrics}

        return {"current": current, "previous": previous, "changes": changes}

    def get_campaign_groups(self, start: str, end: str) -> list:
        """
        GET /campaign-groups?period=START_END&pageSize=100

        Returns list of LinkedIn Campaign Groups with full metrics.
        Each item: {id, name, numberOfCampaigns, numberOfCompanies,
                    impressions, clicks, engagements, costInUsd,
                    conversions, clickConversions, viewConversions,
                    conversionRate}
        """
        period = f"{start}_{end}"
        return self._get_all_pages(
            "/campaign-groups",
            {"period": period},
            data_key="data",
        )

    def get_campaign_group_weekly(self, group_id: str, start: str, end: str) -> dict:
        """
        GET /campaign-groups/{id}/overview?period=START_END

        Returns {summary: {...}, weeklyData: [{weekStart, weekEnd,
                impressions, clicks, engagements, costInUsd, conversions}]}
        """
        period = f"{start}_{end}"
        body = self._get(f"/campaign-groups/{group_id}/overview", {"period": period})
        return body.get("data", body)

    def get_ad_sets(self, start: str, end: str) -> list:
        """
        GET /campaigns?period=START_END&pageSize=100

        Returns list of ad sets (LinkedIn campaigns). Each item includes:
          {id, name, status, impressions, clicks, engagements,
           costInUsd, conversions, conversionRate}

        'format' is injected by detect_format(name) for each item.

        IMPORTANT: TLA ad sets report ALL engagement types as 'clicks';
        do NOT compare TLA click CTR to Image/Video click CTR.
        """
        period = f"{start}_{end}"
        items = self._get_all_pages(
            "/campaigns",
            {"period": period},
            data_key="data",
        )
        for item in items:
            item["format"] = detect_format(item.get("name", ""))
        return items

    def get_ad_set_weekly(self, adset_id: str, start: str, end: str) -> dict:
        """
        GET /campaigns/{id}/overview?period=START_END

        Returns {summary: {...}, weeklyData: [{weekStart, weekEnd,
                impressions, clicks, engagements, costInUsd, conversions}]}
        """
        period = f"{start}_{end}"
        body = self._get(f"/campaigns/{adset_id}/overview", {"period": period})
        return body.get("data", body)

    def get_companies(
        self,
        start: str,
        end: str,
        sort_by: str = "clicks",
        limit: int = 50,
    ) -> list:
        """
        GET /companies?startDate=&endDate=&pageSize=&sortBy=&sortOrder=desc

        Returns up to `limit` companies sorted by `sort_by`.
        Each item: {id, name, country, impressions, clicks, engagements,
                    costInUsd, abmStage: {name}, intents: [{name}],
                    abmCampaigns: [{name}], currentEngagementScore, exclusion}
        """
        body = self._get(
            "/companies",
            {
                "startDate": start,
                "endDate": end,
                "pageSize": limit,
                "sortBy": sort_by,
                "sortOrder": "desc",
            },
        )
        return body.get("data", [])

    def get_deals(self, start: str, end: str) -> list:
        """
        GET /deals?dateFrom=&dateTo=&pageSize=100

        Returns all deals with attribution data.
        Each item: {id, dealName, company: {name}, amount, linkedinInfluenced,
                    abmInfluenced, stage: {name}, campaigns: [{name}],
                    impressionsBeforeDeal, clicksBeforeDeal, engagementsBeforeDeal}
        """
        return self._get_all_pages(
            "/deals",
            {"dateFrom": start, "dateTo": end},
            data_key="data",
        )

    def get_abm_stages(self) -> list:
        """
        GET /abm-stages

        Returns [{id, name, color, displayOrder}] for all ABM stages.
        """
        body = self._get("/abm-stages")
        return body.get("data", [])

    def get_companies_entering_stage(self, stage_id: str, start: str, end: str) -> list:
        """
        GET /abm-stages/{id}/companies-entering?dateFrom=&dateTo=&pageSize=100

        Returns companies that newly entered this stage during the period.
        """
        return self._get_all_pages(
            f"/abm-stages/{stage_id}/companies-entering",
            {"dateFrom": start, "dateTo": end},
            data_key="data",
        )

    def get_stage_history(self, stage_id: str, start: str, end: str) -> list:
        """
        GET /abm-stages/{id}/history?dateFrom=&dateTo=&pageSize=100

        Returns the stage transition log for this stage.
        """
        return self._get_all_pages(
            f"/abm-stages/{stage_id}/history",
            {"dateFrom": start, "dateTo": end},
            data_key="data",
        )

    def get_ad_spend(self, start: str, end: str) -> list:
        """
        GET /ad-spend?startDate=&endDate=&pageSize=100

        Returns monthly spend breakdown per campaign.
        Each item: {campaignName, year, month, costInUsd,
                    impressions, clicks, engagements}
        """
        return self._get_all_pages(
            "/ad-spend",
            {"startDate": start, "endDate": end},
            data_key="data",
        )

    def get_job_titles(self, start: str, end: str, limit: int = 15) -> list:
        """
        GET /job-titles?period=START_END&pageSize=&sortBy=clicks&sortOrder=desc

        Returns persona engagement sorted by clicks.
        """
        period = f"{start}_{end}"
        body = self._get(
            "/job-titles",
            {
                "period": period,
                "pageSize": limit,
                "sortBy": "clicks",
                "sortOrder": "desc",
            },
        )
        return body.get("data", body) if isinstance(body, dict) else body

    def get_abm_campaigns(self) -> list:
        """
        GET /abm-campaigns

        Returns list of ABM campaigns (ZenABM's campaign groups / Zena groups).
        """
        body = self._get("/abm-campaigns")
        return body.get("data", body) if isinstance(body, dict) else body

    def get_intents(self) -> list:
        """
        GET /intents

        Returns available intent signal definitions.
        """
        body = self._get("/intents")
        return body.get("data", body) if isinstance(body, dict) else body

    # ------------------------------------------------------------------
    # Derived / analytical methods
    # ------------------------------------------------------------------

    def get_format_summary(self, start: str, end: str) -> dict:
        """
        Aggregate ad set metrics by detected format.

        Returns:
          {
            "formats": {
              "TLA": {
                "campaigns": int,
                "impressions": int,
                "clicks": int,
                "engagements": int,
                "costInUsd": float,
                "cpc": float,
                "engagement_rate": float,   # engagements/impressions
                "metric_label": "Engagement Rate",
                "metric_value": float,
                "tla_disclaimer": str,
              },
              "Image": { ... "metric_label": "Link CTR", "metric_value": float },
              ...
            },
            "ad_sets": [...]   # raw list with 'format' injected
          }

        IMPORTANT — TLA disclaimer:
          TLA 'clicks' count ALL engagement types (likes, shares, comments,
          link clicks). A TLA CTR of 8-11% is NOT comparable to Image/Video
          link CTR. For TLA, report 'Engagement Rate' (engagements/impressions).
          True landing-page CTR for TLA is unavailable at campaign level from
          the ZenABM API (no ad-level endpoint exists).
        """
        ad_sets = self.get_ad_sets(start, end)

        # Accumulate totals per format
        totals: dict[str, dict] = {}
        for item in ad_sets:
            fmt = item.get("format", "Other")
            if fmt not in totals:
                totals[fmt] = {
                    "campaigns": 0,
                    "impressions": 0,
                    "clicks": 0,
                    "engagements": 0,
                    "costInUsd": 0.0,
                }
            t = totals[fmt]
            t["campaigns"] += 1
            t["impressions"] += item.get("impressions", 0) or 0
            t["clicks"] += item.get("clicks", 0) or 0
            t["engagements"] += item.get("engagements", 0) or 0
            t["costInUsd"] += item.get("costInUsd", 0) or 0

        # Compute derived metrics
        for fmt, t in totals.items():
            impr = t["impressions"]
            clicks = t["clicks"]
            engagements = t["engagements"]
            spend = t["costInUsd"]

            t["cpc"] = round(spend / clicks, 2) if clicks else 0
            t["cpm"] = round(spend / impr * 1000, 2) if impr else 0
            t["engagement_rate"] = round(engagements / impr * 100, 3) if impr else 0
            t["link_ctr"] = round(clicks / impr * 100, 3) if impr else 0

            if fmt == "TLA":
                t["metric_label"] = "Engagement Rate"
                t["metric_value"] = t["engagement_rate"]
                t["tla_disclaimer"] = (
                    "TLA 'clicks' include all engagement actions (likes, shares, "
                    "comments, link clicks). TLA click CTR is NOT comparable to "
                    "Image/Video link CTR. Use Engagement Rate for TLA. "
                    "True landing-page CTR is unavailable at campaign level from "
                    "the ZenABM API — no ad-level endpoint exists."
                )
            else:
                t["metric_label"] = "Link CTR"
                t["metric_value"] = t["link_ctr"]

        return {"formats": totals, "ad_sets": ad_sets}

    def get_impression_hogs(
        self,
        start: str,
        end: str,
        threshold_multiplier: float = 5.0,
    ) -> list:
        """
        Identify companies whose impression count is significantly above peers.

        A company is flagged if:
          company.impressions > median(all_impressions) * threshold_multiplier

        Returns a list of flagged company dicts, each with an added
        'impression_vs_median' key showing the multiple of the median.

        These accounts are often being heavily served ads but may not be
        converting — worth investigating before further spend.
        """
        companies = self.get_companies(start, end, sort_by="impressions", limit=100)
        if not companies:
            return []

        impression_values = [c.get("impressions", 0) or 0 for c in companies]
        if len(impression_values) < 2:
            return []

        median_val = statistics.median(impression_values)
        threshold = median_val * threshold_multiplier

        hogs = []
        for company in companies:
            impr = company.get("impressions", 0) or 0
            if impr > threshold and median_val > 0:
                company = dict(company)
                company["impression_vs_median"] = round(impr / median_val, 1)
                hogs.append(company)

        return sorted(hogs, key=lambda c: c.get("impressions", 0), reverse=True)
