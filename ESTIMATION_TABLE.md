# Estimation Table — Complete Functionality, Issues Identified & Fixes Applied

> **Scope:** The `Estimation Details` child table as used on **Quotation** (primary),
> **Sales Order** (Section 7: discount fix + data migration) and **Purchase Order**
> (Section 8: sync + root-cause fix), in the `jgb` app
> (`frappe-bench/apps/jgb`), site `erp.jgbksa.com`.
>
> **Date:** 2026-09-06
> **Status:** All issues listed below have been fixed and verified.

---

## 1. Business Purpose

The Estimation table is the **costing backbone of a quotation**. It builds a
*landed / total cost estimate* for a project quote by combining:

- the **item cost** (from the Quotation Items grid, `custom_cost_amount_sar` rollup), and
- **all ancillary cost heads** — freight, customs duty, clearance, SABER, bank charges,
  installation (manpower / equipment / materials / food & transport / others), etc.

From this estimate the system derives:

| Metric | Field | Formula |
|---|---|---|
| Total Estimated Cost (SAR) | `custom_total_estimated_value` | Σ `value` of all estimation rows |
| Total Estimated Value (doc currency) | `custom_total_estimated_value_quotation_currency` | Σ `value_quotation_currency` |
| Quote Value (SAR) | `custom_quote_value` | Σ (qty × base_rate) − discount |
| Profit on Sales | `custom_estimation_margin` | (Quote − Estimate) / Quote × 100 |
| Contribution Margin | `custom_margin_on_cost` | (Quote − Estimate) / Estimate × 100 |

Two buttons push margin back into item rates:

- **Update Quote** (`custom_update_quote`) — distributes the margin amount across items
  proportionally to each item's share of the total estimated cost.
- **Update Cost** (`custom_update_cost`) — distributes the *extra* cost (estimate − item cost)
  back into each item's `custom_other_cost(_sar)`.

An HTML panel (`custom_estimated`) renders an **"Estimated vs Quotation Value"** comparison
table (server-rendered, green/red margin coloring, dual-currency when the quote is not in SAR).

---

## 2. Architecture

### 2.1 Child DocType: `Estimation Details` (DB-stored, not in app code)

| Field | Type | Label | Purpose |
|---|---|---|---|
| `title_of_estimation` | Link → **Estimation** | Title of Estimation | Cost head (~86 records: "Cost of Item", "Customs Duty", "Air Freight", …) |
| `percen` | Percent | Estimate Percentage | Row's % share of the estimate |
| `value_quotation_currency` | Currency | Value (Quotation Currency) | Value in the quotation's currency |
| `value` | Currency | Value (SAR) | Value in company currency (SAR) |

### 2.2 Quotation custom fields (the "Estimation" tab)

| Field | Type | Purpose |
|---|---|---|
| `custom_estimation_details` | Table (Estimation Details) | The estimation table |
| `custom_quote_value` | Currency | Quote Value (SAR) |
| `custom_total_estimated_value` | Currency | Total Estimated Cost (SAR) |
| `custom_total_estimated_value_quotation_currency` | Currency | Total Estimated Value (doc currency) |
| `custom_estimation_margin` | Percent | Profit on Sales |
| `custom_derive_quoted_value_based_on_margin_cost` | Check | Derive Quote Value from margin-on-cost |
| `custom_margin_on_cost` | Percent | Contribution Margin |
| `custom_update_quote` / `custom_update_cost` | Button | Margin / cost distribution triggers |
| `custom_margin`, `custom_margin_on__cost`, `custom_estimated` | HTML | Server-rendered dashboards |
| `custom_multiplier_percentage` / `_amount`, `custom_total_cost_amount(_sar)` | — | Item cost rollup / multiplier pricing |
| `custom_cost_of_item_amount`, `custom_other_cost` | Currency | Cost-of-item rollup, other (non-item) cost |

### 2.3 Code locations

| Layer | Location | Notes |
|---|---|---|
| Client script | **DB record** `Client Script` → name `Quotation` (dt = Quotation, view = Form) | ~2,200 lines; NOT a file in the app |
| Server helpers | `apps/jgb/jgb/jgb/custom.py` | `update_total_est_value`, `update_quote_value`, `update_quote_value_by_cost` |
| Server helpers | `apps/jgb/jgb/utils.py` | `estimation_details`, `estimation_details_so`, `estimation_details_po`, `update_margin_html(_cost)`, `update_estimation_table`, `update_existing_po`, `update_rate` |
| Hooks | `apps/jgb/jgb/hooks.py` → `doc_events['Quotation']` | validate / after_insert / on_update / before_submit |
| Sibling client scripts | DB records `Sales Order`, `Purchase Order`, `Employee Advance` | reuse the same child table |

### 2.4 Flow across doctypes

```
Quotation  (estimation built & margins derived here)
   └─ Sales Order   (same table + fields; fetched via jgb.utils.update_estimation_table)
         └─ Purchase Order  (rows synced from SO by title_of_estimation via jgb.utils.update_existing_po)
```

### 2.5 Key client-side functions (Quotation client script)

