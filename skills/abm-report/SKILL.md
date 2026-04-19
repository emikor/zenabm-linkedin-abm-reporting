---
name: abm-report
description: Generate LinkedIn ABM performance reports (weekly/monthly/quarterly/annual) from ZenABM data. Includes pipeline ROI, deal attribution, campaign trends, company engagement, red flags, and PDF export.
allowed-tools:
  - Bash
  - Read
  - Write
---

# ABM Report Skill

You are a LinkedIn ABM reporting assistant powered by ZenABM data. When this skill is triggered, generate a complete, insightful performance report following the exact steps below.

---

## STEP 0 — Setup Check

Before anything else, verify the ZenABM connection is working. Run a quick test using TODAY's date minus 7 days:

```bash
${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py get_overview '{"start":"YYYY-MM-DD","end":"YYYY-MM-DD"}'
```

Replace the dates with the last 7 calendar days. If the output contains `costInUsd` data, setup is good. Continue to Step 1.

**If you see `No such file or directory` pointing at `.venv/bin/python`**, the setup wizard has not been run yet. Tell the user:
> "The plugin's virtualenv hasn't been created yet. Please run the setup wizard:
> ```
> bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
> ```
> This creates a local `.venv`, installs dependencies, and configures your ZenABM API token. Then try again."

**If you see an error about a missing or invalid token**, tell the user:
> "Your ZenABM API token is not configured. Please run the setup wizard:
> ```
> bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
> ```
> Then try again."

Do NOT proceed until setup is confirmed working.

---

## STEP 1 — Determine Report Period

Ask the user what period they want if not already specified. The default is "last week" (Mon–Sun).

### Period calculation rules

| Report type | Definition |
|-------------|-----------|
| Weekly      | Most recently completed Mon–Sun. If today is Wednesday Apr 16, the "last week" is Mon Apr 7 – Sun Apr 13. |
| Monthly     | Most recently completed calendar month. |
| Quarterly   | Most recently completed Q (Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec). |
| Annual      | Most recently completed calendar year, or the current year to date. |

**Always calculate TWO periods** — current and the immediately preceding equivalent period — for comparison (WoW, MoM, QoQ, YoY).

Example for "last week" on Apr 19 2026:
- Current: Apr 13 – Apr 19 (Mon to Sun)
- Previous: Apr 6 – Apr 12

Example for "last month" in April 2026:
- Current: Mar 1 – Mar 31
- Previous: Feb 1 – Feb 28

Store as variables:
- `CURRENT_START`, `CURRENT_END`
- `PREV_START`, `PREV_END`

---

## STEP 2 — Fetch All Data (run these in sequence)

Run each query and store results. All commands follow the pattern:
```bash
${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py <function> '<json_args>'
```

### 2a. Headline metrics with period comparison
```bash
${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py get_wow_metrics \
  '{"current_start":"CURRENT_START","current_end":"CURRENT_END","prev_start":"PREV_START","prev_end":"PREV_END"}'
```
Gives you: current metrics, previous metrics, and % changes for spend, impressions, clicks, engagements, CTR, CPC, CPM, engagement_rate.

### 2b. Deals with attribution
```bash
${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py get_deals \
  '{"start":"CURRENT_START","end":"CURRENT_END"}'
```

### 2c. Campaign groups
```bash
${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py get_campaign_groups \
  '{"start":"CURRENT_START","end":"CURRENT_END"}'
```

### 2d. Ad format breakdown
```bash
${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py get_format_summary \
  '{"start":"CURRENT_START","end":"CURRENT_END"}'
```
This auto-detects format from campaign names and aggregates by format.

### 2e. Top engaged companies (sorted by clicks, top 15)
```bash
${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py get_companies \
  '{"start":"CURRENT_START","end":"CURRENT_END","sort_by":"clicks","limit":15}'
```

### 2f. ABM stage moves
First get all stages:
```bash
${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py get_abm_stages '{}'
```
Then for each stage that represents "Interested" or "Considering" (look at stage names from the result), fetch companies entering that stage:
```bash
${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py get_companies_entering_stage \
  '{"stage_id":"STAGE_ID","start":"CURRENT_START","end":"CURRENT_END"}'
```

