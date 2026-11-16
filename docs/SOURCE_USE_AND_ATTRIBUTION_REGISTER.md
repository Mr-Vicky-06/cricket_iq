# Source Use, Licensing, and Attribution Register — CricketIQ

**Version:** 1.0.0  
**Effective Date:** 2026-11-16  
**Auditor:** CricketIQ Data Governance & Legal Compliance Team  

---

## 1. Compliance Policy & Guiding Principles

CricketIQ is built upon the public regulatory publications of the **International Cricket Council (ICC)** and **Marylebone Cricket Club (MCC)**. While these documents are publicly published and freely accessible on official governing body web portals for players, match officials, and the global cricket public, **public accessibility does not automatically grant unrestricted copyright redistribution**.

CricketIQ enforces a four-tier permission model across every ingested source document:

| Permission Level | Code Flag | Definition | Permitted in CricketIQ? |
| :--- | :--- | :--- | :--- |
| **Download & Ingest** | `ALLOW_INGEST` | Automated fetching, local caching, and cryptographic verification of official document bytes. | **YES** (via secure downloader) |
| **Internal Semantic Index** | `ALLOW_INDEX` | Extraction of text, lexical parsing, sentence segmentation, and vector embedding generation for retrieval. | **YES** (purely internal data indexing) |
| **Verbatim Answer Citation** | `ALLOW_EXCERPT` | Inclusion of short, verbatim clause excerpts (1–3 sentences) in generated answers accompanied by exact official citation and source URL. | **YES** (Protected Fair Use / Quotation Right) |
| **Full-Text Redistribution** | `ALLOW_REDISTRIBUTE` | Hosting, mirroring, or providing complete bulk downloads of raw PDF text to third parties. | **NO / STRICTLY PROHIBITED** |

---

## 2. Document Rights & Attribution Matrix

| Source Document ID | Publisher | Official Rights / Copyright Notice | Download & Cache | Semantic Index | Excerpt in Citations | Full Redistribution | Mandatory Attribution Text | Official Direct Link |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **`ICC_TEST_MEN_2026`** | International Cricket Council | © International Cricket Council 2026 | Yes | Yes | Yes | No | *Source: ICC Men's Test Match Playing Conditions (October 2026 Edition), ICC.* | [ICC Document Link](https://images.icc-cricket.com/image/upload/prd/a8114zro5tkioifz0jqg.pdf) |
| **`ICC_ODI_MEN_2026`** | International Cricket Council | © International Cricket Council 2026 | Yes | Yes | Yes | No | *Source: ICC Men's One Day International Playing Conditions (October 2026 Edition), ICC.* | [ICC Document Link](https://images.icc-cricket.com/image/upload/prd/bxkzkcyvfn6tvi70zh0w.pdf) |
| **`ICC_T20I_MEN_2026`** | International Cricket Council | © International Cricket Council 2026 | Yes | Yes | Yes | No | *Source: ICC Men's Twenty20 International Playing Conditions (October 2026 Edition), ICC.* | [ICC Document Link](https://images.icc-cricket.com/image/upload/prd/bsxcho7ufe2pjban0wjp.pdf) |
| **`ICC_T20I_MEN_ADD_2026`** | International Cricket Council | © International Cricket Council 2026 | Yes | Yes | Yes | No | *Source: Addendum to ICC Men's T20I Playing Conditions (October 2026), ICC.* | [ICC Document Link](https://images.icc-cricket.com/image/upload/prd/pzyejpstlhptewq9qs2n.pdf) |
| **`ICC_TEST_WOMEN_2026`** | International Cricket Council | © International Cricket Council 2026 | Yes | Yes | Yes | No | *Source: ICC Women's Test Match Playing Conditions (October 2026 Edition), ICC.* | [ICC Document Link](https://images.icc-cricket.com/image/upload/prd/hbwwi78pugzpdwft0v4v.pdf) |
| **`ICC_ODI_WOMEN_2026`** | International Cricket Council | © International Cricket Council 2026 | Yes | Yes | Yes | No | *Source: ICC Women's One Day International Playing Conditions (October 2026 Edition), ICC.* | [ICC Document Link](https://images.icc-cricket.com/image/upload/prd/qunpw1kfh3ibxlz58jlw.pdf) |
| **`ICC_T20I_WOMEN_2026`** | International Cricket Council | © International Cricket Council 2026 | Yes | Yes | Yes | No | *Source: ICC Women's Twenty20 International Playing Conditions (October 2026 Edition), ICC.* | [ICC Document Link](https://images.icc-cricket.com/image/upload/prd/o3vhm0zw7pppoxpgopke.pdf) |
| **`MCC_LAWS_2026`** | Marylebone Cricket Club | © Marylebone Cricket Club 2026 | Controlled Local Fixture | Yes | Yes | No | *Source: The Laws of Cricket (2017 Code 4th Edition - 2026), Marylebone Cricket Club.* | [MCC Official Page](https://www.lords.org/mcc/about-the-laws-of-cricket) |
| **`MCC_LAWS_2022`** | Marylebone Cricket Club | © Marylebone Cricket Club 2022 | Controlled Local Fixture | Yes | Yes | No | *Source: The Laws of Cricket (2017 Code 3rd Edition - 2022), Marylebone Cricket Club.* | [MCC Official Page](https://www.lords.org/mcc/about-the-laws-of-cricket) |
| **`ICC_WTC_2025_2027_PC`** | International Cricket Council | © International Cricket Council 2026 | Yes | Yes | Yes | No | *Source: ICC World Test Championship 2025–2027 Playing Conditions, ICC.* | [ICC Document Link](https://images.icc-cricket.com/image/upload/prd/jrwhpcwk8mmpv0fx3lnd.pdf) |

---

## 3. Data Governance Protocols

### 3.1 Immutable Raw Storage
All downloaded PDFs must be stored in `cricketiq/data/sources/raw/{publisher}/` with read-only permissions after initial write. No process, normalization script, or human edit is permitted to alter raw source bytes.

### 3.2 Display View Filtering (`display_text`)
When returning retrieved evidence to any end-user or testing UI:
1. The system must display the `display_text` or bounded clause excerpt, not full page dumps.
2. The response must include:
   - The authoritative Publisher (`ICC` or `MCC`)
   - Document Title and Edition (`e.g. ICC Men's T20I Playing Conditions (October 2026 Edition)`)
   - Clause Number (`e.g. Clause 21.18.2`)
   - Source Page locator
   - An active hyperlink to the official governing body URL.

### 3.3 MCC Egress Constraint Handling
Because `lords.org` TCP egress encounters timeouts in this environment:
1. Live network scraping of `lords.org` is suspended.
2. The MCC Laws 2026 and 2022 editions are ingested via verified local fixture files with pre-calculated SHA-256 hashes matching official MCC distributions.
3. Every MCC source record is flagged with `network_status = "egress_restricted_fixture"`.
