# Sales Estimation Process — Reference Guide

> **Purpose:** How cost estimation and margin pricing work on **Quotation → Sales Order →
> Purchase Order** in ERP (site `erp.jgbksa.com`, app `jgb`).
> Written for sales/pricing users and future maintainers.
>
> **Companion technical doc:** `apps/jgb/ESTIMATION_TABLE.md` (full issue log, fixes,
> and verification history — Sep 2026 overhaul).
>
> **Last updated:** 2026-09-13

---

## 1. What the Estimation Table Is

The **Estimation table** (`Estimation Details` child table) is the costing backbone of a
quotation. It builds the **total landed cost estimate** of a deal:

```
Total Estimated Cost (SAR)
    = Cost of Item        (auto = Σ item cost, always synced)
    + Freight / Transportation
    + Customs Duty, Clearance, SABER, Bank Charges
    + Installation charges (manpower / equipment / materials / food & accommodation / others)
    + any other cost head picked from the "Estimation" list (~86 records)
```

From this estimate the system derives pricing and margins:

| Field | Label | Meaning |
|---|---|---|
| `custom_total_estimated_value` | Total Estimated Cost (SAR) | Σ of all estimation row values |
| `custom_quote_value` | Quote Value / SO Value (SAR) | Σ (qty × rate) − discount — **net of discount** |
| `custom_estimation_margin` | **Profit on Sales** | (Quote − Estimate) / Quote × 100 |
| `custom_margin_on_cost` | **Contribution Margin** | (Quote − Estimate) / Estimate × 100 |

Relationship: `Profit on Sales = Margin-on-Cost / (1 + Margin-on-Cost/100)`
(e.g. 25% margin-on-cost ≡ 20% profit-on-sales).

---

## 2. Where It Lives

| Doctype | Estimation fields | Notes |
|---|---|---|
| **Quotation** | "Estimation" tab: table + totals + margins + buttons + HTML dashboards | Where estimation is built |
| **Sales Order** | Same set (SO Value = net of discount) | Mirrors the quotation |
| **Purchase Order** | Same table; Order Value & margins are **copied from the SO** at creation | PO margins are measured against the SO's sales value, not the PO's purchase total |

Child table fields (`Estimation Details`):

| Field | Type | Purpose |
|---|---|---|
| `title_of_estimation` | Link → Estimation | Cost head (freight, customs, installation, …) |
| `percen` | Percent | Row's % share of the estimate |
| `value` | Currency | Value in **SAR** |
| `value_quotation_currency` | Currency | Value in the document currency |

Server-side safety net: `jgb.jgb.custom.update_total_est_value` runs on Quotation
**validate** and re-sums the totals (covers API / Data Import / server flows).

---

## 3. Building an Estimation on a New Quotation

1. **Default rows are seeded automatically** on a new, empty quotation (11 rows):
   Cost of Item, Customs Duty, Freight & Delivery - 5% Calculated Default,
   Customs Clearance Charges, SABER Charges, Bank Charges, and the five
   Installation Charges rows.
2. **Cost of Item is always auto-synced** — its value = Σ item cost
   (`custom_cost_amount_sar` rollup). It cannot be held manually.
3. **Freight & Delivery - 5% row** auto-fills `5% × Σ item cost` — but only **once**,
   while its value is still 0, and only when a cost recalculation runs
   (item cost/qty/multiplier change). After that it is user-owned. If the row is
   deleted, nothing re-adds it (defaults seed only on new, empty quotations).
4. **All other rows are manual** — pick any head from the Estimation list
   (Transportation Charge, Air Freight, Port Charges, …) and enter a value.
   Entering a `value` computes `percen` (value ÷ Σ item cost); entering a `percen`
   computes the `value` and the document-currency value.
5. Totals, Profit on Sales, and Contribution Margin recompute live; the
   **"Estimated vs Quotation Value"** HTML table (green/red margins) re-renders.

> **Excel import** (Pennbarry / Hattersley / Antec Controls flows) creates **items only** —
> it never touches the estimation table.

---

## 4. Margins — How to Adjust Profit on Sales

Profit on Sales is **read-only** — it is always derived. You adjust it by moving one
of its two inputs:

### A. Target margin → price the quote (most common)
1. Tick **"Derive Quoted Value based on -Margin Cost"** (this also reveals the
   Contribution Margin field).
2. Enter the target in **Contribution Margin** (e.g. 25).
3. Click **Update Quote** → item rates are raised so the quote yields that margin.
   Profit on Sales recomputes automatically (25% margin-on-cost ⇒ 20% profit-on-sales).

### B. Quote fixed → adjust the cost side
Edit estimation rows (overheads) or item costs. Estimate ↑ ⇒ Profit on Sales ↓.

### C. Multiplier route
`custom_multiplier_percentage` recalculates all item net costs → Cost of Item →
estimate → margins.

### D. Discount route
`discount_amount` reduces the **net** quote value → Profit on Sales falls.
(SO Value is net-of-discount everywhere since the Sep 2026 fix.)

---

## 5. Per-Item Profit Share (added Sep 2026)

Each item row (Quotation Item, Sales Order Item) carries its own share of the profit:

| Field (in row detail, not in grid) | Type | Meaning |
|---|---|---|
| `custom_profit_on_sales_percentage` | Percent | This item's profit as % of its own cost |
| `custom_profit_on_sales_amount` | Currency (SAR) | Profit allocated to this item |