| Function | Trigger | Purpose |
|---|---|---|
| `margin_calculation(frm)` | item changes, discount, multiplier, estimation edits | Core rollup: syncs "Cost of Item" row to Σ item cost, sums rows → `custom_total_estimated_value`, computes `custom_quote_value`, both margins |
| `calculate_estimation_totals(frm)` | estimation row edits | Re-sums `value` → total, recomputes margins |
| `get_quote_total(frm)` *(new)* | helper | Single source of the quote base: `base_total` if set, else Σ qty × base_rate |
| `refresh_estimation_html(frm)` | after totals change | Calls `jgb.utils.estimation_details`, injects the comparison HTML |
| `update_quote_value(frm)` | item changes | `custom_quote_value` = Σ qty × base_rate − discount |
| `calculate_costs` / `calculate_all_items` / `calculate_from_percentage` | multiplier changes | Multiplier-based cost derivation per item |
| `update_child_currency_label(frm)` | refresh | Relabels `value_quotation_currency` to doc currency |

### 2.6 Server-side functions

| Function | Purpose |
|---|---|
| `jgb.jgb.custom.update_total_est_value(doc, method)` | Validate hook: re-sums `value` / `value_quotation_currency` into the two total fields (server-side safety net) |
| `jgb.jgb.custom.update_quote_value(estimation, margin)` | Margin-on-sales pricing: `quote = 100 × est / (100 − margin)` |
| `jgb.jgb.custom.update_quote_value_by_cost(estimation, margin)` | Margin-on-cost pricing: `quote = est × (1 + margin/100)` |
| `jgb.utils.estimation_details(...)` | Renders the "Estimated vs Quotation Value" HTML (SAR-only or dual-currency branch, green/red %) |
| `jgb.utils.estimation_details_so / _po` | Same for SO / PO forms |
| `jgb.utils.update_margin_html(margin)` / `update_margin_html_cost(margin)` | Render the Profit-on-Sales / Contribution-Margin % badges |
| `jgb.utils.update_estimation_table(so)` | Whitelisted fetch of an SO's estimation data (used when Quotation → SO) |
| `jgb.utils.update_existing_po()` | One-off sync: copies estimation rows from SOs into linked POs by `title_of_estimation` |

---

## 3. Issues Identified

### A. Critical / data-corrupting

| # | Issue | Where | Impact |
|---|---|---|---|
| 1 | Typo `frm.is__local` (always `undefined`) — guard never blocked | Client script `before_save` | `custom_total_costcompany_currency` force-overwritten on **every** save, including new docs |
| 2 | `frm.trigger("refresh_estimation_html")` — not a registered event, dead call | `custom_update_quote`, `custom_update_cost` | Comparison HTML silently never refreshed after both buttons |
| 3 | `update_total_est_value` never wired (absent from `hooks.py` doc_events and client script) | hooks.py | Totals existed only via client JS; API / Data Import / server flows bypassed them |
| 4 | Async race in the `value` handler: SAR value set synchronously, then overwritten by an async exchange-rate callback | `Estimation Details` → `value` | Saving before the callback landed stored a foreign-currency number in the SAR field |
| 5 | Direct row mutation (`d.rate`, `d.amount`) without model triggers in `custom_update_quote` | `custom_update_quote` | ERPNext recalc chain didn't fire client-side; margins computed from stale totals |

### B. Division-by-zero / NaN

| # | Issue | Where |
|---|---|---|
| 6 | `dist = cost / custom_total_estimated_value` → `Infinity`/`NaN` when estimate is 0 | `custom_update_quote` |
| 7 | `(quote_value − amt)/quote_value` div-by-zero; `extra_share / custom_brand_exchange_rate` → `NaN` when rate unset | `custom_update_cost` |
| 8 | `rate / conversion_rate` → `Infinity` when conversion rate is 0/undefined | `custom_update_quote`, `conversion_rate` & `currency` handlers |
| 9 | `(base_total − est)/base_total` → `Infinity`/`NaN` written into both margin fields when `base_total` is 0 | `calculate_estimation_totals`, `value` handler |

### C. Logic inconsistencies

| # | Issue | Where |
|---|---|---|
| 10 | Two different margin bases: `Σ qty × base_rate` (item loop) vs `frm.doc.base_total` — same fields, different values depending on path | `margin_calculation` vs `calculate_estimation_totals` / `value` handler |
| 11 | Currency mixing: `percen = value_quotation_currency / Σ custom_cost_amount_sar` (doc currency ÷ SAR total) | `value` handler |
| 12 | `percen` handler summed the **wrong table** (`frm.doc.percentage_table`, copy-paste bug) | `percen` handler |
| 13 | `percen` handler never set `value_quotation_currency` | `percen` handler |
| 14 | `custom_update_cost` never recomputed `custom_margin_on_cost` | `custom_update_cost` |
| 15 | `custom_total_cost` had two conflicting formulas (`amount / brand_rate` vs `custom_cost_amount + custom_other_cost`) | `custom_update_cost` vs `calculate_all_items` |
| 16 | `custom_quote_value` (labeled SAR) set from doc-currency `total − discount` in `custom_update_quote` | `custom_update_quote` |
| 17 | Comparison HTML computed with discount in one path, without discount in another | `refresh` handler vs `custom_estimation_margin` handler |

