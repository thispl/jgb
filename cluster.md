# Cluster-Based Sales Document Visibility — Replication Spec

## 1. Purpose

Restrict sales documents (Quotation, Sales Order, Delivery Note, Sales Invoice —
and optionally Opportunity, Visit Report, MARCOM Project Reference) so that:

- A sales person sees **only** the documents belonging to their own **cluster**
  (their sales group/territory team).
- A sales manager sees the documents of the whole cluster/group under them.
- One sales group **cannot** see another group's documents.

Implemented in Frappe/ERPNext via a custom `Cluster` DocType + `cluster` Link
fields + automatically generated **User Permissions**, all driven by a hook on
`Sales Person.after_insert`. This mechanism is company-agnostic — the same code
works for any company; only the Cluster *values* differ.

---

## 2. Architecture Overview

```
Sales Person (created)
   └─ after_insert hook: create_cluster_and_update_up()
        ├─ Creates Cluster doc  "Territory - Sales Person Name"  (linked to user_id)
        ├─ Creates User Permission 1:  allow="Cluster",      for_value=<cluster>, apply_to_all_doctypes=1
        └─ Creates User Permission 2:  allow="Sales Person", for_value=<sales person name>, apply_to_all_doctypes=1

Frappe permission engine (automatic):
   - Any DocType having a Link→"Cluster" field   ⇒ filtered by Cluster User Permission
   - Any DocType having a Link→"Sales Person" field ⇒ filtered by Sales Person User Permission
   - User Permission with apply_to_all_doctypes applies ONLY where a matching
     Link field exists; no code needed per doctype.

Document flow:
   Opportunity.cluster ─┐
   Quotation.cluster ───┼─ (same-name field copy via get_mapped_doc) ─→ Sales Order.cluster
   DN / SI ── restricted via sales_person_user (Link→Sales Person), populated by
              SO→DN / SO→SI get_mapped_doc copying sales_person_user automatically.
```

**Important design fact (match the original exactly):**
Quotation / Sales Order / Opportunity are restricted by the **`cluster` link +
Cluster user permission**. Delivery Note / Sales Invoice have **no** `cluster`
field — they are restricted by the **`sales_person_user` link (Link → Sales
Person) + the Sales Person user permission**. Both user permissions are created
together by the same hook, so replication must create BOTH.

---

## 3. Components to Build

### 3.1 `Cluster` DocType

Module: your app (original: `norden` → app module `Norden`).

| Property | Value |
|---|---|
| `autoname` | `field:cluster` |
| `allow_rename` | 1 |
| `allow_import` | 1 |
| `editable_grid` | 1 |
| `track_changes` | 1 |
| Permissions | `System Manager`: create/read/write/delete/email/export/print/report/share |

Fields:

| fieldname | fieldtype | label | options | flags |
|---|---|---|---|---|
| `cluster` | Data | Cluster | — | `unique: 1` |
| `user` | Link | User | `User` | — |

`cluster.py` is a plain `Document` subclass (`class Cluster(Document): pass`).

Cluster record names follow `"<Territory> - <Sales Person Name>"`
(e.g. `Dubai - Binu A G`). For a multi-company reuse you may optionally prefix
the company, e.g. `NCPL - India - John`, to avoid name clashes on a shared site.

### 3.2 Custom Fields (Link → Cluster)

Add via **Customize Form** or export as `fixtures: ["Custom Field"]`:

| DocType | fieldname | insert_after | allow_on_submit |
|---|---|---|---|
| Quotation | `cluster` | `territory` | 1 |
| Sales Order | `cluster` | `represents_company` | 1 |
| Opportunity | `cluster` | `transaction_date` | 0 |
| (optional) MARCOM Project Reference | `custom_cluster` | `custom_territory` | 0 |

All: `fieldtype: Link`, `options: Cluster`, `label: Cluster`,
`ignore_user_permissions: 0` (must stay 0 — otherwise the user permission is
bypassed).

**Do NOT add `cluster` to DN/SI** unless you want stricter parity than the
original (see §3.4 note). The original relies on `sales_person_user` there.

### 3.3 Supporting Custom Fields (required by the mechanism)

| DocType | fieldname | fieldtype | options | fetch_from |
|---|---|---|---|---|
| Quotation | `sales_person_user` | Link | Sales Person | — |
| Quotation | `sale_person` | Link | User | `sales_person_user.user_id` |
| Sales Order | `sales_person_user` | Link | Sales Person | — |
| Sales Order | `sale_person` | Link | User | `sales_person_user.user_id` |
| Sales Invoice | `sales_person_user` | Link | Sales Person | — |
| Sales Invoice | `sale_person` | Link | User | — |
| Delivery Note | `sales_person_user` | Link | Sales Person | — |
| Delivery Note | `sale_person` | Link | User | — |
| Opportunity | `sale_person` | Link | User | — |
| Sales Person | `custom_territory` | Link | Territory | — |

