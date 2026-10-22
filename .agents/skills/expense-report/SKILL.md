---
name: expense-report
description: 'Generate a self-contained Vietnamese HTML spending report from the finance SQLite database for a user-specified date range. Use for yêu cầu báo cáo chi tiêu, báo cáo thu chi, thống kê theo thời gian, tạo báo cáo HTML, or monthly spending analysis.'
argument-hint: '<date range, e.g. 2026-10-01 đến 2026-10-22>'
---

# Expense Report

Generate a self-contained HTML report for a period the user supplies. The report focuses on expenses and includes income and net balance for context, with charts, data-driven interpretation, a category summary, and transaction tables. Use the workspace template [report-template.html](./assets/report-template.html) and repeated [currency-section.html](./assets/currency-section.html).

## Procedure

### 1. Resolve the reporting period

1. Accept explicit start/end dates or a clear natural-language period such as “tháng 9/2024” or “từ đầu tháng đến hôm nay”. Treat both start and end calendar dates as inclusive.
2. Resolve relative periods against the current date. State the resolved dates in the report.
3. If the range is missing or ambiguous, ask one concise question before querying. Reject invalid dates and end dates earlier than start dates.
4. Do not silently substitute the current month when the user supplied no period.

### 2. Inspect the database and schema

1. Follow [AGENTS.md](../../../AGENTS.md): inspect the SQLite files in `database/` and inspect live tables/columns before queries. The current expected location is `database/finance.db`, but verify it exists and is unambiguous each run.
2. Use a read-only SQLite connection (URI `mode=ro` and `PRAGMA query_only=ON`). Never create or modify the database, schema, settings, or transaction records while reporting.
3. Confirm that the live schema supports `transactions` (`type`, `amount`, `currency_code`, `occurred_at`, `category_id`, optional `payment_method_id`, `description`), `categories`, and the needed foreign keys. If it does not, stop and explain the mismatch; do not guess column names.
4. If no database exists or multiple finance databases are ambiguous, ask the user which database to use or state that a report cannot be generated yet.

### 3. Query only the requested period

Use parameterized, read-only queries. Filter `occurred_at` by calendar date inclusively, using SQLite `date(occurred_at) BETWEEN ? AND ?` with bound `YYYY-MM-DD` start and end values. Join categories for names; optionally join payment methods only if their details are included. Retrieve relevant transaction rows and aggregate amounts in application memory with `Decimal(str(amount))`, quantized to `0.01`; avoid SQLite `SUM()` on decimal-affinity values to prevent binary-float rounding artifacts. Query:

- Transactions in the period, ordered by `occurred_at`, then `id`.
- Rows by `currency_code` and `type` (income/expense) for the selected period.
- Expense rows by currency and category, and by currency/date for category and trend summaries.
- Rows for the comparison period so its totals can be aggregated the same way.

Do not query receipt file paths or unrelated personal data. Do not include bank account numbers or other sensitive details in the report. Use only data from the selected period. Do not assume a transaction is confirmed based on attachment content; this database stores transactions already recorded by the entry workflow.

### 4. Calculate and interpret

For each currency separately:

- Calculate total expense, total income, and net (`income - expense`). Never add or compare amounts across different currencies; do not invent or fetch exchange rates.
- Calculate category share as category expense divided by total expense. If total expense is zero, avoid division and show an empty/zero state.
- Compare expenses against the user-selected period's previous-month equivalent: for a complete calendar month, use the previous full calendar month; for month-to-date, use the same calendar dates in the previous month (clamp the end date to that month's last day); for a custom date range, shift both boundaries back one calendar month and clamp invalid day numbers. State the exact comparison dates. Do not compare different currencies.
- Show total expense change and per-category changes. Calculate absolute change as current minus comparison; calculate percentage change as `(current - comparison) / comparison * 100` only when the comparison amount is nonzero. Otherwise label percentage as “không xác định” and show the absolute change.
- Identify factual patterns such as the largest spending category, highest-spend date/bucket, number of transactions, and average expense per calendar day (including days with no spending) when meaningful. Clearly label calculations and avoid unsupported explanations, financial advice, or causal claims.
- Use daily buckets for periods up to 93 days; use monthly buckets for longer periods to keep the chart readable. Report the chosen bucket interval.
- If there are no transactions, still create a valid HTML report with zero/empty-state summaries and explain that no records were found for the period.
- If the result contains more than 1,000 transactions, ask whether to narrow the period or include all transaction rows. Never silently truncate records.

### 5. Render the HTML report

1. Fill [report-template.html](./assets/report-template.html); repeat [currency-section.html](./assets/currency-section.html) once per currency found. If there are no transactions, use the configured currency from `app_settings` if available; otherwise label currency as unspecified and do not imply a zero balance in a known currency.
2. Include the resolved reporting period, generation date/time, a per-currency section with summary cards, an expense-by-category chart, an expense trend chart, concise interpretation bullets, a comparison summary/table, a category summary table, and a transaction detail table. Label each chart's daily/monthly bucket interval and the comparison date range.
3. Generate charts as inline SVG with accessible `<title>`/`<desc>` and text/table fallbacks. Keep the report self-contained: inline CSS and SVG only; no remote scripts, fonts, images, or chart services.
4. HTML-escape every value from the database or user input before inserting it into text, attributes, table cells, or SVG labels. Generate chart markup only from validated numeric values; never interpolate untrusted text as markup. Redact account-like digit sequences (8 or more consecutive digits) from descriptions before rendering.
5. Format amounts to two decimal places and use the corresponding currency code in labels. Preserve negative net values and label them clearly. Use the user's language; default to Vietnamese.
6. Save UTF-8 HTML under `reports/expense-report-<start>-to-<end>.html`. Create `reports/` if needed. Never overwrite an existing report; append `-02`, `-03`, etc. to choose the next unused name.

### 6. Verify and report completion

- Confirm the file exists and is non-empty; read it back and check the expected period, currency sections, summary, interpretation, and tables are present.
- Report the saved file path, period, currency/currencies, and transaction count. Link the generated HTML file in the final response.
- If the query or rendering fails, report the error and do not claim a report was created.

## Data model reference

The live schema is authoritative. In the current finance database, `transactions.amount` is `DECIMAL(16,2)`, `currency_code` stores the currency, `occurred_at` stores ISO-8601 text, and `category_id` references `categories.id`. Income and expense kinds are stored in `transactions.type`. The `app_settings` table may be empty; do not infer a configured currency when it has no row.
