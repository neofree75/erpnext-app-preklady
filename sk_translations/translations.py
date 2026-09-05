"""Jadro apky: bezpečné uloženie a kompilácia `.po` súborov.

Kľúčové fakty overené vo frappe v16 (`frappe/gettext/translate.py`,
`frappe/translate.py`):

* `.mo` sa NEzapisuje do `apps/`, ale do
  `sites/assets/locale/<locale>/LC_MESSAGES/<app>.mo` (`get_mo_path()`).
  Ten adresár je writable aj v Dockeri, `apps/` byť nemusí.
* `bench compile-po-to-mo` je len wrapper nad `read_po()` + `write_mo()`,
  takže sa dá spraviť priamo v procese — žiadny subprocess.
* Zlúčené preklady žijú v Redise pod `MERGED_TRANSLATION_KEY`
  (`frappe.cache.hget`), nie v pamäti workera. `frappe.translate.clear_cache()`
  preto stačí — reštart bench/supervisor NIE je potrebný.
* `bench migrate` ani `bench build` s prekladmi nesúvisia.
"""

import io
import re
import shutil
from pathlib import Path

import frappe
from babel.messages.pofile import read_po
from frappe import _

#: `gettext.find()` hľadá adresár presne podľa kódu jazyka (pomlčky na
#: podčiarkovníky). Hlavička `Language:` v `.po` je iba metadáta a NErozhoduje.
LOCALE_PATTERN = re.compile(r"^[a-z]{2,3}(_[A-Za-z]{2,4})?$")

STORE_DIRNAME = "sk_translations"


def normalize_locale(locale: str) -> str:
	"""Znormalizuj kód jazyka na tvar, aký očakáva `gettext.find()`.

	Frappe používa pomlčky (`pt-BR`), babel/gettext podčiarkovníky (`pt_BR`).
	`get_translations_from_mo()` robí ten istý `replace`, takže adresár musí
	byť v podčiarkovníkovom tvare.
	"""
	locale = (locale or "").strip().replace("-", "_")

	if not LOCALE_PATTERN.match(locale):
		frappe.throw(_("Neplatný kód jazyka: {0}").format(locale))

	return locale


def validate_app(app: str) -> str:
	"""Povoľ len nainštalované apky.

	Chráni aj pred path traversal — názov apky ide do cesty k `.mo` súboru.
	"""
	app = (app or "").strip()

	if app not in frappe.get_installed_apps():
		frappe.throw(_("Aplikácia {0} nie je na tomto site nainštalovaná").format(app))

	return app


def parse_catalog(po_bytes: bytes):
	"""Rozparsuj `.po` obsah. Poškodený súbor zahoď skôr, než sa čohokoľvek dotkne."""
	try:
		return read_po(io.BytesIO(po_bytes))
	except Exception as e:
		frappe.throw(_("Súbor .po sa nepodarilo rozparsovať: {0}").format(e))


def get_store_dir(app: str) -> Path:
	"""Trvalé úložisko `.po` v private files site-u.

	`sites/assets/locale/` môže prestavba image alebo `bench build` vymazať,
	private files sú perzistentný volume. Odtiaľ vieme `.mo` kedykoľvek
	prekompilovať (viď `recompile_all()` na `after_migrate`).
	"""
	path = Path(frappe.get_site_path("private", "files", STORE_DIRNAME, app))
	path.mkdir(parents=True, exist_ok=True)
	return path


def get_store_path(app: str, locale: str) -> Path:
	return get_store_dir(app) / f"{locale}.po"


def apply_po(app: str, locale: str, po_bytes: bytes) -> dict:
	"""Ulož `.po`, skompiluj `.mo` a zneplatni cache prekladov.

	Vracia dict so štatistikou pre log. Beží v background jobe — erpnext/sk.po
	má ~2.7 MB a ~20k reťazcov, čo je na request cyklus priveľa.
	"""
	from frappe.gettext.translate import write_binary

	app = validate_app(app)
	locale = normalize_locale(locale)

	catalog = parse_catalog(po_bytes)

	store_path = get_store_path(app, locale)
	store_path.write_bytes(po_bytes)

	mo_path = write_binary(app, catalog, locale)

	frappe.translate.clear_cache()

	return {
		"app": app,
		"locale": locale,
		"po_path": str(store_path),
		"mo_path": str(mo_path),
		"messages": len(catalog),
	}


def recompile_all() -> list[dict]:
	"""Prekompiluj všetky uložené `.po`.

	Zavesené na `after_migrate` — po update apky alebo prestavbe kontajnera
	môže `sites/assets/locale/` zmiznúť a preklady by ticho vypadli.
	"""
	root = Path(frappe.get_site_path("private", "files", STORE_DIRNAME))
	results = []

	if not root.exists():
		return results

	installed = set(frappe.get_installed_apps())

	for app_dir in sorted(root.iterdir()):
		if not app_dir.is_dir() or app_dir.name not in installed:
			continue

		for po_file in sorted(app_dir.glob("*.po")):
			try:
				results.append(apply_po(app_dir.name, po_file.stem, po_file.read_bytes()))
			except Exception:
				frappe.log_error(
					title="sk_translations: prekompilovanie zlyhalo",
					message=f"{app_dir.name}/{po_file.name}\n\n{frappe.get_traceback()}",
				)

	return results


def remove_po(app: str, locale: str) -> None:
	"""Odstráň preklad — uložené `.po` aj skompilované `.mo`."""
	from frappe.gettext.translate import get_mo_path

	app = validate_app(app)
	locale = normalize_locale(locale)

	get_store_path(app, locale).unlink(missing_ok=True)
	Path(get_mo_path(app, locale)).unlink(missing_ok=True)

	frappe.translate.clear_cache()
