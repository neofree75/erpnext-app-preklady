"""Klientská strana: sťahovanie balíčkov z hubu a manuálny upload `.po`.

Beží u ZÁKAZNÍKA. Celé nasadenie prekladu je:

    stiahni .po  →  ulož  →  skompiluj .mo  →  frappe.translate.clear_cache()

Žiadny `bench` subprocess, žiadny `bench migrate`, žiadny reštart supervisora.
Používateľ uvidí zmenu po refreshi stránky.
"""

import base64
import hashlib

import frappe
from frappe import _
from frappe.utils import now_datetime

from sk_translations.translations import apply_po, normalize_locale, recompile_all, validate_app
from sk_translations.translation_sync.doctype.translation_sync_log.translation_sync_log import add_log

REQUEST_TIMEOUT = 60


def get_settings():
	return frappe.get_single("Translation Sync Settings")


@frappe.whitelist()
def sync_now():
	"""Ručné spustenie synchronizácie z UI. Vlastná práca ide na pozadie."""
	frappe.only_for("System Manager")

	frappe.enqueue(
		"sk_translations.sync.run_sync",
		queue="long",
		timeout=1500,
		job_name="sk_translations_sync",
	)

	return {"queued": True}


@frappe.whitelist()
def recompile_now():
	"""Prekompiluj `.mo` z uložených `.po` — záchrana po prestavbe kontajnera."""
	frappe.only_for("System Manager")

	results = recompile_all()

	for result in results:
		add_log(source="Prekompilovanie", status="Úspech", **_log_fields(result))

	return {"recompiled": len(results)}


def run_sync(force: bool = False) -> dict:
	"""Hlavná slučka: zisti čo je nové, stiahni a nasaď."""
	settings = get_settings()

	if not settings.enabled:
		return {"skipped": "vypnuté"}

	if not (settings.hub_url and settings.get_password("token", raise_exception=False)):
		return {"skipped": "chýba URL alebo licenčný kľúč"}

	locale = normalize_locale(settings.locale or "sk")
	state = {} if force else settings.get_installed_state()

	try:
		updates = _call_hub(settings, "check_updates", {"installed": state, "locale": locale})["updates"]
	except Exception as e:
		settings.db_set({"last_sync": now_datetime(), "last_status": f"Chyba: {e}"})
		add_log(source="Hub", status="Chyba", locale=locale, error=frappe.get_traceback())
		raise

	installed_apps = set(frappe.get_installed_apps())
	selected = settings.get_selected_apps()
	applied, skipped, failed = 0, 0, 0

	for update in updates:
		app = update["app"]

		# Preklad apky, ktorú zákazník nemá, nemá kam ísť.
		if app not in installed_apps or (selected and app not in selected):
			skipped += 1
			continue

		try:
			package = _call_hub(settings, "download", {"app": app, "locale": locale})
			result = _apply_package(package, locale)
			state[app] = package["checksum"]
			add_log(source="Hub", status="Úspech", version=package.get("version"),
				checksum=package["checksum"], **_log_fields(result))
			applied += 1
		except Exception:
			failed += 1
			add_log(source="Hub", status="Chyba", app=app, locale=locale, error=frappe.get_traceback())
			frappe.log_error(title=f"sk_translations: sync {app} zlyhal")

	settings.set_installed_state(state)
	settings.db_set(
		{
			"last_sync": now_datetime(),
			"last_status": _("Nasadené: {0}, preskočené: {1}, chyby: {2}").format(
				applied, skipped, failed
			),
		}
	)

	return {"applied": applied, "skipped": skipped, "failed": failed}


def _call_hub(settings, method: str, payload: dict) -> dict:
	"""Zavolaj endpoint hubu. Token ide v tele, nie v URL — nekončí v logoch."""
	import requests

	url = f"{settings.hub_url}/api/method/sk_translations_hub.api.{method}"
	body = {"token": settings.get_password("token"), "site": frappe.local.site, **payload}

	response = requests.post(url, json=body, timeout=REQUEST_TIMEOUT)
	response.raise_for_status()

	return response.json()["message"]


def _apply_package(package: dict, locale: str) -> dict:
	"""Over integritu a kompatibilitu balíčka, potom ho nasaď."""
	po_bytes = base64.b64decode(package["content"])

	if hashlib.sha256(po_bytes).hexdigest() != package["checksum"]:
		frappe.throw(_("Checksum stiahnutého balíčka nesedí — prenos je poškodený"))

	_warn_on_version_mismatch(package)

	return apply_po(package["app"], locale, po_bytes)


def _warn_on_version_mismatch(package: dict) -> None:
	"""Nesúlad verzií nie je fatálny — chýbajúce reťazce padnú na angličtinu.

	Ale zamlčať sa nesmie: `.po` je viazané na POT z konkrétnej verzie apky.
	"""
	installed = _get_app_version(package["app"])

	if not installed:
		return

	minimum, maximum = package.get("min_app_version"), package.get("max_app_version")

	if (minimum and installed < minimum) or (maximum and installed > maximum):
		frappe.log_error(
			title="sk_translations: nesúlad verzií",
			message=(
				f"App {package['app']} má verziu {installed}, balíček je pre "
				f"{minimum or '*'}–{maximum or '*'}. Preklad sa nasadí, ale nemusí byť úplný."
			),
		)


def _get_app_version(app: str) -> str | None:
	try:
		return frappe.get_attr(f"{app}.__version__")
	except Exception:
		return None


def _log_fields(result: dict) -> dict:
	return {
		"app": result["app"],
		"locale": result["locale"],
		"message_count": result["messages"],
		"mo_path": result["mo_path"],
	}


@frappe.whitelist()
def upload_po(file_url: str, app: str, locale: str = "sk"):
	"""Manuálne nasadenie `.po` z prílohy — záložná cesta, keď hub nie je dostupný."""
	frappe.only_for("System Manager")

	app = validate_app(app)
	locale = normalize_locale(locale)

	name = frappe.db.get_value("File", {"file_url": file_url}, "name")

	if not name:
		frappe.throw(_("Súbor sa nenašiel: {0}").format(file_url))

	content = frappe.get_doc("File", name).get_content(encodings=[])
	po_bytes = content if isinstance(content, bytes) else content.encode("utf-8")

	result = apply_po(app, locale, po_bytes)
	add_log(
		source="Manuálny upload",
		status="Úspech",
		checksum=hashlib.sha256(po_bytes).hexdigest(),
		**_log_fields(result),
	)

	return result


def daily():
	_scheduled("Denne")


def weekly():
	_scheduled("Týždenne")


def _scheduled(frequency: str) -> None:
	settings = get_settings()

	if settings.enabled and settings.auto_sync and settings.sync_frequency == frequency:
		run_sync()
