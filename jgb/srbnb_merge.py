"""One-off merge: consolidate divisional SRNB accounts (2501-2505) into 2220.

Snapshots every table that holds an Account link to the source accounts into
zbackup_srbnb_* tables BEFORE merging (merge rewrites links in place and
deletes the source Account docs - irreversible).

Run:
	bench --site erp.jgbksa.com execute jgb.srbnb_merge.run
"""

import time

import frappe
from frappe.model.rename_doc import get_link_fields
from frappe.utils import cstr

scrub = frappe.scrub

TARGET = "2220 - Stock Received But Not Billed - JGB"
SOURCES = [
	"2501 - Stock Received But Not Billed - HVAC - JGB",
	"2502 - Stock Received But Not Billed - Valves & Pipelines - JGB",
	"2503 - Stock Received But Not Billed -Waterworks - JGB",
	"2504 - Stock Received But Not Billed - Filtration - JGB",
	"2505 - Stock Received But Not Billed - Misting - JGB",
]
GROUP = "2500 - Stock Received But Not Billed - JGB"
PREFIX = "zbackup_srbnb_"


def _backup_name(*parts):
	return (PREFIX + "_".join(scrub(p) for p in parts))[:60]


def _in_list(values):
	return "(" + ", ".join(frappe.db.escape(v) for v in values) + ")"


def _create_backup(name, create_sql):
	frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{name}`")
	frappe.db.sql_ddl(create_sql)
	cnt = frappe.db.sql(f"SELECT COUNT(*) FROM `{name}`")[0][0]
	print(f"  {name}: {cnt} rows")
	return cnt


def backup_tables():
	print("=== Backing up affected rows ===")
	in_all = _in_list(SOURCES + [GROUP])
	in_src = _in_list(SOURCES)

	# the Account docs themselves (sources get deleted, group gets disabled)
	_create_backup(
		_backup_name("account"),
		f"CREATE TABLE `{_backup_name('account')}` AS SELECT * FROM `tabAccount` WHERE name IN {in_all}",
	)

	total = 0
	for lf in get_link_fields("Account"):
		doctype, fieldname = lf["parent"], lf["fieldname"]
		if lf.get("issingle"):
			bname = _backup_name("singles", doctype, fieldname)
			total += _create_backup(
				bname,
				f"CREATE TABLE `{bname}` AS SELECT * FROM `tabSingles` "
				f"WHERE doctype={frappe.db.escape(doctype)} AND field={frappe.db.escape(fieldname)} "
				f"AND value IN {in_src}",
			)
			continue

		if not frappe.db.table_exists(doctype):
			continue
		bname = _backup_name(doctype, fieldname)
		total += _create_backup(
			bname,
			f"CREATE TABLE `{bname}` AS SELECT * FROM `tab{doctype}` WHERE `{fieldname}` IN {in_src}",
		)
	print(f"=== Backups done, {total} rows snapshotted ===")


def merge_one(old, retries=20):
	from erpnext.accounts.doctype.account.account import merge_account

	for attempt in range(retries):
		try:
			merge_account(old, TARGET)
			frappe.db.commit()
			print(f"  merged {old}")
			return
		except Exception as e:
			frappe.db.rollback()
			if "actively being used" in cstr(e) and attempt < retries - 1:
				print(f"  system busy, waiting 60s (attempt {attempt + 1})...")
				time.sleep(60)
			else:
				raise


def verify():
	print("=== Post-merge verification ===")
	gle = frappe.db.sql(
		f"SELECT COUNT(*) FROM `tabGL Entry` WHERE account IN {_in_list(SOURCES)}"
	)[0][0]
	print(f"  GL rows still on old accounts: {gle} (expect 0)")
	gle_new = frappe.db.sql(
		"SELECT COUNT(*), SUM(debit-credit) FROM `tabGL Entry` WHERE account=%s", (TARGET,)
	)[0]
	print(f"  GL rows on 2220: {gle_new[0]}, net: {gle_new[1]}")
	for row in frappe.db.sql(
		f"SELECT name FROM `tabAccount` WHERE name IN {_in_list(SOURCES)}"
	):
		print(f"  WARNING: leftover account {row[0]}")
	dad = frappe.db.sql(
		"SELECT parent, snrb_account FROM `tabDivision Account Details` WHERE company='Joint Global Business Co LLC'",
		as_dict=True,
	)
	for d in dad:
		print(f"  DAD {d.parent} -> {d.snrb_account}")


def run():
	backup_tables()

	print("=== Merging ===")
	for src in SOURCES:
		merge_one(src)

	print("=== Disabling empty group 2500 ===")
	frappe.db.set_value("Account", GROUP, "disabled", 1)
	frappe.db.commit()

	verify()
	print("=== Done ===")