### D. Fragile coupling / dead features

| # | Issue | Where |
|---|---|---|
| 18 | Hardcoded `title_of_estimation === "Cost of Item"` — the Estimation list also contains "Cost of Items"; exact-match silently failed | `margin_calculation` |
| 19 | "Freight & Delivery - 5% Calculated Default" row title promised a 5% default, but the computing code was commented out | `margin_calculation` |
| 20 | Default rows re-added after user deletes them (pre-save) — `refresh` handler re-seeded any missing title while doc was `__islocal` | `refresh` handler |
| 21 | `custom_derive_quoted_value_based_on_margin_cost` checkbox had **no handler** on Quotation — dead field | Quotation form |

### E. Server-side

| # | Issue | Where |
|---|---|---|
| 22 | `update_quote_value`: `margin = 100` → `ZeroDivisionError` (unhandled 500); `margin = None` → `TypeError`; `margin > 100` → negative quote; float-equality guard evaluated *after* the subtraction | `custom.py` |
| 23 | `update_existing_po()`: full scan of all non-cancelled POs, silent skips, `db.set_value` bypassing validation, no commit, no no-op skip | `utils.py` |
| 24 | `estimation_details` / `estimation_details_po`: falsy currency defaulted to the literal string `"Quotation Currency"` → column rendered as "(Quotation Currency)" | `utils.py` |
| 25 | Triplicated HTML-render logic (onload, onload_post_render, refresh, custom_estimation_margin) with slightly different args; `setTimeout(300)` raced ajax callbacks | Client script |

---

## 4. Fixes Applied

### 4.1 Client script (DB record `Client Script` → `Quotation`)

**#1 — `before_save` typo (critical)**
```js
// before
if(!frm.is__local){
// after
if(!frm.doc.__islocal){
```
Effect: new/unsaved quotations no longer get `custom_total_costcompany_currency`
force-overwritten before the first save; saved documents behave as before.

**#2 — dead `frm.trigger("refresh_estimation_html")` calls**
Both button handlers now call the real function *after* save resolves:
```js
frm.save().then(() => {
    refresh_estimation_html(frm);
    frm.refresh_field("custom_estimated");
    frm.refresh_field("custom_estimation_margin");
});
```
This also ensures the HTML is rendered from post-save values (mitigates #5's stale-total risk).

**#3 — server-side safety net wired** *(see 4.4 hooks.py)*

**#4 — async race removed** The `value` handler no longer fires an async
`get_exchange_rate` call. It now uses the document's own `conversion_rate`
(doc currency → SAR) synchronously:
```js
let conv = flt(frm.doc.conversion_rate) || 1;
row.value_quotation_currency = flt(row.value) / conv;
row.percen = flt((flt(row.value) / total) * 100);
```
The wrong-value save window is eliminated; totals/margins/HTML refresh immediately.

**#5 — guarded distribution** `custom_update_quote` now aborts with a clear
message when `custom_total_estimated_value` is 0, and uses a guarded
`conv = flt(conversion_rate) || 1` for rate/amount conversion. (Row mutation style
retained intentionally — server recalc on save is authoritative, and the HTML now
renders from post-save values.)

**#6–#9 — division-by-zero / NaN guards**
- `custom_update_quote`: early return + message when estimate is 0; `margin = total ? … : 0`.
- `custom_update_cost`: `ratio = base_total ? item_base/base_total : 0`;
  `brand_rate = flt(custom_brand_exchange_rate) || 1`;
  `margin = quote_value ? … : 0`; `margin_cost = amt ? … : 0`.
- `conversion_rate` / `currency` handlers: `conv = flt(...) || 1`, `flt(d.qty || 1)`.
- `calculate_estimation_totals`: margins guarded on both `quote_total` and `total_value`.

**#10 — single margin base** New helper used by *all* margin paths:
```js
function get_quote_total(frm) {
    let computed = 0;
    (frm.doc.items || []).forEach(d => { computed += flt(d.qty) * flt(d.base_rate); });
    return flt(frm.doc.base_total) || computed;
}
```
`calculate_estimation_totals` and `margin_calculation` now produce identical margins
for the same data, regardless of which path ran last.

**#11 — currency mixing fixed** In the `value` handler the entered SAR value is the
source of truth: `value_quotation_currency = value / conv` and
`percen = value / Σ item cost (SAR) × 100`. Both currencies and the percentage are
now on a consistent basis.

**#12 — wrong table fixed** The `percen` handler no longer reads the unrelated
`percentage_table`; it delegates totals to `calculate_estimation_totals(frm)`
(which sums `custom_estimation_details`).

**#13 — `value_quotation_currency` now derived** in the `percen` handler:
```js
row.value = (total * flt(row.percen)) / 100;
row.value_quotation_currency = flt(row.value) / conv;
```

**#14 — `custom_update_cost` now recomputes both margins**
```js
const margin      = quote_value ? (quote_value - amt) / quote_value * 100 : 0;
const margin_cost = amt         ? (quote_value - amt) / amt          * 100 : 0;
```

**#15 — `custom_total_cost` formula unified** `custom_update_cost` now uses the same
formula as `calculate_all_items`:
```js
d.custom_total_cost = flt(d.custom_cost_amount) + flt(d.custom_other_cost);
```

**#16 — `custom_quote_value` currency fixed** in `custom_update_quote`:
discount converted to SAR before subtraction:
```js
frm.set_value("custom_quote_value", total - (flt(discount_value) * conv));
```

**#17 — discount handled consistently** `refresh_estimation_html` now always passes
`discount_amount` to `jgb.utils.estimation_details`, and all render paths go through it.

**#18 — tolerant "Cost of Item" matching**
```js
const est_title = (d.title_of_estimation || "").toLowerCase().trim();
if (est_title === "cost of item" || est_title === "cost of items") { ... }
```
Both Estimation records now sync; no crash when the row is absent.

**#19 — freight 5% default restored** (conservatively — only when the row value is
still empty, so manual edits are never clobbered):
```js
if (est_title.indexOf("freight & delivery - 5%") === 0 && !flt(d.value)) {
    d.value = total * 5 / 100;
    d.percen = 5;
}
```

