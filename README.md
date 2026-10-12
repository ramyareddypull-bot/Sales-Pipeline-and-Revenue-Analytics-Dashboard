# Sales Pipeline & Revenue Analytics Dashboard

A read-only Streamlit dashboard for a CSV snapshot of Salesforce-style opportunities. Four tabs cover executive results, pipeline and forecast quality, sales-team performance, and opportunity detail/trends. No Salesforce API, database, AI service or credentials are required.

## Launch locally

Prerequisites: [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.12 (uv can manage the pinned interpreter).

From the project directory:

```sh
uv sync --locked
uv run --extra ai python -m streamlit run app.py --server.port 8503
```

Open http://127.0.0.1:8503. Port 8503 keeps this dashboard separate from other local Streamlit apps. Run the command in a terminal while using the dashboard.

Initial setup used:

```sh
uv init --bare sales-pipeline-dashboard
cd sales-pipeline-dashboard
uv python pin 3.12
uv add streamlit pandas numpy plotly
uv add --dev pytest
uv sync
```

All dependency management and Python execution use uv. `pyproject.toml`, `uv.lock` and `.python-version` define the reproducible environment.

## Source data

The bundled `sales_pipeline_demo_650.csv` is copied from the supplied file in Downloads. It contains 650 opportunity records and is loaded automatically when no upload is selected. No records or KPI values are generated. Upload a UTF-8 CSV (up to 20 MB) with the same 22-column schema to replace it. Clearing the upload restores the default. The active filename and loaded/matching record counts are displayed.

Required columns:

```text
opportunity_id, account_id, account_name, opportunity_name, owner,
sales_team, region, industry, segment, product, lead_source,
opportunity_type, created_date, close_date, stage, probability_pct,
amount_usd, forecast_category, stage_entered_date, last_activity_date,
next_step, loss_reason
```

IDs remain strings, including leading zeros. Surrounding whitespace is removed. Dates are parsed and normalized to UTC calendar days; date-only Salesforce exports are recommended. Amounts support numeric values and `$50,000` formatting. Probability is a numeric 0–100 value; it is never inferred from the stage or clamped into range.

### Data quality and calculation coverage

The quality panel reports total, accepted and rejected records, duplicate IDs, missing source fields, and row-level issues (CSV record numbers include the header). Blank categories become `Unknown`; blank next steps become `Not provided`.

Missing IDs, duplicate IDs, invalid/negative amounts, invalid stages, invalid created/close dates or a close date before creation exclude the entire record. **All occurrences of duplicate IDs are rejected** because the source provides no supported version-selection rule. Reconcile duplicates upstream and upload again. Noncritical invalid fields do not remove otherwise usable revenue:

- Invalid/missing probabilities remain null. Unweighted metrics remain available, but the complete weighted pipeline displays N/A if any selected open deal is missing its probability. The affected category/group weighted total is also N/A.
- Missing or inconsistent activity/stage dates remain null and are excluded only from the corresponding aging/risk checks. Activity or stage dates before creation, or after a closed deal's close date, are flagged.
- Unknown forecast classifications are labeled Unknown and shown explicitly, never mapped to Commit or Best Case.
- Overdue open deals remain valid records.
- Negative aging from a future date relative to the analysis date is unavailable, never silently changed to zero. Open deals with incomplete risk timestamps are counted and labeled.

The analysis date defaults to the current America/Los_Angeles date and can be changed for reproducible risk testing. This changes age calculations only; it **does not reconstruct a prior opportunity snapshot** or change opportunity stages. Records created after that date are flagged and excluded from age buckets, while retaining their current snapshot amounts.

## Metrics and interpretation

All metrics are calculated in `utils/metrics.py` from the same filtered dataframe.

- Open pipeline: amounts in Prospecting, Qualification, Discovery, Proposal and Negotiation.
- Closed Won Opportunity Value: amounts for Closed Won. This is not recognized accounting revenue or ARR.
- Closed Lost Value: amounts for Closed Lost.
- Weighted pipeline: open amount × probability / 100, excluding closed opportunities.
- Win rate: unique won IDs / unique won-plus-lost IDs. Open deals are excluded. No closed deals means N/A.
- Average won deal size and average/median won sales cycle use Closed Won opportunities only.
- Sales cycle is actual close minus creation. Open opportunity age is analysis date minus creation.
- Pipeline coverage is unavailable unless you explicitly supply a positive revenue target in the planning controls. Match the target's period and scope to the current filters; it is never invented.
- Commit and Best Case values follow their exact source categories. They overlap with other pipeline/risk measures and must not be added to total pipeline.
- At-risk open opportunities meet at least one condition: expected close before analysis date, inactivity >14 days, or current-stage age >30 days. Values/counts are taken from the union, without double counting.
- Missing dates do not imply a safe deal. Incomplete risk coverage is stated explicitly.

Owner/team rankings group by both owner and sales team. Regional, industry, segment, lead-source and opportunity-type groupings reuse the same metric definitions. No marketing ROI or CAC is inferred without costs. Tables and charts show all values computed from source records; no fixed KPI constants drive the UI.

## Filters and navigation

The sidebar filters all five tabs, including the AI context, by **Close Date Range**, sales owner/team, region, stage, industry, segment, product, forecast category, lead source and opportunity type. Close date is expected for open opportunities and actual for closed opportunities. Empty multiselects mean All. Selected dimensions combine with AND, and choices within a dimension combine with OR. Categories match case-insensitively without altering the source records.

Date presets are All Dates (the default), Last 30 Days, Last 90 Days, This Quarter, Last Quarter, This Year and Custom Range. Presets use the visible analysis date. Last 30/90 Days include that date; This Quarter and This Year include the full calendar period, including future expected closes. All Dates includes every source close date. Custom ranges can extend beyond the source dates and intentionally produce an empty cohort.

Category choices cascade in sidebar order: region → team → owner → industry → segment → product → opportunity type → stage → forecast category → lead source. Upstream selections take precedence; invalid downstream selections are cleared with a visible notice. This prevents contradictory retained choices. When the date range itself is empty, category choices remain available for easy recovery. Active restrictions are shown above the tabs with individual Clear actions.

**Reset All Filters** restores All Dates, clears every category, chart drill-down and search, and resets the detail selection. New datasets reset this same data-dependent state. Switching tabs preserves it. Display preferences and an explicitly entered planning target are not dataset filters.

1. **Executive Overview:** pipeline, Closed Won value, weighted pipeline, win rate, deal size, cycle and overdue cards; ordered stages; monthly Closed Won value; switchable revenue distribution.
2. **Pipeline & Forecast:** current stage count/amount/weighted funnel, forecast categories, sortable risk table, and aging bands. The funnel is explicitly a current snapshot, not a historical conversion funnel. Open records labeled Closed, Omitted or Unknown remain in forecast reconciliation rather than silently disappearing.
3. **Sales Team Performance:** owner/team leaderboard with highlighted leaders, switchable rep measure, regional comparison, industry/segment/type views, and lead-source chart/table.
4. **Deal Deep-Dive & Revenue Trends:** searchable/sortable records, downloadable filtered CSV, daily/weekly/monthly/quarterly trends, won sales-cycle distribution and group summaries, loss reasons, and a read-only opportunity detail panel.

Deep-dive search matches opportunity ID/name, account and owner without regard to case, and filters the opportunity table, details and its download only. Sort controls support amount, close date, probability, stage age and inactivity; table headers remain sortable. All charts use the sidebar-filtered cohort. The header's Export Dashboard Data downloads the global cohort; table and drill-down exports download their corresponding subsets plus calculated fields. Spreadsheet-dangerous text is prefixed with an apostrophe to prevent uploaded content executing as a formula when exported.

### Phase 2 interactions and presentation

KPI cards use compact currency values with exact values beneath, tooltips and relevant opportunity counts. The overview shows a horizontal open-stage chart with amount/count/weighted selection, revenue distribution, switchable revenue trends, and rules-based insights calculated from current records. Rep rankings and their leaderboard use the same selected measure, with Top 5, Top 10 and All controls. Region comparisons have an independent metric selector; the global segment filter applies to them. Team win-rate and overlapping risk-category charts supplement the existing views.

Every supported drill-down uses an adjacent native selection control under **Explore … opportunities**. Available dimensions include open stage, region, sales owner/team, industry, lead source and risk category; distribution and segment/type views also support details. Selecting a category opens **Selected Opportunities** and its CSV export. Clear selection reverses it. Drill-downs remain local to their detail table and never alter global KPI totals. Owner/team pairs preserve team assignments. This keyboard-friendly fallback intentionally uses no custom JavaScript or bar-click dependency. Plotly tooltips, zoom and range sliders remain interactive; zoom affects only its chart.

Complete-month Closed Won comparisons appear only when the two months before the analysis month are entirely within the selected close-date range, both contain recorded wins and the prior value is positive. The comparison has its own labeled current-month value and baseline; it is not a delta on the full-cohort KPI. The CSV cannot prove export completeness, and no historical pipeline comparisons are inferred.

Native bordered cards and Streamlit chart theming support light/dark mode (choose it from Streamlit Settings). Backgrounds are transparent and conditional highlights use low-opacity fills with textual status/risk labels. **Compact layout** under Display & revenue planning stacks chart sections and reduces KPI columns for narrow screens. No generated CSS class selectors or custom JavaScript are used. Browser-specific visual appearance still benefits from review in your chosen theme/window size.

Trends use actual close dates for closed values/counts and creation dates for created-opportunity measures. The global Close Date Range still determines the cohort in both cases. Weekly periods start Monday. Period labels mark bucket starts and can precede the selected start date; only matching records contribute. Unobserved periods are not filled with invented activity. Snapshot data cannot establish historical pipeline balances, stage transitions, conversion rates between stages, or forecast accuracy.

## Architecture

```text
app.py                         Setup, upload, quality panel, shared cohort, tabs
utils/data_loader.py           Bounded CSV loading and cached preprocessing
utils/data_cleaning.py         Schema validation and derived fields
utils/metrics.py               Reusable financial/group/time calculations
utils/filters.py               Consistent global close-date/dimension filtering
utils/risk_analysis.py         Risk union and open opportunity age buckets
components/sidebar.py          Session filter state and optional target control
components/overview.py         Executive tab
components/pipeline_forecast.py Pipeline and risk tab
components/sales_performance.py Rep/team and market performance tab
components/deal_deep_dive.py    Record exploration, trends, cycles and losses
components/common.py           Consistent cards, formatting, tables and charts
components/dashboard_header.py Dataset, cohort/date strip and global export
components/drilldown.py        Shared native category-to-opportunity exploration
components/opportunity_table.py Search, sort, conditional formatting and details
components/trend_chart.py      Shared metric/frequency controls and range slider
utils/dashboard_metrics.py     Observed-period comparisons and descriptive insights
tests/                         Financial, cleaning, risk, filter and UI tests
```

CSV preprocessing uses `st.cache_data` with a ten-minute TTL and a random per-session key so uploads cannot share cache results across sessions. Cache keys include content and analysis date. A new file invalidates dataset-dependent widget state. Uploads remain in memory, not saved to disk. Public deployment/authentication is outside this local MVP.

The optional Revenue Analyst is available in the fifth **AI Revenue Analyst** tab, implemented by `components/ai_revenue_analyst.py`, `utils/revenue_context.py` and `utils/revenue_analyst.py`. It uses the current filtered cohort and sends a Groq request only when you submit a chat message. All four analytics tabs continue working without AI credentials.

## Verification

```sh
uv run pytest -q
```

The actual supplied CSV is checked at fixed analysis date **2026-10-11** against these references:

| Metric | Expected |
| --- | ---: |
| Total opportunities | 650 |
| Open opportunities | 231 |
| Closed Won opportunities | 220 |
| Closed Lost opportunities | 199 |
| Open pipeline | $26,237,000 |
| Weighted open pipeline | $12,023,875 |
| Closed Won opportunity value | $27,683,200 |
| Win rate | approximately 52.51% |

These values appear in tests as source-validation expectations, not application calculations. Tests also cover the $30,000/$14,000 pipeline examples, 80% win-rate case, invalid optional/critical values, duplicates, strict risk boundaries, no double-counting, zero denominators, filter/group reconciliation, trend date choice, CSV export sanitization and Streamlit interactions including new uploads and empty results. Phase 2 tests add calendar boundaries, future-inclusive presets, cascading cleanup, case-insensitive filtering, drill-down/export scope, owner search, overlapping risk counts, comparison eligibility, transparent theme styling, compact layout and full reset. The CSV cleaning, existing financial metric functions and original source dataset are preserved.

## Troubleshooting

- Invalid CSV: review the quality panel; missing required headers prevent loading. Fix errors in your export and re-upload.
- Weighted pipeline N/A: provide valid 0–100 probabilities for all selected open opportunities.
- Empty results: reset filters or expand the Close Date Range. An unfinished two-date selection intentionally displays no cohort.
- Unexpected aging: check the analysis date and source timestamps. Older sample close dates will be overdue as the current date advances.
- Port in use: choose another port, e.g. `uv run --extra ai python -m streamlit run app.py --server.port 8504`.
- Environment issues: run `uv sync --locked` with the pinned Python version.

## Optional AI Revenue Analyst architecture

The fifth tab is **AI Revenue Analyst**. It displays a privacy notice, sample questions, a native chat input and a Clear analyst chat action. Missing credentials or optional dependencies disable only chat, with setup instructions. Filters, dataset or analysis-date changes clear stale chat. Invalid/empty cohorts also clear chat and block requests. No request is sent until a question is submitted.

Install the optional official SDK support:

```sh
uv sync --locked --extra ai
```

Configure `GROQ_API_KEY` and `GROQ_MODEL` in the **server environment** or the project's existing `.env`. Use `.env.example` as a template only if you do not already have a `.env`; do not overwrite an existing file. Choose a supported chat-completion model available in your Groq account. The selected model and credential come from configuration; Python contains model-specific response settings for GPT-OSS. Ordinary `uv sync --locked` keeps the four analytics tabs independent of the AI extra.

### Context and integration contract

`build_revenue_context()` accepts only the current **validated, globally filtered dataframe**, analysis date, close-date range, filter selections and a dataset fingerprint. It reuses the existing calculation functions; all financial numbers, rankings, weighted/open differences and month-over-month changes are computed in Python.

The JSON context includes:

- Complete cohort KPIs, stage totals, forecasts and unique at-risk counts.
- Team and lead-source rankings by win rate with won/lost counts, plus owner/team, industry and region rankings by Closed Won value.
- Risk categories ranked by pipeline exposure, clearly identified as overlapping rule-based categories.
- Up to 24 months of observed Closed Won values; percentage changes only for consecutive, fully selected, completed calendar months with positive baselines.
- Up to 40 opportunity records: explicitly mentioned IDs/names first, then largest at-risk deals and largest opportunities. At most 20 groups per ranking are included, with explicit coverage counts. No unfiltered-record fallback is used.
- Nulls for unavailable values, scope/date metadata and snapshot limitations. Free-text next steps and loss notes are not sent.

Question length is capped at 4,000 characters and the full Python context at 60,000 characters. Before contacting Groq, `utils/revenue_request.py` selects relevant precomputed facts and caps serialized request context at **10,000 UTF-8 bytes**. It retains all cohort KPIs, up to five opportunity details, up to five groups per relevant ranking and six recent monthly observations, reducing details further if needed. Coverage counts and omitted dimensions are explicit. No financial totals are recomputed or silently truncated. Oversized core facts fail with a request to narrow filters. This keeps ordinary requests below common account token limits; unusual inputs or lower provider limits may still require narrower filters. The service cannot answer arbitrary calculations absent from the supplied context and is instructed to say what is unavailable.

The tab uses this server-side flow, catching `ContextError` and `RevenueAnalystError` to show their safe messages:

```python
from utils.revenue_context import build_revenue_context
from utils.revenue_analyst import synchronize_scope, respond

# Inside the fifth tab, using app.py's current global cohort:
context = build_revenue_context(
    filtered, analysis_date=analysis_date, close_range=dates,
    selections=selections, dataset_id=fingerprint, revenue_target=target,
)
synchronize_scope(st.session_state, context)  # BEFORE rendering stored messages
# Show a privacy notice: filtered metrics/details and chat are sent to Groq.
# Only after an explicit chat submission:
if question:
    context = build_revenue_context(
        filtered, analysis_date=analysis_date, close_range=dates,
        selections=selections, dataset_id=fingerprint,
        revenue_target=target, question=question,
    )
    answer = respond(context, question, st.session_state)
```

The scope fingerprint covers the dataset identity, current records, analysis date, selections and planning target. Scope changes clear prior chat before display or requests; changing only the question does not clear conversation. If loading fails, the tab clears its AI history and shows an unavailable state. Empty filtered frames are supported without reverting to the original CSV. Do not copy API config/client objects into session state or render them to the browser.

### Groq behavior and limitations

`respond()` loads only the two named environment settings on the server and creates the official Groq client on an explicit request, with a 25-second timeout and one retry. It supplies at most four recent messages within a 2,000-byte history budget and retains at most 40 successful messages for display. GPT-OSS models use low reasoning effort and a 2,200-token completion budget to leave room for a visible answer; other models keep the 1,100-token budget. Empty or token-limited completions show specific retry guidance and are not added to history. Errors distinguish request size (413), authentication (401), model access (403/404), quota/rate limits (429), timeouts, connections and server failures. Messages are sanitized; raw exception text, credentials and provider account details are never forwarded to UI messages. No browser-side API call, external tools, trading/actions, Salesforce write-back or credential input widget is included. Credentials are read server-side from the existing .env or environment; do not enter them into chat.

The system instruction requires interpretation of supplied facts only and forbids new arithmetic, causal speculation, fabricated numbers, historical pipeline claims and invented explanations. Prompt safeguards cannot guarantee model compliance; responses must be reviewed against dashboard facts. Live response quality and account/model access are not verified by mocked tests. UI tests mock Groq. Live API access and response quality have not been verified; requests occur when you submit a question in the app.

Run all tests, including the credential-free optional-service mocks:

```sh
uv run --extra ai pytest -q
```
