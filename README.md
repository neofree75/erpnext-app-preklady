# SK Translations (klient)

Nasadzuje preklady (`.po`) na Frappe / ERPNext v16 bez kopírovania súborov
cez FTP a bez spúšťania `bench`.

Protistrana je samostatná apka **[sk_translations_hub](../erpnext-app-preklady-hub)**,
ktorá beží na distribučnom serveri. Táto apka sa k nemu hlási licenčným kľúčom.

## Ako to funguje

```
hub  ──token──▶  stiahne .po
                 uloží do private files
                 skompiluje .mo
                 frappe.translate.clear_cache()
```

## Prečo netreba `bench`

Overené v zdrojákoch Frappe v16:

| Predpoklad | Realita |
|---|---|
| `.mo` sa musí zapísať do `apps/` | `get_mo_path()` → `sites/assets/locale/<locale>/LC_MESSAGES/<app>.mo`. `apps/` sa nedotýkame, takže read-only image v Dockeri nevadí. |
| treba spustiť `bench compile-po-to-mo` | ten príkaz je len wrapper nad `read_po()` + `write_mo()`; voláme ich priamo v procese |
| treba `bench migrate` | migrate s prekladmi nesúvisí |
| treba reštart supervisora | zlúčené preklady sú v Redise (`frappe.cache.hget(MERGED_TRANSLATION_KEY, lang)`), nie v pamäti workera — `frappe.translate.clear_cache()` stačí |

Používateľ uvidí nový preklad po refreshi stránky (F5).

## Inštalácia

```bash
bench get-app sk_translations <repo-url>
bench --site <site> install-app sk_translations
```

Potom **Translation Sync Settings** → URL hubu + licenčný kľúč. Tlačidlo
*Synchronizovať teraz* spustí sync na pozadí, výsledok je v **Translation Sync Log**.
Ďalej to beží samo podľa nastavenej frekvencie.

Bez pripojenia na hub sa dá `.po` nasadiť ručne cez
`sk_translations.sync.upload_po(file_url, app, locale)`.

## Ak sa DocTypy po inštalácii nevytvoria

`bench get-app` na záver reštartuje supervisor cez `sudo`. Ak to zlyhá (user
`frappe` nemá `sudo supervisorctl`), zostane v Redise stará hodnota kľúča
`app_modules` — bez apky. `install-app` potom v `sync_for()` nenájde žiadny
modul a **ticho preskočí import DocTypov**: v logu chýba riadok
`Updating DocTypes for sk_translations`.

Náprava:

```python
# bench --site <site> console
import frappe
from frappe.model.sync import sync_for

frappe.cache.delete_value("app_modules")
frappe.client_cache.delete_value("installed_app_modules")
frappe.setup_module_map()

sync_for("sk_translations", force=1, reset_permissions=True)
frappe.db.commit()
```

Potom ako root reštartovať workery, aby videli novú apku:

```bash
supervisorctl restart frappe-bench-web: frappe-bench-workers:
```

## Na čo si dať pozor

- **Kód jazyka rozhoduje o ceste k `.mo`.** `gettext.find()` hľadá adresár
  presne podľa kódu jazyka. Rozhoduje pole `language` v balíčku — hlavička
  `Language:` v `.po` je len metadáta a ignoruje sa. Používame `sk`.
- **`.po` je viazané na verziu apky.** Balíček nesie rozsah
  `min_app_version`–`max_app_version`; nesúlad sa zaloguje, ale nasadenie
  nezablokuje (chýbajúce reťazce padnú na angličtinu).
- **Preklad apky, ktorá nie je nainštalovaná, sa preskočí** — `validate_app()`
  to zároveň chráni pred path traversal cez názov apky.
- **`after_migrate` prekompiluje `.mo`** z uložených `.po`. Bez toho by preklady
  ticho vypadli po prestavbe kontajnera, keď sa `sites/assets/` vyprázdni.

## Stav

Kostra. Doplniť treba: testy, workspace/onboarding, čistenie starých logov
(Log Settings), tlačidlo na manuálny upload v UI.