(`sale_person`/`sales_person_user` may already exist on some doctypes — reuse.)

### 3.4 Server Code

App `hooks.py` — doc_events:

```python
doc_events = {
    "Sales Person": {
        "after_insert": "<your_app>.custom.create_cluster_and_update_up"
    },
    # optional (only if replicating workflow-email routing):
    "Quotation": {
        "validate": ["<your_app>.utils.quotation_workflow_alert"]
    },
}
```

`<your_app>/custom.py`:

```python
@frappe.whitelist()
def create_cluster_and_update_up(doc, method):
    # 1. Create the Cluster record named "<territory> - <person name>"
    cluster = frappe.new_doc("Cluster")
    cluster.cluster = doc.custom_territory + ' - ' + doc.sales_person_name
    cluster.user = doc.user_id
    cluster.save(ignore_permissions=True)
    frappe.db.commit()

    # 2. User Permission: this user may only see docs in their Cluster
    #    (applies to every doctype with a Link->Cluster field: Quotation, SO,
    #     Opportunity, Visit Report, MARCOM ref)
    user_per = frappe.new_doc("User Permission")
    user_per.user = doc.user_id
    user_per.allow = "Cluster"
    user_per.for_value = cluster.name
    user_per.apply_to_all_doctypes = 1
    user_per.save(ignore_permissions=True)

    # 3. User Permission: this user may only see docs for their Sales Person
    #    (covers DN/SI/SO/Quotation via sales_person_user field)
    user_per = frappe.new_doc("User Permission")
    user_per.user = doc.user_id
    user_per.allow = "Sales Person"
    user_per.for_value = doc.name
    user_per.apply_to_all_doctypes = 1
    user_per.save(ignore_permissions=True)
```

`<your_app>/utils.py` — lookup used by client scripts to auto-fill `cluster`:

```python
@frappe.whitelist()
def set_cluster(sales_person):
    # sales_person here is the *User* id (email); Cluster.user stores user_id
    doc = frappe.get_value("Cluster", {"user": sales_person})
    if doc:
        return doc
```

Optional — bulk backfill used in the original for historical Sales Orders:

```python
def update_quotation_cluster(import_file):
    filepath = get_file(import_file)
    rows = read_csv_content(filepath[1])
    for pp in rows:
        if frappe.db.exists('Sales Order', {'name': pp[1]}):
            frappe.db.sql(
                "update `tabSales Order` set cluster = '%s' where name = '%s'"
                % (pp[6], pp[1]))
```

### 3.5 Client Scripts

**Quotation (Form)** — on `sale_person` change, resolve and set `cluster`:

```javascript
frappe.ui.form.on('Quotation', {
    sale_person(frm) {
        if (frm.doc.sale_person) {
            frappe.call({
                method: "<your_app>.utils.set_cluster",
                args: { 'sales_person': frm.doc.sale_person },
                callback(r) {
                    if (r.message && r.message != frm.doc.cluster) {
                        frm.set_value("cluster", r.message);
                    }
                }
            });
        }
    }
});
```

Same handler on **Opportunity** (`sale_person` trigger). The original
Opportunity script additionally keeps a hardcoded `email → cluster name`
fallback map for ~20 salespeople — optional, only needed if Cluster/User
records are not yet in place.