**Behavior:**

| Action | Effect |
|---|---|
| Edit Profit % / Profit Amount on one row | **Only that row's rate changes** (`rate = (cost + profit) / qty / conversion_rate`). Other rows untouched. Margin % absorbs the variation. |
| Edit an item's **rate** directly | That row's profit fields back-compute (`profit = rate × qty × conv − cost`). Other rows untouched. |
| **Update Quote** button | Explicit *reset to default distribution*: total profit (estimate × margin-on-cost%) shared across items **proportional to item cost** (100% of profit distributed), filling every row's profit fields. |
| **Update Cost** button | Cost-side only — profit shares and rates survive; margin % absorbs. |
| Currency / conversion-rate change | Rates re-derived from **cost + profit share** (manual variations survive). |

The two fields are hidden from the grid (visible in the row dialog) to keep the grid
layout as it was; users can re-enable the columns per-user via grid settings.

---

## 6. The Two Buttons

| Button | What it does | Direction |
|---|---|---|
| **Update Quote** (`custom_update_quote`) | Distributes the **margin** into item **rates** (via per-item profit shares) | margin → price |
| **Update Cost** (`custom_update_cost`) | Distributes the **extra cost** (estimate − item cost) back into items' `custom_other_cost(_sar)`, proportional to item cost | estimate → cost |

Order of operations on a draft: **fill the estimation table first**, then Update Quote.
With a zero estimate, Update Quote aborts with a message (guard added Sep 2026).

---

## 7. Downstream Flow (Quotation → SO → PO)

```
Quotation (estimation built here, margins derived)
   └─ Sales Order   — items/rates carry over; SO Value is net of discount
         └─ Purchase Order — estimation (rows + Order Value + margins) COPIED from the SO
                             at creation; margins computed from the copied values
```

- The PO copy (`jgb.utils.update_estimation_table`) pulls the SO's estimate, quote
  value, and rows. Since Sep 2026 the PO **computes its own margins** from the copied
  values instead of trusting the SO snapshot (fixes POs created before the SO's
  estimation was filled showing 0% profit).
- Submitted documents are **frozen**: margin fields are read-only and recalc triggers
  fire only on item edits. Changes require amend → adjust → resubmit.

---

## 8. Known Behaviors & Caveats

1. **"Cost of Item" matching is tolerant** — both "Cost of Item" and "Cost of Items"
   titles sync with the item-cost rollup.
2. **Freight 5% fills only once** (while the row value is empty); later cost changes do
   not auto-update it — manual edits are preserved.
3. **Default rows deleted pre-save stay deleted** (no re-seeding on refresh).
4. **PO doc-currency column unreliable** — the SO→PO copy only carries the SAR `value`;
   `value_quotation_currency` on POs may be 0 or equal to the SAR value (e.g. AED POs).
   SAR-based totals and dashboards are unaffected.
5. **Two margin bases by design on PO** — copied margins use the SO's sales value; the
   PO's own recalc function uses the PO purchase total. Unifying them is a product decision.
6. **Server hook** `update_total_est_value` re-sums totals on Quotation validate only;
   it does not recompute margins.
7. `bench console` does not auto-commit — call `frappe.db.commit()` explicitly.

---

## 9. Quick Reference — Where the Logic Lives

| Layer | Location |
|---|---|
| Client scripts (DB records, not files) | `Client Script` → `Quotation`, `Sales Order`, `Purchase Order` |
| Server helpers | `apps/jgb/jgb/jgb/custom.py` — `update_total_est_value`, `update_quote_value`, `update_quote_value_by_cost`, `process_uploaded_file` |
| Server helpers | `apps/jgb/jgb/utils.py` — `estimation_details(_so/_po)`, `update_margin_html(_cost)`, `update_estimation_table`, `update_existing_po` |
| Hook | `apps/jgb/jgb/hooks.py` → `doc_events['Quotation']['validate']` |
| Custom fields | `custom_estimation_details`, `custom_quote_value`, `custom_total_estimated_value(_quotation_currency)`, `custom_estimation_margin` / `custom_margin_on_quote`, `custom_margin_on_cost`, `custom_derive_quoted_value_based_on_margin_cost`, `custom_update_quote`, `custom_update_cost`, item-level `custom_profit_on_sales_percentage` / `_amount` |
| Full fix history | `apps/jgb/ESTIMATION_TABLE.md` (Sections 1–9) |

---

## 10. Sep 2026 Overhaul — Summary of What Changed

All issues below were found, fixed, and verified (details in `ESTIMATION_TABLE.md`):

- **Quotation (25 fixes):** save-overwrite typo, dead HTML-refresh calls, div-by-zero/NaN
  guards, wrong-table bug in the percen handler, currency mixing, async exchange-rate race,
  unified margin base, tolerant Cost-of-Item matching, freight 5% default restored,
  default-row resurrection fixed, derive-quote checkbox implemented, consolidated HTML renderer.
- **Sales Order:** SO Value now **net of discount** in all six setters; margins on the net
  basis; currency-arg bug in the renderer fixed; one-time data migration corrected **50 SOs**.
- **Purchase Order:** POJGBKSA2515 profit-on-sales 0% → 19.68% (synced from corrected SO);
  creation-time copy now computes margins itself; 366-PO audit found no other live issues.
- **Per-item profit share feature** added (Section 5) so a single item's rate can be
  adjusted without re-rating all items.