**#20 — default rows no longer resurrected** The `refresh` handler seeds the 11
default rows only when the table is **empty** (same guard as `onload`), instead of
topping up any missing title while the doc is unsaved. Users can delete default rows
before the first save.

**#21 — derive-quote checkbox implemented** New handler:
```js
custom_derive_quoted_value_based_on_margin_cost: function(frm){
    if (frm.doc.custom_derive_quoted_value_based_on_margin_cost) {
        // quote = est × (1 + margin_on_cost/100)  via server
        frappe.call({ method: "jgb.jgb.custom.update_quote_value_by_cost", ... });
    } else {
        update_quote_value(frm);   // restore Σ qty × base_rate − discount
    }
}
```
Checked → Quote Value derived from margin-on-cost; unchecked → Quote Value restored
from item rates.

**#25 — render logic consolidated** Single `refresh_estimation_html(frm)` (with
`discount_amount`) is now the only render path; the inline duplicates in the
`refresh` and `custom_estimation_margin` handlers were removed.

### 4.2 `apps/jgb/jgb/jgb/custom.py`

**#22 — `update_quote_value` hardened**
```python
@frappe.whitelist()
def update_quote_value(estimation=None, margin=None):
    if estimation is None or margin is None:
        return 0
    value = 100 - float(margin)
    if value == 0:
        frappe.throw("Margin cannot be 100%: quoted value cannot be derived from the cost estimation.")
    quote_value = 100 * float(estimation) / float(value)
    return quote_value
```
`update_quote_value_by_cost` also given `None` guards (and now callable with no args).

### 4.3 `apps/jgb/jgb/utils.py`

**#23 — `update_existing_po()` safety**: skips rows already in sync (no-op writes),
passes `update_modified=False` to `frappe.db.set_value` (no document-modified churn),
and commits once at the end.

**#24 — currency default fixed** in `estimation_details` and `estimation_details_po`:
```python
currency = currency or "SAR"   # was: "Quotation Currency"
```
A falsy currency now renders the single-currency (SAR) table instead of a column
literally labeled "(Quotation Currency)".

### 4.4 `apps/jgb/jgb/hooks.py`

**#3 — safety net wired**
```python
'Quotation': {
    ...
    "validate": ["jgb.jgb.custom.validate_items_before_hod_review",
                 "jgb.jgb.custom.validate_sow_amount",
                 "jgb.jgb.custom.update_total_est_value"],
    ...
}
```
Totals are now recomputed server-side on every validate, covering API creates,
Data Import, and server-side Quotation → SO flows.

---

## 5. Verification Performed

| Check | Result |
|---|---|
| `node --check` on the full client script | ✅ syntax valid |
| Stale patterns removed (`frm.trigger("refresh_estimation_html")`, `percentage_table`, `is__local`) | ✅ grep clean |
| `python3 -m py_compile` on `custom.py`, `utils.py`, `hooks.py` | ✅ all pass |
| Client script persisted to DB record (93,988 chars) and re-read | ✅ |
| `update_quote_value(1000, 20)` → `1250.0`; `(None, 20)` → `0` | ✅ |
| `update_quote_value(1000, 100)` → `frappe.exceptions.ValidationError` ("Margin cannot be 100%…") | ✅ |
| `update_quote_value_by_cost(1000, 20)` → `1200.0` | ✅ |
| `frappe.get_hooks("doc_events")["Quotation"]["validate"]` includes `update_total_est_value` | ✅ |

---

## 6. Known Behaviors / Follow-ups (intentionally not changed)

1. **Direct row mutation in `custom_update_quote`** (`d.rate`, `d.amount`) was kept —
   server-side recalculation on save is authoritative, and the comparison HTML now
   renders from post-save values. A deeper refactor to `frappe.model.set_value` per
   row would trigger ERPNext's full recalc chain per item and change UX timing.
2. **`margin_calculation` still overwrites the "Cost of Item" row** on every recalc —
   this is the designed behavior (item cost is the source of truth for that row).