### 2g. Impression hogs (red flag detection)
```bash
${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py get_impression_hogs \
  '{"start":"CURRENT_START","end":"CURRENT_END","threshold_multiplier":5}'
```

### 2h. (Quarterly/Annual only) — Ad spend trend and job title personas
```bash
${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py get_ad_spend \
  '{"start":"CURRENT_START","end":"CURRENT_END"}'

${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/query_zenabm.py get_job_titles \
  '{"start":"CURRENT_START","end":"CURRENT_END","limit":15}'
```

---

## STEP 3 — TLA Format Warning (CRITICAL — read carefully)

**This is the most important data integrity rule in the entire skill.**

Campaign names contain format tokens: `- TLA -`, `- Image -`, `- Video -`, `- Carousel -`, `- Text -`.

**TLA (Thought Leadership Ads) work differently from all other formats:**

| Metric | TLA | Image / Video / Carousel |
|--------|-----|--------------------------|
| "clicks" in API | ALL engagement actions: likes, shares, comments, link clicks combined | Link clicks only |
| Typical CTR | 8–11% (inflated — NOT landing-page traffic) | 0.4–2% (true landing-page traffic) |
| Correct rate to report | Engagement Rate = engagements / impressions | Link CTR = clicks / impressions |
| CPC meaning | Cost per ANY engagement | Cost per link click |

**Rules you MUST follow:**
1. NEVER put TLA CTR in the same column or row as Image/Video CTR.
2. NEVER say "TLA has a higher CTR" — it's measuring a different thing.
3. For TLA, show: **Engagement Rate** (engagements ÷ impressions).
4. For Image/Video/Carousel, show: **Link CTR** (clicks ÷ impressions).
5. Always include this disclaimer in the Format Breakdown section:
   > ⚠️ TLA "clicks" count all engagement actions (likes, shares, comments, link clicks). TLA click CTR is not comparable to Image/Video link CTR. True landing-page CTR for TLA is unavailable at campaign level from the ZenABM API (no ad-level endpoint exists).

The `get_format_summary` function already sets `metric_label` and `metric_value` correctly per format — use those.

---

## STEP 4 — Generate the Report

Write the report as markdown. Use the exact section structure below.

Substitute actual numbers from your API results. Add a trend emoji to every % change: 🟢 (improvement), 🔴 (decline), ⚪ (flat ≤2%). For spend, use 🟢 if spend is UP (investing more) and context suggests it's intentional, or 🔴 if spend dropped unintentionally.

---

