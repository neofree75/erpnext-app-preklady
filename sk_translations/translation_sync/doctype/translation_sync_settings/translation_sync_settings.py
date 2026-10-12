import json
import uuid
from contextlib import contextmanager

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
		if self.instance_id and self.instance_site == frappe.local.site:
			return self.instance_id

		# Pri prvom syncu môžu ID generovať dva procesy naraz (scheduler a ručný
		# sync, v Dockeri aj z rôznych kontajnerov). Bez zámku by server jedno
		# zaregistroval a druhé odmietol — a v DB by mohlo ostať práve odmietnuté.
		with _db_lock(f"sk_translations_instance_id:{frappe.local.site}"):
			# Zamykajúce čítanie — obyčajné by v REPEATABLE READ mohlo vrátiť
			# snapshot spred commitu druhého procesu.
			singles = frappe.qb.DocType("Singles")
			stored = dict(
				frappe.qb.from_(singles)
				.select(singles.field, singles.value)
				.where((singles.doctype == self.doctype) & singles.field.isin(["instance_id", "instance_site"]))
				.for_update()
				.run()
			)
			instance_id, instance_site = stored.get("instance_id"), stored.get("instance_site")

			if not instance_id or instance_site != frappe.local.site:
				instance_id = uuid.uuid4().hex
				frappe.db.set_single_value(
					self.doctype, {"instance_id": instance_id, "instance_site": frappe.local.site}
				)
				# Commit ešte pod zámkom, aby druhý proces po jeho uvoľnení videl nové ID.
				frappe.db.commit()

		self.instance_id, self.instance_site = instance_id, frappe.local.site

		return self.instance_id


@contextmanager
def _db_lock(name: str, timeout: int = 30):
	"""Pomenovaný zámok v databáze — platí naprieč procesmi aj kontajnermi."""
	if frappe.db.db_type == "postgres":
		frappe.db.sql("select pg_advisory_lock(hashtext(%s))", name)
	elif not frappe.db.sql("select get_lock(%s, %s)", (name, timeout))[0][0]:
		frappe.throw(_("Nepodarilo sa získať zámok {0}").format(name))

	try:
		yield
	finally:
		if frappe.db.db_type == "postgres":
			frappe.db.sql("select pg_advisory_unlock(hashtext(%s))", name)
		else:
			frappe.db.sql("select release_lock(%s)", name)
