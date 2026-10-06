# Research summary and what it changed (Oct 2026)

Six notes sit beside this file (01 marketplaces, 02 policy/legal, 03 product quality, 04 tooling, 05 risks/benchmarks, 06 marketing/formats). Highlights:

1. **Demand is real but income is skewed.** Printable planners, wall art, templates and worksheets sell; most sellers earn little. Plan for many varied, good listings over months.
2. **Etsy is strict about AI**: disclosure in the description, "Designed by" attribution, no prompt products, and suspensions for mass near-identical listings. MoneyHub's approach (template-driven, human-reviewed, varied, disclosed) is the safe path; add guards.
3. **IP is the fastest way to lose a shop.** Brand/character/celebrity/sports terms and resold free assets. -> built-in **risk check**.
4. **Buyer experience drives reviews and ranking.** Print-at-actual-size, compatibility, working links, no typos. -> **Start Here** page, licence, QA.
5. **Pinterest + short video are the traffic engines**, with fresh creative, keyword-rich text, a strong first 3 seconds and captions. -> **/brag-style launch videos** with music, captions and share copy.
6. **Timing matters**: list 6-9 weeks before peak. -> **seasonal calendar**.
7. **Bundles and freebies** raise value and funnel traffic. -> **bundle builder** and **free sample** PDFs.
8. **Spreadsheets** need protected formulas, a Start Here sheet and a Google Sheets copy-link PDF. -> sheet protection and instructions.
9. **KDP** is a second outlet for planner/journal interiors with its own margin rules (future).
10. **APIs**: Etsy has a draft-listing API (needs approval); others lack one. Manual upload stays; revisit an Etsy draft publisher when it can be tested.

## Built in this round (see commit log)
`moneyhub brag` (launch video + music + SFX + captions + share copy, from latent-spaces/brag, MIT), `moneyhub risk`, `moneyhub bundle`, `moneyhub sample`, `moneyhub calendar`, `moneyhub keywords`, Start Here page in every package, sheet protection, media QA, pin safe-zone fix. (A Google Sheets copy-link page and a separate licence page were considered but are not built; the Start Here page carries the licence note.)

## Not built (and why)
Etsy/Pinterest API publishing (cannot be verified from this sandbox; policy expects human review), KDP export, Typst engine, HyperFrames engine, e-ink/disc-bound planner variants (exact specs not verified), AI music models (licence/hardware), Canva/Notion native files.