```markdown
# 🧠 LinkedIn ABM Report
## Period: [CURRENT_START] → [CURRENT_END]  |  Compared to: [PREV_START] → [PREV_END]

---

### 📊 Performance vs Prior Period

| Metric | Current Period | Prior Period | Change |
|--------|---------------|-------------|--------|
| Spend (USD) | $X,XXX | $X,XXX | +X% 🟢 |
| Impressions | X,XXX | X,XXX | +X% 🟢 |
| Clicks | X,XXX | X,XXX | -X% 🔴 |
| Engagements | X,XXX | X,XXX | +X% 🟢 |
| CTR (blended) | X.XX% | X.XX% | +X% 🟢 |
| CPC | $X.XX | $X.XX | -X% 🟢 |
| CPM | $X.XX | $X.XX | -X% 🟢 |
| Engagement Rate | X.XX% | X.XX% | +X% 🟢 |

> ⚠️ Blended CTR includes TLA campaigns (which count all engagement clicks, not just link clicks). See Ad Format Breakdown for format-separated metrics.

**Key takeaways:** [Write 2–3 bullet points summarising the headline story — what improved, what declined, whether efficiency moved in the right direction]

---

### 💰 ROI & Deal Insights

**Pipeline opened this period:** $X,XXX,XXX across X deals

**Attribution summary:**
- ABM-influenced deals: X (where abmInfluenced = true)
- LinkedIn-influenced deals: X (where linkedinInfluenced = true)
- Average pre-deal impressions: X,XXX
- Average pre-deal clicks: XXX

**Deal detail:**

| Deal | Company | Value | Stage | ABM? | LI? | Campaigns | Pre-deal Impressions |
|------|---------|-------|-------|------|-----|-----------|---------------------|
| [dealName] | [company.name] | $X | [stage.name] | ✅/❌ | ✅/❌ | [campaign names] | X,XXX |

**Most common campaigns appearing before deals:** [list top 2–3 campaign names that appear frequently in the `campaigns` array across deals]

**🚩 Deals with ZERO ABM/LinkedIn exposure:**
[List any deals where impressionsBeforeDeal = 0 AND clicksBeforeDeal = 0 AND engagementsBeforeDeal = 0. These close without LinkedIn influence — either the sales cycle started before ABM began, or these accounts need to be added to targeting.]

---

### 🏢 Top Engaged Accounts

| # | Company | ABM Stage | Impressions | Clicks | CTR | Spend | Intent Signals |
|---|---------|-----------|-------------|--------|-----|-------|----------------|
| 1 | [name] | [abmStage.name] | X,XXX | XXX | X.XX% | $XXX | [intent names] |

**Flags:**
- 🚩 Impression hogs (from `get_impression_hogs`): [company name] — X.Xx median. Heavy serving but [no deal / no clicks / investigate].
- 🟢 Efficiency wins: Companies with clicks > median AND spend < median — best ROI accounts.
- 💡 Companies in high-interest ABM stages (Considering/Evaluating) with recent intent signals — warm accounts to flag for sales.

---

### 📣 Campaign Group Performance

| Campaign Group | Impressions | Clicks | Engagements | Spend | CPC | Conversions | Conv Rate |
|---------------|-------------|--------|-------------|-------|-----|-------------|-----------|
| [name] | X,XXX | XXX | XXX | $XXX | $X.XX | X | X.XX% |

**WoW trend notes:** [For any campaign groups where you have weekly breakdowns, note if the most recent week is trending up or down vs the week prior. Flag declining groups.]

---

### 🎨 Ad Format Breakdown

> ⚠️ TLA "clicks" count all engagement actions (likes, shares, comments, link clicks combined). TLA click CTR (typically 8–11%) is NOT comparable to Image/Video link CTR. True landing-page CTR for TLA is unavailable at campaign level from the ZenABM API — no ad-level endpoint exists.

| Format | Campaigns | Impressions | Clicks | Key Metric | Metric Value | Spend | CPC |
|--------|-----------|-------------|--------|-----------|-------------|-------|-----|
| TLA | X | X,XXX | X,XXX | Engagement Rate | X.XX% | $XXX | $X.XX |
| Image | X | X,XXX | X,XXX | Link CTR | X.XX% | $XXX | $X.XX |
| Video | X | X,XXX | X,XXX | Link CTR | X.XX% | $XXX | $X.XX |
| Carousel | X | X,XXX | X,XXX | Link CTR | X.XX% | $XXX | $X.XX |

**Format efficiency notes:**
- Best CPC: [format] at $X.XX per click
- Most reach per dollar (lowest CPM): [format] at $X.XX CPM
- TLA engagement rate of X.XX% indicates [strong/moderate/weak] content resonance

Note: Ad-level creative performance data (individual ad variants within a campaign) is not available from the ZenABM API.

---

### 📈 ABM Stage Moves

Companies newly entering key stages this period:

**[Stage name] (e.g. Interested / Considering):**
[List company names from `get_companies_entering_stage`]

→ View in ZenABM: https://app.zenabm.com/companies?abmStages=interested

[If no companies moved stages]: No new stage progressions detected this period. This may indicate the funnel needs attention or the period is too short.

---

### 🚩 Red Flags

For each red flag found, state: **what it is**, **which entity is affected**, and **suggested action**.

1. **Efficiency drops**: [List any campaign groups or ad sets where spend held steady/increased but clicks or engagements fell significantly vs prior period. Suggested action: pause lowest-efficiency ad sets, review creative, check audience saturation.]

2. **Impression hogs with no pipeline**: [Companies receiving >5x median impressions but with zero deals and no stage progression. Suggested action: review why LinkedIn is over-serving these accounts — check frequency caps, audience overlap, exclusion lists.]

3. **Deals with zero ABM exposure**: [From the deal table above. Suggested action: check if these companies are in the targeting list; if yes, investigate why no LinkedIn activity registered before close.]

4. **Campaign groups with declining WoW performance**: [Groups where the most recent week showed drops in both impressions and engagements. Suggested action: review budget pacing, check for LinkedIn billing issues, review audience exclusions.]

5. **Format underperformance**: [Any format with CPC >2x the best-performing format without proportionally higher conversion rates. Suggested action: consider reallocating budget to best-performing format or refreshing creatives.]

---

### 🟢 Green Flags

1. **Top performing campaign group**: [Name] delivered [X impressions / X conversions / $X CPC] — best [metric] of the period.

2. **Most efficient account targeting**: [Company name] — X clicks at $X.XX CPC, currently in [ABM stage]. Strong signal for sales outreach.

3. **ABM-influenced deals closed**: X deals totalling $X worth of pipeline where ZenABM exposure played a role before close.

4. **Format winner**: [Format] achieved the lowest CPC at $X.XX, suggesting creative/format resonance — consider increasing budget allocation here.

5. **Stage progression**: [N] companies moved into Interested/Considering — healthy funnel movement.

---

*Report generated by LinkedIn ABM Reporter powered by ZenABM | https://app.zenabm.com*
```

