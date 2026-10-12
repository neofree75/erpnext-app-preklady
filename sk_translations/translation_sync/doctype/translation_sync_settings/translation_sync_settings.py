import json
import uuid

import frappe
from frappe import _
from frappe.model.document import Document


class TranslationSyncSettings(Document):
	def validate(self):
		if self.hub_url:
			self.hub_url = self.hub_url.rstrip("/")

			if not self.hub_url.startswith("https://") and "localhost" not in self.hub_url:
				frappe.throw(_("URL servera prekladov musí používať HTTPS"))

	def get_selected_apps(self) -> list[str] | None:
		"""Zoznam apiek z nastavení, alebo None = bez obmedzenia."""
		if not self.only_apps:
			return None

		return [a.strip() for a in self.only_apps.replace("\n", ",").split(",") if a.strip()]

	def get_installed_state(self) -> dict[str, str]:
		"""Mapa aplikácia → checksum posledného úspešne nasadeného balíčka."""
		try:
			return json.loads(self.installed_state or "{}")
		except ValueError:
			return {}

	def set_installed_state(self, state: dict[str, str]) -> None:
		self.db_set("installed_state", json.dumps(state, indent=1, sort_keys=True))

	def get_instance_id(self) -> str:
		"""Trvalé ID tejto inštalácie pre server prekladov.

		Viaže sa na názov site: klon databázy pod iným názvom (staging, kópia
		pre iného klienta) dostane nové ID a server ho posúdi ako novú inštanciu.
		"""
		if not self.instance_id or self.instance_site != frappe.local.site:
			self.db_set({"instance_id": uuid.uuid4().hex, "instance_site": frappe.local.site})

		return self.instance_id
