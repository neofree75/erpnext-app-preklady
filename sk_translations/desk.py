import frappe

SIDEBAR = "Integrations"
SECTION_LABEL = "Preklady"
ITEMS = (
	("Translation Sync Settings", "Translation Sync Settings", "settings"),
	("Translation Sync Log", "Translation Sync Log", "history"),
)

# Tlačidlo na raile ERPNext; definuje ho `dock/sk_translations/sk_translations.json`.
RAIL_HOST = "erpnext"
RAIL_ENTRY = {"link_type": "Sidebar", "link_to": "Translation Sync", "hidden": 0}


def has_dock():
	"""Frappe 16 s doctypom Dock kreslí rail z `Dock` a vlastného `Sidebar` modulu."""
	return bool(frappe.db.exists("DocType", "Dock"))


def ensure_rail_entry():
	"""Zobraz tlačidlo Preklady na raile ERPNext aj na site, ktorý má rail uložený (Manage Dock).

	Bez uloženého usporiadania sa tlačidlo zobrazí samo z nášho `Dock` (`mount_on: erpnext`).
	Uložené usporiadanie však Frappe o nové tlačidlá appky nedopĺňa, len ich ponúkne na pridanie.
	Voláme preto len z `after_install` a z patchu, nie z `after_migrate`, aby sme neprepisovali
	neskoršie presunutie alebo skrytie tlačidla na site.
	"""
	try:
		from frappe.desk.doctype.dock.dock import get_dock, save_site_dock, stored_row
	except ImportError:
		return  # staršia verzia Frappe bez Dock

	try:
		site = get_dock(RAIL_HOST, None, 0)
		if not site:
			return
		rows = [stored_row(row) for row in site.items]
		if any(row.get("link_to") == RAIL_ENTRY["link_to"] for row in rows):
			return
		save_site_dock(RAIL_HOST, [*rows, dict(RAIL_ENTRY)])
	except Exception:
		frappe.log_error(title="Pridanie tlačidla Preklady na rail ERPNext")


def ensure_sidebar_items():
	"""Doplň sekciu Preklady do ľavého sidebaru workspace Integrations.

	Len pre Frappe bez doctypu Dock — novšie verzie `Workspace Sidebar` v menu nezobrazujú
	a appka má vlastný `Sidebar` a tlačidlo na raile.

	Frappe pri `bench migrate` reimportuje štandardný Workspace Sidebar zo
	svojho `workspace_sidebar/integrations.json`, takže naše položky zmiznú
	a treba ich doplniť znova. Voláme z `after_migrate` aj `after_install`.
	"""
	if has_dock() or not frappe.db.exists("Workspace Sidebar", SIDEBAR):
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
