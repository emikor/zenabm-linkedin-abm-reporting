# LinkedIn ABM Reporter — Claude Code Plugin

A Claude Code plugin that generates comprehensive LinkedIn ABM performance reports directly from your ZenABM account. Ask Claude for a weekly, monthly, quarterly, or annual report and it will pull live data, surface insights, flag issues, and optionally export a styled PDF — all without leaving your terminal.

---

## What This Plugin Reports On

### Headline Performance (with period-over-period comparison)
- Total spend, impressions, clicks, engagements
- Blended CTR, CPC, CPM, engagement rate
- % change vs the prior equivalent period with trend indicators

### Pipeline ROI & Deal Attribution
- All deals opened in the period with ABM/LinkedIn influence flags
- Pre-deal LinkedIn exposure (impressions, clicks, engagements before deal creation)
- Which campaigns most commonly appear before deals close
- Deals with zero ABM exposure (potential targeting gaps)

### Campaign Group Performance
- Impressions, clicks, engagements, spend, CPC, conversions per group
- Week-over-week trend within the period

### Ad Format Breakdown (with TLA handling)
- Separate metrics per format: TLA, Image, Video, Carousel, Text
- TLA uses Engagement Rate (engagements/impressions) — NOT click CTR
- Image/Video/Carousel use Link CTR (clicks/impressions)
- These are never mixed or compared directly (see API Limitations below)

### Top Engaged Accounts
- Top 15 companies sorted by clicks
- ABM stage, intent signals, spend, CTR per account
- Impression hog flagging: companies receiving >5x median impressions

### ABM Stage Moves
- Companies newly entering "Interested" or "Considering" stage during the period
- Direct link to ZenABM for follow-up

### Red Flags (auto-detected)
- Efficiency drops: spend up, engagement down
- Impression hogs with no pipeline or stage progression
- Deals that closed with zero LinkedIn exposure
- Campaign groups with declining week-over-week performance
- Format underperformance vs peers

### Green Flags
- Top-performing campaign groups and formats
- Best efficiency accounts (high clicks, low CPC)
- ABM-influenced deals closed

### Quarterly/Annual Additions
- Top 10 companies by total clicks
- Top 5 campaign groups by pipeline-influenced deals
- Month-over-month spend and engagement trend table
- Overall ROI summary (pipeline/spend ratio, cost per deal)

---

## Installation

In Claude Code, run this one command:

```
/plugin marketplace add emikor/zenabm-linkedin-abm-reporting
```

Claude Code will fetch the marketplace and prompt you to install `linkedin-abm-reporter` — confirm and you're done.

<details>
<summary>Manual / explicit install (two commands)</summary>

```
/plugin marketplace add emikor/zenabm-linkedin-abm-reporting
/plugin install linkedin-abm-reporter@zenabm-linkedin-abm-reporting
```

Or from the shell:

```bash
claude plugin marketplace add emikor/zenabm-linkedin-abm-reporting
claude plugin install linkedin-abm-reporter@zenabm-linkedin-abm-reporting
```
</details>

---

## Setup (First Time)

Run the setup wizard to configure your ZenABM API token:

```bash
bash ~/linkedin-abm-reporter/scripts/setup.sh
```

The wizard will:
1. Prompt for your ZenABM API token (find it in ZenABM → Settings → API)
2. Test the token against the live API
3. Write a `.env` file to the plugin root
4. Print next steps

Then install Python dependencies:

```bash
pip install -r ~/linkedin-abm-reporter/requirements.txt
```

---

## Usage

Once installed, simply ask Claude:

### Weekly report
> "Give me last week's LinkedIn ABM report"
> "ABM weekly report"
> `/abm-report`

### Monthly report
> "Generate an ABM report for last month"
> "What does our LinkedIn performance look like for March?"

### Quarterly report
> "ABM Q1 report"
> "Give me a quarterly LinkedIn ABM summary"

### Annual report
> "Full year LinkedIn ABM report"
> "Annual ABM wrap"

### Specific date range
> "LinkedIn ABM report from April 1 to April 14"

Claude will fetch all the data, compute comparisons, and generate a structured markdown report in the conversation. You can then export it as a PDF.

---

## PDF Export

After Claude generates the report, it will ask:

> "Would you like to export this as a PDF?"

Say yes and it will run:
```bash
python ~/linkedin-abm-reporter/scripts/export_pdf.py /tmp/abm-report-YYYY-MM-DD-YYYY-MM-DD.md
```

The PDF will be saved to the same directory as the markdown temp file. The design features:
- Clean A4 layout with page numbers
- Dark blue headings with coloured table headers
- Zebra-striped tables
- Emoji-friendly font stack
- Proper handling of long tables across pages

You can also run it manually on any markdown file:
```bash
python ~/linkedin-abm-reporter/scripts/export_pdf.py /path/to/report.md
```

---

## CLI Usage (Advanced)

