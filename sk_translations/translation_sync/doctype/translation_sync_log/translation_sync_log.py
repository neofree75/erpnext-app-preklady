import frappe
from frappe.model.document import Document


class TranslationSyncLog(Document):
	pass


def add_log(**kwargs) -> None:
	"""Zapíš záznam do logu. Zlyhanie logovania nesmie zhodiť samotnú synchronizáciu."""
	try:
		frappe.get_doc({"doctype": "Translation Sync Log", **kwargs}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="sk_translations: log sa nepodarilo zapísať")