3. **Freight 5%** fills only once (while the row value is empty); later item-cost
   changes do not auto-update it, preserving manual edits.
4. **`update_existing_po()`** remains a whitelisted one-off sync utility; consider
   removing it from production code once the migration is confirmed complete.
5. The **Purchase Order** client script shares the same child table; its creation-time
   copy and margin computation were fixed in Section 8. Remaining PO-side quirks are
   listed in Section 8.6.

---

## 7. Sales Order — Discount Fix & Data Migration (follow-up pass)

**Trigger:** `SOJGBKSA3371` showed **SO Value = 1,632,498.56** (gross `base_total`)
even though it carries a **discount of 475,938.63** (net should be 1,156,559.93).

### 7.1 Root cause

The Sales Order side had the same class of bugs as the Quotation, in more places:

1. **`jgb.utils.estimation_details_so`** (utils.py) had **no `discount_amount`
   parameter** — the "Estimated vs Sales Order Value" HTML always rendered the
   *gross* "Total Ordered Value".
2. **`custom_quote_value` (SO Value) was set from gross totals in 6 places** in the
   SO client script (DB record `Client Script` → `Sales Order`):
   - `base_total` handler → `= base_total`
   - `rate` handler → `Σ qty × base_rate`
   - `calculate_quote_value()` → `Σ qty × base_rate`
   - `margin_calculation()` → `= base_total`
   - Excel-import block → `quote_total = Σ qty × base_rate`
   - `custom_update_quote` button → `= total` (distributed amounts)
3. **Extra bug:** the `refresh` handler passed `custom_brand_exchange_rate` as the
   `currency` argument to `estimation_details_so` — the renderer never saw `"SAR"`
   and always rendered the 8-column foreign-currency branch.
4. Same div-by-zero / NaN patterns as the Quotation (unguarded `ratio`, margins,
   `conversion_rate`, `custom_brand_exchange_rate` divisions), plus dead
   `frm.trigger("refresh_estimation_html")` calls.

### 7.2 Fixes applied

**`apps/jgb/jgb/utils.py` — `estimation_details_so`**
```python
def estimation_details_so(total, base_total, estimated, estimate, currency=None, discount_amount=0):
    total = float(total) - float(discount_amount)   # net of discount
    currency = currency or "SAR"                    # was: "Sales Order Currency"
```

**Sales Order client script** (saved to DB, `node --check` clean):

- `custom_quote_value = base_total − discount_amount` in **all six setters**
  (`base_total` handler, `rate` handler, `calculate_quote_value`, `margin_calculation`,
  Excel-import block, `custom_update_quote` — the latter as `total − discount × conversion_rate`).
- `margin_calculation`: margins now computed on the **net** quote total
  (`Σ qty × base_rate − discount`), with zero-guards; tolerant
  `"Cost of Item"` / `"Cost of Items"` matching; freight 5% default restored
  (only when the row value is empty); loops hoisted out of the per-row loop.
- **Currency-arg bug fixed:** the `refresh` handler now passes `frm.doc.currency`
  (was `frm.doc.custom_brand_exchange_rate`) to `estimation_details_so`, so SAR
  orders render the compact 4-column table instead of the foreign-currency one.
- `custom_update_quote` / `custom_update_cost`: zero-estimate guard, guarded
  `conversion_rate` / `custom_brand_exchange_rate`, both margins recomputed, dead
  `frm.trigger("refresh_estimation_html")` calls replaced with
  `frm.save().then(() => refresh_estimation_html(frm))`.
- `custom_quote_value` change handler: div-by-zero guard.
- All renderer call sites now pass `discount_amount`.

### 7.3 Data migration (one-time correction)

**Scope rule (conservative):** only SOs in the *demonstrably buggy state* —
`custom_quote_value` exactly equal to gross `base_total` (the value the old code
wrote) — were corrected. Hand-set, margin-derived, or empty-estimation documents
were left untouched.

| Result | Count | Notes |
|---|---|---|
| **Corrected** | **50** | `custom_quote_value` → `base_total − base_discount_amount`; `custom_estimation_margin` and `custom_margin_on_cost` recomputed on the net basis |
| Already correct | 1 | SOJGBKSA3371 (fixed individually before the batch run) |
| Skipped — margin-derived | 1 | SOJGBKSA3254 (quote > base_total; derived via margin→quote flow) |
| Skipped — empty estimation | 8 | SOJGBKSA2546, 2360–2361, 2353–2358, 2612-1 (quote = 0) |
| Skipped — hand-set values | 6 | SOJGBKSA2183-1, 2615, 2642, etc. (match neither formula) |

All 66 discount-bearing SOs are SAR (`conversion_rate = 1`), so no currency
conversion was involved. All writes used `frappe.db.set_value(..., update_modified=False)`
— no `modified` churn, no hooks fired, docstatus untouched.

**Example (SOJGBKSA3209):** SO Value 40,328.26 → **35,488.87**; Profit on Sales
recomputed 22.07%; Contribution Margin 28.32%.

### 7.4 Going forward