You can call the ZenABM API directly from the command line for custom queries:

```bash
# Quick overview
python ~/linkedin-abm-reporter/scripts/query_zenabm.py get_overview \
  '{"start":"2024-04-07","end":"2024-04-13"}'

# Period comparison
python ~/linkedin-abm-reporter/scripts/query_zenabm.py get_wow_metrics \
  '{"current_start":"2024-04-07","current_end":"2024-04-13","prev_start":"2024-03-31","prev_end":"2024-04-06"}'

# Top companies by spend
python ~/linkedin-abm-reporter/scripts/query_zenabm.py get_companies \
  '{"start":"2024-04-01","end":"2024-04-30","sort_by":"costInUsd","limit":20}'

# Format breakdown
python ~/linkedin-abm-reporter/scripts/query_zenabm.py get_format_summary \
  '{"start":"2024-04-01","end":"2024-04-30"}'

# Impression hogs
python ~/linux-abm-reporter/scripts/query_zenabm.py get_impression_hogs \
  '{"start":"2024-04-01","end":"2024-04-30","threshold_multiplier":5}'

# All deals
python ~/linkedin-abm-reporter/scripts/query_zenabm.py get_deals \
  '{"start":"2024-01-01","end":"2024-03-31"}'
```

All output is plain JSON — pipe it to `jq` for filtering.

### Available functions

| Function | Description |
|----------|-------------|
| `get_overview` | Headline metrics for a date range |
| `get_wow_metrics` | Two-period comparison with % changes |
| `get_campaign_groups` | All LinkedIn Campaign Groups |
| `get_campaign_group_weekly` | Weekly breakdown for one group |
| `get_ad_sets` | All ad sets with format detection |
| `get_ad_set_weekly` | Weekly breakdown for one ad set |
| `get_format_summary` | Aggregated metrics per format |
| `get_companies` | Top companies by any metric |
| `get_impression_hogs` | Companies over-indexed on impressions |
| `get_deals` | Deals with attribution data |
| `get_abm_stages` | All ABM stage definitions |
| `get_companies_entering_stage` | Companies new to a given stage |
| `get_stage_history` | Stage transition log |
| `get_ad_spend` | Monthly spend breakdown |
| `get_job_titles` | Persona engagement data |
| `get_abm_campaigns` | ABM campaign list |
| `get_intents` | Intent signal definitions |
| `detect_format` | Detect format from a campaign name string |

---

## Data Sources & API Limitations

### ZenABM API
- Base URL: `https://app.zenabm.com/api/v1`
- Auth: Bearer token (configured via setup.sh)
- All data is scoped to your ZenABM account and the LinkedIn accounts connected to it

### TLA Format — Critical Limitation

**TLA (Thought Leadership Ads)** report their metrics differently from all other LinkedIn ad formats:

| | TLA | Image / Video / Carousel |
|--|-----|--------------------------|
| API "clicks" | All engagement actions (likes, shares, comments, link clicks combined) | Link clicks only |
| Typical CTR | 8–11% | 0.4–2% |
| What it means | Content engagement, not website traffic | True landing-page traffic |

The plugin enforces a strict rule: **TLA CTR is never compared to Image/Video CTR**. The report always shows Engagement Rate (engagements/impressions) for TLA and Link CTR (clicks/impressions) for other formats.

Additionally, **true landing-page CTR for TLA is not available at campaign level** from the ZenABM API. There is no ad-level endpoint that would allow computing click-through on just the "visit website" action for TLA ads.

### No Ad-Level Creative Data
The ZenABM API operates at campaign (ad set) level. It is not possible to see which individual ad variant (specific image, headline, or body copy) performed best within a campaign.

### Pagination
All list endpoints are paginated. The API client transparently fetches all pages, so you always get the full dataset.

### Date Ranges
ZenABM uses inclusive date ranges. The range `2024-04-07_2024-04-13` includes data from both April 7 and April 13.

---

## Troubleshooting

### "ZENABM_API_TOKEN is not set"
Run the setup wizard: `bash ~/linkedin-abm-reporter/scripts/setup.sh`

### "HTTP 401 / 403" errors
Your token may be expired or incorrect. Re-run `setup.sh` to enter a new token.

### "module not found" errors
Install dependencies: `pip install -r ~/linkedin-abm-reporter/requirements.txt`

### PDF export fails
WeasyPrint requires system libraries on some platforms:
- **macOS**: `brew install pango`
- **Ubuntu/Debian**: `apt-get install libpango-1.0-0 libpangoft2-1.0-0`

### Empty data / all zeros
Check that the date range you specified actually contains data in your ZenABM account. LinkedIn data may have a 24–48 hour reporting delay.

### Impression hog threshold
If you have a large enterprise account where >5x median is too sensitive, adjust the multiplier:
```bash
python query_zenabm.py get_impression_hogs '{"start":"...","end":"...","threshold_multiplier":10}'
```
