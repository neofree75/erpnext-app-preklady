import frappe


def after_install():
	"""Založ jazyk `sk`, ak ešte neexistuje.

	Bez záznamu v Language sa jazyk nedá vybrať v profile používateľa
	ani v System Settings, aj keby `.mo` bolo na mieste.
	"""
	if not frappe.db.exists("Language", "sk"):
		frappe.get_doc(
			{
				"doctype": "Language",
				"language_code": "sk",
				"language_name": "Slovak",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
