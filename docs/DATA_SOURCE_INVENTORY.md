# Authoritative Data Source Inventory — CricketIQ

**Version:** 1.0.0  
**Effective Date:** 2026-11-16  
**Status:** Approved for Pre-Phase 4 Corpus Engineering  
**Authority Reference:** ICC Regulations Portal & Marylebone Cricket Club (MCC)  

---

## 1. Overview & Inventory Taxonomy

This inventory catalogs all official cricket regulatory documents evaluated for CricketIQ. It enforces strict separation between:
- **Tier 1 (Core Authoritative Corpus):** MCC Laws of Cricket and standard ICC Men's & Women's Playing Conditions (current October 2026 edition and key predecessor editions).
- **Tier 2 (Competition Overlays):** Event-specific playing conditions (e.g. World Test Championship, T20 World Cup) that modify standard playing conditions.
- **Tier 3 (Explicitly Out of MVP Scope):** Domestic leagues (IPL, BBL, PSL, Hundred, Ranji Trophy), recreational/school cricket, and non-ICC tournaments.

---

## 2. Master Document Register

| Document ID | Authority | Title | Edition | Format | Category | Effective Date | Applicability Basis | Source Landing URL | Official PDF URL | Status | Parent Doc ID |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`ICC_TEST_MEN_2026`** | ICC | Men's Test Match Playing Conditions | Oct 2026 | Test | Men's | 2026-10-01 | `SERIES_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/a8114zro5tkioifz0jqg.pdf` | `discovered` | `None` |
| **`ICC_ODI_MEN_2026`** | ICC | Men's One Day International Playing Conditions | Oct 2026 | ODI | Men's | 2026-10-01 | `SERIES_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/bxkzkcyvfn6tvi70zh0w.pdf` | `discovered` | `None` |
| **`ICC_T20I_MEN_2026`** | ICC | Men's Twenty20 International Playing Conditions | Oct 2026 | T20I | Men's | 2026-10-01 | `SERIES_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/bsxcho7ufe2pjban0wjp.pdf` | `candidate` | `None` |
| **`ICC_T20I_MEN_ADD_2026`** | ICC | Addendum to Men's T20I Playing Conditions | Oct 2026 | T20I | Men's | 2026-10-01 | `SERIES_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/pzyejpstlhptewq9qs2n.pdf` | `discovered` | `ICC_T20I_MEN_2026` |
| **`ICC_FOUR_DAY_MEN_2026`**| ICC | Men's Four-Day Test Match Playing Conditions | Oct 2026 | Test | Men's | 2026-10-01 | `SERIES_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/j9wexmqm2dgcyirvepbl.pdf` | `discovered` | `None` |
| **`ICC_TEST_WOMEN_2026`** | ICC | Women's Test Match Playing Conditions | Oct 2026 | Test | Women's | 2026-10-01 | `SERIES_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/hbwwi78pugzpdwft0v4v.pdf` | `discovered` | `None` |
| **`ICC_ODI_WOMEN_2026`** | ICC | Women's One Day International Playing Conditions | Oct 2026 | ODI | Women's | 2026-10-01 | `SERIES_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/qunpw1kfh3ibxlz58jlw.pdf` | `discovered` | `None` |
| **`ICC_T20I_WOMEN_2026`** | ICC | Women's Twenty20 International Playing Conditions | Oct 2026 | T20I | Women's | 2026-10-01 | `SERIES_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/o3vhm0zw7pppoxpgopke.pdf` | `discovered` | `None` |
| **`ICC_T20I_WOMEN_ADD_2026`**| ICC | Addendum to Women's T20I Playing Conditions | Oct 2026 | T20I | Women's | 2026-10-01 | `SERIES_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/pzyejpstlhptewq9qs2n.pdf` | `discovered` | `ICC_T20I_WOMEN_2026` |
| **`MCC_LAWS_2026`** | MCC | Laws of Cricket (2017 Code 4th Edition - 2026) | 4th Ed (2026) | All | Open | 2026-10-01 | `SERIES_START_DATE` | [MCC Laws Directory](https://www.lords.org/mcc/about-the-laws-of-cricket) | `https://www.lords.org/getmedia/a4ef9f77-2a25-4f5b-a286-4601f08e6334/Laws-of-Cricket-2017-Code-4th-Edition.pdf` | `discovered` | `None` |
| **`MCC_LAWS_2022`** | MCC | Laws of Cricket (2017 Code 3rd Edition - 2022) | 3rd Ed (2022) | All | Open | 2022-10-01 | `MATCH_DATE` | [MCC Laws Directory](https://www.lords.org/mcc/about-the-laws-of-cricket) | `https://www.lords.org/mcc/about-the-laws-of-cricket/historical-laws` | `discovered` | `None` |
| **`ICC_WTC_2025_2027_PC`** | ICC | ICC World Test Championship 2025–2027 Playing Conditions | 2025–2027 | Test | Men's | 2026-10-01 | `COMPETITION_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/jrwhpcwk8mmpv0fx3lnd.pdf` | `discovered` | `ICC_TEST_MEN_2026` |
| **`ICC_WTC_2025_2027_REGS`**| ICC | ICC World Test Championship 2025–2027 Tournament Regulations | 2025–2027 | Test | Men's | 2025-06-01 | `COMPETITION_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/doztximb3sxhwcc4oo3f.pdf` | `discovered` | `None` |
| **`ICC_T20WC_MEN_2026`** | ICC | ICC Men's T20 World Cup 2026 Playing Conditions | 2026 | T20I | Men's | 2026-02-01 | `COMPETITION_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/yyt7m8uh9c1uehrbvuwb.pdf` | `discovered` | `ICC_T20I_MEN_2026` |
| **`ICC_WTC_2023_2025_HIST`**| ICC | ICC World Test Championship 2023–2025 Playing Conditions | 2023–2025 | Test | Men's | 2023-06-01 | `COMPETITION_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/xdemi21znqlhfddojbbf.pdf` | `discovered` | `None` |
| **`ICC_T20WC_MEN_2024_HIST`**| ICC | ICC Men's T20 World Cup 2024 Playing Conditions | 2024 | T20I | Men's | 2024-06-01 | `COMPETITION_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/euhohq8vpgzi0urumg3y.pdf` | `discovered` | `None` |
| **`ICC_T20WC_WOMEN_2024_HIST`**| ICC | ICC Women's T20 World Cup 2024 Playing Conditions | 2024 | T20I | Women's | 2024-10-01 | `COMPETITION_START_DATE` | [ICC PC Directory](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) | `https://images.icc-cricket.com/image/upload/prd/hn1rzsw3frn6wuw9dlly.pdf` | `discovered` | `None` |

---

## 3. Tier 3: Explicitly Out of MVP Scope

The following competitions have been evaluated and classified as `out_of_scope` for the current MVP release. No source files will be ingested into the active authoritative bundle:
- **Indian Premier League (IPL):** BCCI Playing Conditions (Impact Player, review protocols).
- **Big Bash League (BBL / WBBL):** Cricket Australia tournament regulations.
- **Pakistan Super League (PSL):** PCB Playing Conditions.
- **The Hundred:** ECB Playing Conditions (100-ball match format).
- **Domestic Multi-Day (Ranji Trophy, Sheffield Shield, County Championship):** National board regulations.
- **Club / Recreational Cricket:** Regional association guidelines.

Any natural-language question targeting these competitions will be identified by the Applicability Engine and addressed with a clear out-of-scope clarification rather than an incorrect international ruling.

---

## 4. Relationship Semantics

In accordance with ADR 0001 and Section 3 of the Pre-Phase 4 Audit:
1. **`INCORPORATES`:** All ICC Playing Conditions incorporate the baseline MCC Laws of Cricket for rules not modified.
2. **`MODIFIES`:** An ICC Playing Condition modifies a specific MCC Law (e.g. ICC Clause 21.18 modifies MCC Law 21 by instituting a mandatory Free Hit).
3. **`SUPPLEMENTS`:** An Addendum or Competition Regulation supplements a parent format condition without replacing it entirely.
4. **`SUPERSEDES`:** A newly effective edition replaces a predecessor edition for matches whose applicability trigger date falls on or after the transition boundary.