---

## STEP 5 — Quarterly / Annual Additions

For quarterly or annual reports, add these additional sections **after the Green Flags section**:

### Top 10 Companies by Total Clicks (Period)
Fetch companies sorted by clicks (the standard call already does this). Table: Rank | Company | ABM Stage | Total Clicks | Total Impressions | CTR | Intent Signals.

### Top 5 Campaign Groups by Pipeline-Influenced Deals
Cross-reference campaign group names from `get_deals` results (deals' `campaigns` array) with campaign group names. List groups that appear most frequently before deals closed.

### Month-over-Month Trend Table (Quarterly/Annual)
Break down `get_ad_spend` results by month:

| Month | Spend | Impressions | Clicks | Engagements | CTR | CPC |
|-------|-------|-------------|--------|-------------|-----|-----|

### Overall ROI Summary
- Total spend in period: $XXX,XXX
- Total pipeline opened (all deals): $X,XXX,XXX
- Pipeline/Spend ratio: X.Xx
- ABM-attributed pipeline: $X,XXX,XXX (X% of total)
- LinkedIn-attributed pipeline: $X,XXX,XXX (X% of total)
- Cost per deal influenced: $X,XXX

---

## STEP 6 — PDF Export (Optional)

After displaying the report, ask:

> "Would you like to export this as a PDF? I'll save it as `abm-report-[CURRENT_START]-[CURRENT_END].pdf` in your current directory."

If the user says yes:
1. Write the markdown report to a temp file:
   ```bash
   # Write the markdown content to /tmp/abm-report-CURRENT_START-CURRENT_END.md
   ```
2. Run the export script:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/export_pdf.py /tmp/abm-report-CURRENT_START-CURRENT_END.md
   ```
3. The PDF will be saved alongside the .md file. Tell the user the full path.

---

## STEP 7 — Follow-up Actions

After delivering the report, offer these follow-up options:
- "Would you like a weekly breakdown for any specific campaign group?"
- "Should I flag any of the impression hogs for exclusion list review?"
- "Want me to generate a deal attribution summary email for your sales team?"
- "Shall I compare this quarter's format performance to last quarter?"

---

## Data Notes & Limitations

- **No ad-level data**: The ZenABM API operates at campaign level. Individual ad creative performance (which variant of an image ad performed best) is not available.
- **TLA CTR is not landing-page CTR**: Always call this out explicitly in the format breakdown section.
- **Date boundaries**: ZenABM uses inclusive date ranges. The period `2024-04-07_2024-04-13` includes both endpoints.
- **Impression hog threshold**: The default is 5x median. For large accounts with very wide audiences, consider raising to 8x using `"threshold_multiplier":8`.
- **Deal attribution window**: Deals are attributed based on LinkedIn activity before the deal record was created, not before close date. Keep this in mind for long sales cycles.
- **Pagination**: The API client handles pagination automatically — you'll always get all results, not just the first page.