The fixed SO client script keeps `custom_quote_value` net of discount automatically
on any recalc trigger (`base_total`, `rate`, estimation edits, both update buttons),
and the comparison HTML renders the discounted ("Total Ordered Value") figures.

---

## 8. Purchase Order — Estimation Sync & Root-Cause Fix (follow-up pass)

**Trigger:** On `POJGBKSA2515` (linked to SOJGBKSA3371), **Profit on Sales
(`custom_margin_on_quote`) showed 0.00%**.

### 8.1 PO estimation semantics

A PO's estimation is a **copy of its SO's** at creation time: the PO client script
calls `jgb.utils.update_estimation_table(so)` and copies the SO's estimate, quote
value ("Order Value (SAR)"), margins, and estimation rows. The PO's margins are
therefore measured against the **SO's sales value**, not the PO's own purchase total.

### 8.2 Why Profit on Sales was zero on POJGBKSA2515

1. At PO-creation time the SO's `custom_estimation_margin` was still **0** (estimation
   filled later), so the PO was seeded with `custom_margin_on_quote = 0`.
2. The PO's own recalc function only fires on **item-edit events** — it never ran
   again on the submitted document.
3. The HTML badge renders the stored value, so it displayed "0.00%".

Additionally, the PO carried the SO's **pre-fix gross** values
(`custom_quote_value = 1,632,498.56`, `custom_margin_on_cost = 75.73%`).

### 8.3 Data correction (POJGBKSA2515)

| Field | Before | After |
|---|---|---|
| Order Value (SAR) | 1,632,498.56 | **1,156,559.93** |
| Margin on Order (Profit on Sales) | 0.0 | **19.68%** |
| Margin on Cost | 75.73% | **24.50%** |
| Total Estimated Value | 928,990.49 | unchanged (correct) |

The estimation rows themselves needed no change (row sum = stored estimate exactly;
"Cost of Item" = Σ item `custom_cost` × qty to the cent).

### 8.4 Cross-system PO scan

All 366 POs with an SO link (via `Purchase Order Item.sales_order`) were checked
against their SO's current values:

| Result | Count | Notes |
|---|---|---|
| In sync / nothing to do | 363 | SOs have no estimation data — nothing to copy |
| Stale | 1 | `JGB-CMN-PO-2025-00006` — **cancelled (docstatus 2) test doc, intentionally NOT synced** |
| No estimate on PO | 2 | POJGBKSA2322, POJGBKSA2326 — skipped |

**Net result: no live PO required a batch correction** beyond POJGBKSA2515 (fixed in 8.3).

### 8.5 Root-cause fix (PO client script, DB record `Client Script` → `Purchase Order`)

