---
title: "SK Translations — návod na inštaláciu"
subtitle: "Slovenské preklady pre Frappe / ERPNext v16"
author: "Code Way, s.r.o. · codeway.sk · info@codeway.sk"
lang: sk
---

# Čo je SK Translations

**SK Translations** je aplikácia pre Frappe Framework / ERPNext v16, ktorá do
vášho systému automaticky dopĺňa slovenské (prípadne ďalšie jazykové) preklady.

Preklady sa sťahujú z distribučného servera Code Way v nastavenom intervale,
skompilujú sa priamo na vašom serveri a prejavia sa hneď po obnovení stránky
(F5). **Netreba kopírovať žiadne súbory, spúšťať migráciu ani reštartovať
systém.**

# Čo potrebujete pred začiatkom

| Položka | Poznámka |
|---|---|
| Frappe Framework / ERPNext **v16** | Staršie verzie nie sú podporované. |
| Python **3.14+** | Súčasť prostredia Frappe bench. |
| Prístup servera na internet | Odchádzajúce HTTPS na server prekladov. |
| Rola **System Manager** | Potrebná na inštaláciu a nastavenie v ERPNexte. |
| Prístup k príkazovému riadku servera (bench) | Krok 1 robí správca servera alebo váš hosting. |
| **URL servera prekladov** a **licenčný kľúč** | Poskytne Code Way, s.r.o. — napíšte na info@codeway.sk |

> **Poznámka:** Ak vám ERPNext prevádzkuje externý dodávateľ alebo hosting,
> krok 1 (inštalácia) preň pošlite tak, ako je uvedený nižšie. Kroky 2 až 4 už
> zvládnete sami cez webové rozhranie.

# Krok 1 — Inštalácia aplikácie

Na serveri, v adresári vášho benchu, spustite:

```
bench get-app sk_translations https://github.com/neofree75/erpnext-app-preklady.git
bench --site <vasa-site> install-app sk_translations
```

`<vasa-site>` nahraďte názvom vašej site (napríklad `firma.erp.sk`).

Po inštalácii sa v ľavom paneli workspace **Integrácia** (Integrations) objaví
nová sekcia **Preklady** s dvoma položkami:

- **Translation Sync Settings** — nastavenie a ručné spustenie synchronizácie
- **Translation Sync Log** — história nasadených jazykových balíčkov

Ak sekciu nevidíte, obnovte stránku klávesom **F5**.

![Sekcia Preklady v bočnom paneli workspace Integrácia](images/sidebar-preklady.png){ width=35% }

# Krok 2 — Nastavenie

Otvorte **Translation Sync Settings** a vyplňte:

| Pole | Čo doň zadať |
|---|---|
| **Zapnuté** | Zaškrtnite — hlavný vypínač aplikácie. |
| **URL servera prekladov** | Adresa, ktorú vám poskytla Code Way, s.r.o. |
| **Licenčný kľúč** | Kľúč, ktorý vám poskytla Code Way, s.r.o. |
| **Jazyk** | Jazyk prekladov, predvolene **Slovenčina** (`sk`). |
| **Automatická synchronizácia** | Zaškrtnite, ak chcete pravidelné sťahovanie na pozadí. |
| **Frekvencia** | *Denne* alebo *Týždenne*. Pre bežnú prevádzku stačí **Denne**. |
| **Iba tieto aplikácie** | Voliteľné. Názvy aplikácií oddelené čiarkou (napr. `erpnext`). Prázdne pole = všetko, na čo máte predplatné a čo je nainštalované. |

![Obrazovka Translation Sync Settings](images/translation-sync-settings.png){ width=100% }

Nastavenie **uložte** tlačidlom *Uložiť* vpravo hore.

# Krok 3 — Prvé spustenie

Kliknite na tlačidlo **Synchronizovať teraz** vpravo hore.

Synchronizácia beží na pozadí, obvykle trvá niekoľko sekúnd až desiatok sekúnd.
Po jej dokončení sa v spodnej sekcii **Stav** doplní:

- **Posledná synchronizácia** — dátum a čas posledného behu
- **Posledný výsledok** — napríklad `Nasadené: 1, preskočené: 0, chyby: 0`
- **Nasadené balíčky** — mapa *aplikácia → checksum*; slúži na to, aby sa
  nezmenené balíčky pri ďalších behoch zbytočne nesťahovali

Potom **obnovte stránku (F5)** — preklady sú nasadené. Ďalej už všetko beží
samo podľa nastavenej frekvencie.

Druhé tlačidlo, **Prekompilovať uložené .po**, znovu zostaví prekladové súbory
z už stiahnutých dát bez volania servera. Bežne ho nepotrebujete; použite ho
len na odporúčanie podpory.

# Krok 4 — Overenie, že to funguje

Otvorte **Translation Sync Log**. Nájdete tu jeden záznam na každý nasadený
jazykový balíček. V zázname vidíte:

| Pole | Význam |
|---|---|
| **Aplikácia** | Ktorej aplikácie sa balíček týka (napr. `erpnext`). |
| **Jazyk** | Jazyk prekladu (napr. `sk`). |
| **Zdroj** | Odkiaľ balíček prišiel — *Hub* znamená server prekladov. |
| **Verzia**, **Checksum** | Presná identifikácia balíčka. |
| **Počet reťazcov** | Množstvo preložených textov v balíčku. |
| **Cesta k .mo** | Skompilovaný súbor, ktorý Frappe reálne používa. |
| **Stav** | *Úspech*, *Preskočené* alebo *Chyba*. |

![Detail záznamu v Translation Sync Log](images/translation-sync-log.png){ width=100% }

Ak je stav **Úspech**, balíček je nasadený a preklady sú aktívne.

# Riešenie problémov

**Preklady sa nezmenili.**
Obnovte stránku klávesom **F5** — prehliadač má načítané staré texty. Ak to
nepomôže, skontrolujte posledný záznam v *Translation Sync Log*.

**Stav „Preskočené".**
Balíček je pre aplikáciu, ktorá na vašej inštancii nie je nainštalovaná, alebo
je už nasadená rovnaká verzia. Toto je v poriadku, nejde o chybu.

**Stav „Chyba".**
Najčastejšou príčinou je nesprávny licenčný kľúč alebo URL servera, prípadne
server nemá prístup na internet. Presný popis chyby je priamo v zázname.

**Časť textov zostala po anglicky.**
Jazykový balíček je pre inú verziu aplikácie, než akú máte nainštalovanú.
Nepreložené texty zostávajú v angličtine — kontaktujte nás a doplníme aktuálny
balíček.

**Po inštalácii sa neobjavila sekcia Preklady.**
Obnovte stránku (F5). Ak sa neobjaví ani potom, napíšte nám na
info@codeway.sk.

# Ochrana osobných údajov

Aplikácia posiela na server prekladov iba to, čo je nutné na výber správneho
jazykového balíčka:

- licenčný kľúč,
- názov vašej site,
- požadovaný jazyk,
- názvy aplikácií a kontrolné súčty už nasadených balíčkov prekladov.

**Žiadne obchodné ani osobné údaje z vášho ERPNextu sa neodosielajú.** Licenčný
kľúč sa prenáša v tele požiadavky (nie v URL), aby nekončil v logoch.

# Podpora

Aplikáciu vyvinula a udržiava **Code Way, s.r.o.**

- Web: codeway.sk
- E-mail: info@codeway.sk

Pri hlásení problému priložte prosím príslušný záznam z **Translation Sync
Log** a verziu vášho Frappe / ERPNextu.

*Licencia MIT. © 2026 Code Way, s.r.o.*
