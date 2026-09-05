# Vývojárske poznámky

Interná dokumentácia k aplikácii **sk_translations**. Zákaznícka dokumentácia je
v [README.md](README.md).

Vyvíja **Code Way, s.r.o.** — [codeway.sk](https://codeway.sk) ·
[info@codeway.sk](mailto:info@codeway.sk)

## Architektúra

Táto apka je klientská polovica. Protistranou je samostatná apka
**sk_translations_hub**, ktorá beží na distribučnom serveri a vydáva jazykové
balíčky. Klient sa k nej hlási licenčným kľúčom.

```
hub  ──token──▶  stiahne .po
                 uloží do private files
                 skompiluje .mo
                 frappe.translate.clear_cache()
```

Vstupné body:

| Modul | Obsah |
|---|---|
| `sync.py` | komunikácia s hubom, `sync_now()`, `recompile_now()`, `upload_po()`, plánované úlohy |
| `translations.py` | `apply_po()`, `recompile_all()`, `validate_app()`, `normalize_locale()` |
| `desk.py` | `ensure_sidebar_items()` — položky vo workspace sidebare *Integrations* |
| `install.py` | `after_install()` |

## Prečo netreba `bench`

Overené v zdrojákoch Frappe v16:

| Predpoklad | Realita |
|---|---|
| `.mo` sa musí zapísať do `apps/` | `get_mo_path()` → `sites/assets/locale/<locale>/LC_MESSAGES/<app>.mo`. `apps/` sa nedotýkame, takže read-only image v Dockeri nevadí. |
| treba spustiť `bench compile-po-to-mo` | ten príkaz je len wrapper nad `read_po()` + `write_mo()`; voláme ich priamo v procese |
| treba `bench migrate` | migrate s prekladmi nesúvisí |
| treba reštart supervisora | zlúčené preklady sú v Redise (`frappe.cache.hget(MERGED_TRANSLATION_KEY, lang)`), nie v pamäti workera — `frappe.translate.clear_cache()` stačí |

Používateľ uvidí nový preklad po refreshi stránky (F5).

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
- **`ensure_sidebar_items()` beží aj v `after_migrate`**, lebo Frappe pri migrate
  reimportuje štandardný `Workspace Sidebar` a naše položky zmiznú.

## Ručné nasadenie `.po`

Bez pripojenia na hub sa dá balíček nasadiť z prílohy (rola System Manager):

```python
# bench --site <site> console
from sk_translations.sync import upload_po

upload_po(file_url="/private/files/frappe-sk.po", app="frappe", locale="sk")
```

## DocTypy sa po inštalácii nevytvorili

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

## Stav

Doplniť treba: testy, workspace/onboarding, čistenie starých logov
(Log Settings), tlačidlo na manuálny upload v UI.
