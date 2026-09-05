import frappe

SIDEBAR = "Integrations"
SECTION_LABEL = "Preklady"
ITEMS = (
	("Translation Sync Settings", "Translation Sync Settings", "settings"),
	("Translation Sync Log", "Translation Sync Log", "history"),
)


def ensure_sidebar_items():
	"""Doplň sekciu Preklady do ľavého sidebaru workspace Integrations.

	Frappe pri `bench migrate` reimportuje štandardný Workspace Sidebar zo
	svojho `workspace_sidebar/integrations.json`, takže naše položky zmiznú
	a treba ich doplniť znova. Voláme z `after_migrate` aj `after_install`.
	"""
	if not frappe.db.exists("Workspace Sidebar", SIDEBAR):
		return

	sidebar = frappe.get_doc("Workspace Sidebar", SIDEBAR)
	existing = {item.link_to for item in sidebar.items if item.type == "Link"}
	missing = [item for item in ITEMS if item[1] not in existing]
	if not missing:
		return

	has_section = any(
		item.type == "Section Break" and item.label == SECTION_LABEL for item in sidebar.items
	)
	if not has_section:
		sidebar.append(
			"items",
			{
				"type": "Section Break",
				"label": SECTION_LABEL,
				"icon": "languages",
				"indent": 1,
				"collapsible": 1,
			},
		)

	for label, link_to, icon in missing:
		sidebar.append(
			"items",
			{
				"type": "Link",
				"link_type": "DocType",
				"link_to": link_to,
				"label": label,
				"icon": icon,
				"child": 1,
				"collapsible": 1,
			},
		)

	# `WorkspaceSidebar.before_save` exportuje štandardný sidebar späť do
	# priečinka vlastniacej aplikácie, keď je zapnutý developer_mode — týmto
	# flagom zabránime prepísaniu integrations.json v repozitári frappe.
	in_import = frappe.flags.in_import
	frappe.flags.in_import = True
	try:
		sidebar.save(ignore_permissions=True)
	finally:
		frappe.flags.in_import = in_import

	frappe.db.commit()