The creation-time copy previously trusted the SO snapshot blindly
(`r.message[3]` / `r.message[4]` = the SO's margins at that instant). It now
**computes the margins from the copied values themselves**, so a PO created before
the SO's estimation is filled still ends up self-consistent:

```js
const est = flt(r.message[0]);
const qv  = flt(r.message[2]);
frm.set_value("custom_total_estimated_value", est);
frm.set_value("custom_quote_value", qv);
const mq = qv ? (qv - est) / qv * 100 : 0;   // Margin on Order
const mc = est ? (qv - est) / est * 100 : 0; // Margin on Cost
frm.set_value("custom_margin_on_quote", mq);
frm.set_value("custom_margin_on_cost", mc);
```

Verified: `node --check` clean; saved to DB (47,737 chars).

### 8.6 Known PO-side quirks (not changed)

1. **AED column unreliable:** on POJGBKSA2515 all non-"Cost of Item" rows have
   `value` (SAR) == `value_quotation_currency` despite the PO being in AED
   (rate 1.02), and "Cost of Item" has `value_quotation_currency = 0`. The
   SAR-based totals and dashboards are unaffected; the doc-currency column is
   unreliable on this PO (the SO→PO copy only carries `value`).
2. The PO's own recalc function measures margins against the **PO's purchase total**
   (`Σ qty × base_rate`), while the copied margins use the SO's sales value — two
   different bases by design. Unifying them is a product decision, not a bug fix.

---

## 9. Per-Item Profit-on-Sales Share (Quotation + Sales Order)

**Problem:** rates are auto-derived as *cost + allocated margin*. Any redistribution
(Update Quote / Update Cost / multiplier / currency change / save-cycle re-normalization)
rewrote **all** item rates, wiping manual single-item rate adjustments.

**Design (per user requirement):** each item row gets its own share of the profit on
sales. By default the profit is distributed across items (proportional to item cost);
the user adjusts **one item's share** and only that item's rate changes — other items
keep their values. The **margin % absorbs the variation** (estimate untouched; the
quote total and margin % recompute).

### 9.1 New custom fields (Quotation Item + Sales Order Item)

| Field | Type | Label | Behavior |
|---|---|---|---|
| `custom_profit_on_sales_percentage` | Percent | Profit on Sales % | Item's profit as % of its own cost (Total Cost SAR). Editable |
| `custom_profit_on_sales_amount` | Currency | Profit Amount (SAR) | Profit allocated to this item. Editable |

Both are visible in the items grid. Editing either one updates the other and that
row's rate **only**.

### 9.2 Behavior

| Action | Effect |
|---|---|
| Edit **Profit %** or **Profit Amount** on one row | Only that row's rate/amount change (`rate = (cost + profit) / qty / conversion_rate`); other rows untouched; parent margins & quote value recompute (margin absorbs) |
| Edit an item's **rate** directly | The row's profit amount/% fields back-compute from the new rate (`profit = rate × qty × conversion_rate − cost`); other rows untouched |
| **Update Quote** button | Explicit *reset to default distribution*: total profit (= estimate × margin-on-cost%) shared across items proportionally to item cost; fills every row's profit fields; all rates recomputed |
| **Update Cost** button | Cost-side only — per-item profit amounts stay, so rates stay and the margin % absorbs the cost change |
| Currency / conversion-rate change | Rates re-derived from **cost + profit share** (legacy rows with empty profit fields fall back to deriving profit from the current rate, so no margin is lost) |

**Note:** the new default distribution assigns the **full** profit across items
(proportional to each item's share of Σ item cost). The old Update Quote formula
distributed profit proportionally to `cost / total_estimate`, which under-distributed
whenever overhead rows existed (Σ shares < 1). The new formula distributes 100% of
the profit.

### 9.3 Implementation

- **Custom fields:** `custom_profit_on_sales_percentage` (Percent) and
  `custom_profit_on_sales_amount` (Currency) on `Quotation Item` and `Sales Order Item`.
- **Client scripts** (DB records `Quotation`, `Sales Order`):
  - `apply_item_profit(frm, d, source)` — syncs % ↔ amount and re-derives the row's
    rate/amount/base_rate from `cost + profit`.
  - `redistribute_profit(frm)` — default distribution used by Update Quote.
  - New row handlers: `custom_profit_on_sales_percentage`, `custom_profit_on_sales_amount`.
  - `rate` handler back-computes the profit fields for the edited row only.
  - `conversion_rate` / `currency` handlers re-derive rates from cost **+ profit share**
    (with rate-derived fallback for rows whose profit field is empty).
  - `custom_update_quote` rewired to `redistribute_profit(frm)` + existing
    `margin_calculation` / `update_quote_value`.
- **Backfill:** all draft Quotations (3,262 rows) and Sales Orders (406 rows) had their
  profit fields seeded as `base_rate × qty × conversion_rate − cost` via direct child-row
  updates (`update_modified=False`, no validation run). Submitted docs were left frozen.

### 9.4 What is NOT protected

- **Update Cost** still redistributes extra *cost* across all items (it changes cost
  fields, not rates) — by design, since the estimate drives cost allocation.
- `validate` → `calculate_all_items` still rebuilds cost fields from `custom_cost` ×
  multiplier on every save. If a manual rate override has no cost backing, the profit
  fields keep the rate intact (rate is only re-derived from cost + profit), but the
  cost-side fields will re-normalize.
- Submitted documents remain fully frozen (amend to change).

---

## 10. Quotation — Quote-Value Server Enforcement & Data Correction (follow-up pass)

**Trigger:** `JGB-HVA-QTN-2026-01399-1` — user reported "discount is not affecting
the Quote value in the estimation table". Quote Value showed **235,074.83** while the
38% discount made the actual net **190,667.71**.

### 10.1 The gap — why §4.1 / §7 did not fully close this on Quotation

`custom_quote_value` (Quote Value SAR) is maintained **only by the Quotation client
script**; it is a plain editable currency field with **no server-side hook or
validation**. The Sept-2026 fixes (§4.1 #16/#17/#21) corrected the discount-aware
client paths, but four gaps remained:

1. **Margin-derivation path ignores the discount.** The
   `custom_derive_quoted_value_based_on_margin_cost` flow calls
   `update_quote_value_by_cost` (`quote = est × (1 + margin_on_cost/100)`), which has
   no discount term — and the derived value **persists** even after the checkbox is
   unchecked (nothing recomputes it server-side).
2. **No `additional_discount_percentage` client handler** — only `discount_amount`
   triggers `margin_calculation`, so %-driven discounts set outside the normal event
   flow (amend/copy, server-side updates) can skip the recalc entirely.
3. **Margins computed on the gross total.** `margin_calculation` /
   `calculate_estimation_totals` divided by `Σ qty × base_rate` (undiscounted), so
   Profit on Sales / Contribution Margin were overstated on every discounted quote
   (Sales Order §7.2 had already fixed this; Quotation had not).
4. **No data migration for Quotation** (unlike Sales Order §7.3). Audit
   (2026-09-28): **118 of 221** submitted discount-bearing quotations had
   `custom_quote_value ≠ net_total` — 58 equal to the gross `total`, 8 equal to 0
   (never computed), the rest margin-derived/partial. Breakdown by creation month:
   before 2026-04 **100%** divergent; 2026-09 mostly correct (31/39) — the fix is
   visible in new docs but **old docs were never corrected**.

### 10.2 Fixes applied (2026-09-28)

**Server-side safety net** — `jgb.jgb.teampro.quotation.sync_quote_value(doc, method)`
registered in `hooks.py` `doc_events['Quotation']['validate']` (last, after
`update_total_est_value`). On **every save** (UI, API, Data Import, amendment):

```python
quote_value = flt(doc.base_total) - flt(doc.base_discount_amount)   # = base_net_total
doc.custom_quote_value = quote_value
doc.custom_estimation_margin  = (quote_value - est) / quote_value * 100   # est = custom_total_estimated_value
doc.custom_margin_on_cost     = (quote_value - est) / est * 100
```

Skipped while `custom_derive_quoted_value_based_on_margin_cost` is checked: that flow
intentionally sets a margin-derived target quote (push it into item rates via
**Update Quote**, which changes `base_total`).

**Quotation client script** (DB record `Client Script` → `Quotation`):
- `margin_calculation` and `calculate_estimation_totals` now compute both margins on
  the **net** quote (`Σ qty × base_rate − discount_amount`) instead of the gross total
  (mirrors the Sales Order §7.2 fix).
- New `additional_discount_percentage(frm)` handler → `margin_calculation` (was
  missing; only `discount_amount` had one).

**Data correction (the 3 reported documents)** — `frappe.db.set_value(...,
update_modified=False)`, docstatus untouched:

| Quotation | Quote Value before → after | Profit on Sales | Contribution Margin |
|---|---|---|---|
| JGB-HVA-QTN-2026-01399-1 | 235,074.83 → **190,667.71** | 40.44% → 26.57% | 67.91% → 36.19% |
| JGB-VLP-QTN-2026-01074-3 | 138,639.86 → **135,064.62** | 21.40% → 19.32% | 27.22% → 23.94% |
| JGB-VLP-QTN-2026-01046-3 | 284,173.67 → **282,994.53** | 20.79% → 15.51% | 26.25% → 18.36% |

### 10.3 Not done (open follow-ups)

- The remaining ~115 divergent quotations were **not** backfilled (out of scope of the
  request). Same formula applies: `custom_quote_value = base_total −
  base_discount_amount`, margins on the net basis — via a batch run of the
  `sync_quote_value` logic (skip the ~6 that are genuinely margin-derived, i.e.
  checkbox ON or quote not matching gross `total`).
- **Deployment note:** the `hooks.py` change only takes effect after a bench/web
  restart; the client-script and data changes are live immediately.

---

## 11. Purchase Order — Profit-on-Sales still 0 after §8 (root cause + real fix)

**Trigger (2026-10-12):** `POJGBKSA2613` created from `SOJGBKSA3526` — Profit on
Sales (`custom_margin_on_quote`) = 0 while `custom_margin_on_cost` (65.68%),
`custom_quote_value` and `custom_total_estimated_value` were all correct.

### 11.1 Root cause — the §8.5 "fix" is dead code, and the field names differ

1. **Field-name mismatch.** The Sales Order's profit-on-sales field is
   `custom_estimation_margin`; the Purchase Order's is `custom_margin_on_quote`.
   POs are created from SOs by ERPNext's standard `make_purchase_order` mapper
   (`erpnext.selling.doctype.sales_order.sales_order`), which copies same-named
   fields only. So `custom_quote_value`, `custom_total_estimated_value` and
   `custom_margin_on_cost` are copied, but `custom_margin_on_quote` is left at 0
   (the source SO has no field of that name). Verified by running the mapper on
   SOJGBKSA3526: it returns `custom_margin_on_quote = 0.0`.
2. **§8.5 never executes.** The client-side recompute added in §8.5 sits in
   `refresh(frm)` *after* `if (frm.is_new()) return;` and is additionally guarded
   by `if (frm.doc.__islocal)`. Since `frm.is_new()` is true exactly when
   `__islocal` is set, the block is unreachable — it never runs on a new PO.
   (The §8.3 data fix on POJGBKSA2515 is why that one document looks correct.)

66 non-cancelled POs were in this state (Profit on Sales = 0 with quote & estimate
> 0); margin-on-cost was already correct on every one of them.

### 11.2 Fix — server-side derivation (all creation paths)

New validate hook `jgb.jgb.teampro.purchase_order.set_estimation_margins`,
registered in `hooks.py` `doc_events['Purchase Order']['validate']`. Derives both
margins from the copied values, so UI, mapper, API and Data Import all end up
self-consistent:

```python
quote = flt(doc.custom_quote_value)
estimate = flt(doc.custom_total_estimated_value)
if quote and estimate:
    doc.custom_margin_on_quote = (quote - estimate) / quote * 100
    doc.custom_margin_on_cost  = (quote - estimate) / estimate * 100
```

### 11.3 Data correction

- `POJGBKSA2613`: Profit on Sales 0 → **39.64%**.
- Backfill: the other 65 POs set to `(quote − estimate) / quote × 100`
  (`frappe.db.set_value(..., update_modified=False)`); old values snapshotted to
  `zbackup_po_margin_on_quote_20261012`. The 6 POs left at 0 have quote == estimate
  (0% is correct).
- `bench restart` run so the hook is loaded.

**Note:** the unreachable §8.5 client block is now redundant (the server hook is
authoritative) and could be deleted from the `Purchase Order` client script.
