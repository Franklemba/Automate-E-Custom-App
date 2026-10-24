"""Keep UI customizations in this app instead of only in the database.

On the development site (developer_mode on):
- Custom Fields, Property Setters, Client Scripts and Server Scripts created from
  the desk with no module are tagged with this app's module.
- Every save of a tagged record re-exports that doctype's fixture file, so the
  change shows up in `git diff` straight away.
- Deleting a tagged record adds it to deleted_records.json.

On every other site, `bench migrate` imports the fixtures and then deletes the
records listed in deleted_records.json (fixtures alone can only add or update).
"""

import json
import os

import frappe
from frappe.core.doctype.data_import.data_import import export_json

APP = "automatee_custom"

# Requests that save a single document sent from a desk form.
SAVE_CMDS = ("frappe.desk.form.save.savedocs", "frappe.client.insert", "frappe.client.save")


def get_module():
	return frappe.get_hooks("CUSTOMIZATION_MODULE", app_name=APP)[-1]


def claim_for_app(doc, method=None):
	"""Tag a customization made by a person in the desk with this app's module."""
	if doc.get("module") or not _is_dev_session():
		return

	# Only claim what the user is editing directly (or through Customize Form), not
	# records that some other doctype's controller creates as a side effect.
	if _doctype_saved_from_desk() in (doc.doctype, "Customize Form"):
		doc.module = get_module()


def make_doctype_standard(doc, method=None):
	"""A DocType in this app's module must not be "Custom", or it never reaches the files."""
	if doc.module == get_module() and doc.custom and _is_dev_session():
		doc.custom = 0


def queue_export(doc, method=None):
	if doc.get("module") != get_module() or not _is_dev_session():
		return

	_forget_deletion(doc.doctype, doc.name)
	_queue(doc.doctype)


def record_deletion(doc, method=None):
	if doc.get("module") != get_module() or not _is_dev_session():
		return

	deleted = _load_deleted()
	entry = {"doctype": doc.doctype, "name": doc.name}
	if entry not in deleted:
		deleted.append(entry)
		_save_deleted(deleted)
	_queue(doc.doctype)


def apply_deletions():
	"""after_migrate: remove records that were deleted on the development site."""
	for entry in _load_deleted():
		if frappe.db.exists(entry["doctype"], entry["name"]):
			frappe.delete_doc(entry["doctype"], entry["name"], ignore_permissions=True, force=True)
			print(f"automatee_custom: deleted {entry['doctype']} {entry['name']}")
	frappe.db.commit()


def export_all():
	"""Rewrite every fixture file. Same result as `bench export-fixtures --app automatee_custom`."""
	for fixture in frappe.get_hooks("fixtures", app_name=APP):
		_export(fixture)


def _queue(doctype):
	# Export once per doctype, after the transaction commits, so the file never
	# holds changes that were rolled back.
	pending = frappe.flags.setdefault("automatee_custom_exports", set())
	if not pending:
		frappe.db.after_commit.add(_export_pending)
	pending.add(doctype)


def _export_pending():
	pending = frappe.flags.pop("automatee_custom_exports", None) or set()
	for fixture in frappe.get_hooks("fixtures", app_name=APP):
		if fixture["dt"] in pending:
			_export(fixture)


def _export(fixture):
	path = frappe.get_app_path(APP, "fixtures", frappe.scrub(fixture["dt"]) + ".json")
	os.makedirs(os.path.dirname(path), exist_ok=True)
	# Same ordering as Frappe's own export_fixtures, so both produce identical files.
	export_json(fixture["dt"], path, filters=fixture.get("filters"), order_by="idx asc, creation asc")


def _is_dev_session():
	flags = frappe.flags
	return bool(
		frappe.conf.developer_mode
		and not (
			flags.in_install
			or flags.in_migrate
			or flags.in_import
			or flags.in_fixtures
			or flags.in_patch
			or flags.in_setup_wizard
		)
	)


def _doctype_saved_from_desk():
	if not getattr(frappe.local, "request", None):
		return None

	form = frappe.form_dict
	cmd = form.get("cmd") or ""
	if cmd not in SAVE_CMDS and not cmd.endswith("run_doc_method"):
		return None

	payload = form.get("doc") or form.get("docs")
	if payload:
		payload = frappe.parse_json(payload)
		return payload.get("doctype") if isinstance(payload, dict) else None
	return form.get("dt")


def _deleted_path():
	return frappe.get_app_path(APP, "deleted_records.json")


def _load_deleted():
	path = _deleted_path()
	if not os.path.exists(path):
		return []
	with open(path) as f:
		return json.load(f)


def _save_deleted(deleted):
	with open(_deleted_path(), "w") as f:
		f.write(json.dumps(sorted(deleted, key=lambda d: (d["doctype"], d["name"])), indent=1) + "\n")


def _forget_deletion(doctype, name):
	# A record created again after being deleted must not be deleted on migrate.
	deleted = _load_deleted()
	entry = {"doctype": doctype, "name": name}
	if entry in deleted:
		deleted.remove(entry)
		_save_deleted(deleted)