**No client code on Sales Order** — `cluster` is copied automatically from
Quotation by `get_mapped_doc` in `make_sales_order` (same-named fields on
source/target map automatically; it's not in `field_no_map`). Likewise,
`sales_person_user` propagates SO → DN and SO → SI automatically.

### 3.6 Manager / Hierarchy Access

The hook grants each sales person permission to **their own** cluster only.
For a **sales manager** to see the whole group, create additional
`User Permission` records for the manager's user (manually or by a script):

- `allow = "Cluster"`, `for_value = <each cluster in the manager's group>`,
  `apply_to_all_doctypes = 1`
- and/or `allow = "Sales Person"`, `for_value = <each subordinate's Sales
  Person record>`, `apply_to_all_doctypes = 1`

Alternative grouping model: name the Cluster after the *team* (e.g.
`Dubai - Team A`) rather than the person, set that shared cluster on all team
members' documents, and give every member (incl. the manager) one Cluster user
permission. Pick one convention — the original uses `"Territory - Person"`.

### 3.7 Optional — Workflow Approval Routing by Cluster

In the original, `cluster` also routes approval emails via a `Workflow
Approval` config doctype (rows: `company`, `territory`, `cluster`, `role`,
`user` in an `Approvers` child table). On Quotation `validate`, an email is
sent to the approver where `doc.cluster == row.cluster` **and**
`doc.company == row.company` **and** `doc.price_list_region == row.territory`
**and** the role matches the pending workflow state
(`Sales Manager`/`Sales Master Manager`, `Operation Director`, `COO`, `HOD`,
`Accounts User`, `Purchase Master Manager`). Hidden Check fields
(`so_check`, `op_check`, `coo_check`, `work_flow`) prevent duplicate sends.
Only include this if the target company wants the same approval matrix; the
visibility mechanism does not depend on it.

### 3.8 Optional — MARCOM Project Reference propagation

On Sales Order `on_submit`, the original creates a `MARCOM Project Reference`
and copies `si.cluster → custom_cluster` (plus territory, qty, consultant
fields). Include only if that doctype is being replicated too.

---

## 4. Backfill for Existing Documents

New user permissions only help if documents actually carry a value:

1. Set `cluster` on existing Quotations/SOs (script/SQL like §3.4 backfill, or
   derive from `sales_person_user` → its `user_id` → `Cluster.user` lookup).
2. Ensure `sales_person_user` is populated on existing DN/SI/SO (it may already
   exist in the data).
3. Decide on blank-value behaviour:
   - By default, Frappe does **not** apply user permissions where the link
     field is empty — docs with blank `cluster`/`sales_person_user` stay
     visible to everyone.
   - Enable **System Settings → Apply Strict User Permissions** (or backfill
     all historical docs) to close that gap.
   - Optionally mark `cluster` `reqd` on new transactions as hardening.

---

## 5. Caveats / Gotchas

- **Two permissions, not one.** Both `Cluster` and `Sales Person` user
  permissions are needed — DN/SI are covered only by the Sales Person one.
- **`apply_to_all_doctypes=1`** applies the restriction to every doctype that
  has a matching Link field — no per-doctype config needed, but any *other*
  doctype gaining a `cluster`/`sales_person_user` link automatically becomes
  restricted too.
- `ignore_user_permissions` must be `0` on the link fields (default).
- **Administrator** and any role exempted via Role Permissions Manager bypass
  user permissions; `ignore_permissions=True` saves in server code bypass too.
- Cluster names are unique; renaming a Sales Person does **not** rename the
  cluster — add rename handling if needed.
- `cluster` on Quotation/SO uses `allow_on_submit=1` so it stays editable on
  submitted docs when corrections are needed.
- Server functions elsewhere in the app often use `ignore_permissions=True`
  (e.g. MARCOM creation on SO submit) — they still run for restricted users.
- The feature is doctype-agnostic w.r.t. company — no `company` field on
  Cluster; reuse the same DocType across companies on a shared site, but keep
  cluster names unique (consider a company prefix).

---

## 6. Replication Checklist (new company)

- [ ] Create `Cluster` DocType (fields `cluster` unique, `user` Link→User;
      `autoname: field:cluster`; System Manager perms).
- [ ] Ensure Sales Person records have `custom_territory` and `user_id` filled.
- [ ] Add `cluster` Link→Cluster on Quotation (after `territory`,
      allow_on_submit), Sales Order (after `represents_company`,
      allow_on_submit), Opportunity (after `transaction_date`).
- [ ] Verify `sales_person_user`/`sale_person` fields exist on Quotation, SO,
      DN, SI (Link→Sales Person / Link→User; fetch `sale_person` from
      `sales_person_user.user_id` where desired).
- [ ] Add `create_cluster_and_update_up` + `Sales Person.after_insert` hook.
- [ ] Add `set_cluster` whitelisted method + Quotation/Opportunity client
      script on `sale_person`.
- [ ] (Per need) create Cluster docs + User Permissions for **existing** sales
      persons — the hook only fires for new ones; run a one-off loop calling
      the same logic.
- [ ] Create User Permissions for **managers** covering every cluster/
      sales person in their group.
- [ ] Backfill `cluster` (and `sales_person_user`) on existing documents.
- [ ] Decide on *Apply Strict User Permissions* for blank fields.
- [ ] (Optional) Workflow Approval matrix + alert hook; MARCOM propagation.

## 7. Test Plan

1. Create Sales Person A (territory Dubai) → verify Cluster `Dubai - A`
   appears + 2 User Permissions on A's user.
2. Create Sales Person B (territory Singapore) → same checks.
3. Log in as A; create a Quotation with `sales_person_user` = A → `cluster`
   auto-fills `Dubai - A`; submit; create Sales Order → `cluster` carried over.
4. As B: confirm A's Quotation/SO is **not visible** in list/form/search.
5. As A: confirm B's docs are not visible.
6. Create DN/SI against A's SO → `sales_person_user` carried → A sees them,
   B does not.
7. Manager: grant extra Cluster/Sales-Person user permissions → manager sees
   both clusters' docs; a non-manager sees only their own.
8. Blank field check: doc with empty `cluster`/`sales_person_user` visible to
   all unless strict permissions are on — confirm intended behaviour.
