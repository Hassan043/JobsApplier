# Portal coverage and extension plan

Updated: 5 November 2026.
The catalog contains 175 distinct source entries, merging repeated names such as Dice and Built In while preserving group/country tags. It includes the requested country boards and a few existing employer-feed sources.

A catalog entry is not a working connector. Most of the supplied names have not been independently verified for current availability, authentication, API access, exports, or terms. No account login, password collection, browser automation, or application submission was added.

## Implemented access paths

- Existing Greenhouse employer-board collector: live smoke-tested earlier; explicit employer token required.
- Existing Lever employer-board collector: offline fixture-tested; explicit site identifier; current first-100 limit.
- New Remotive public-feed collector: offline fixture-tested, 15-second timeout, 8 MB cap, first-100 snapshot, persistent six-hour refresh/cooldown. Not live-probed in this change.
- New Arbeitnow public-feed collector: offline fixture-tested, 15-second timeout, 8 MB cap, first page only, conservative one-hour refresh/cooldown. Not live-probed in this change.
- Generic JSON/JSONL/CSV and saved JobPosting JSON-LD imports remain available when users can supply permitted data. This does not imply every portal offers an export.
- Pangian is degraded after a non-JSON live response. FlexJobs, Remote.co, and Bayt historical scripts are local-only, not maintained native adapters in the new repository.

## Commands

```powershell
python main.py portals
python main.py portals --group talent_networks
python main.py portals --country DE --json
python main.py portals --status fixture_tested
python main.py run --profile examples/demo_profile.json --feeds remotive arbeitnow --queries engineer developer --max-jobs 30
```

The last command is an explicit live-fetch example, not a synthetic demo. It requests jobs only; no CV is sent to these feed endpoints. Use local fixtures/dry-run for the portfolio demonstration. Feed collection is disallowed in dry-run. With multiple profiles, default local title filtering includes their combined role list.

## Access and provider requirements

- Remotive requires visible source attribution/backlinks, limits onward redistribution, and advises at most four refreshes daily. This adapter retains the original source link and enforces a six-hour local request interval, including after failed requests. Data may be delayed by 24 hours. It is not a syndication/export connector for other job boards.
- Arbeitnow documents a public API. Its remote field is not a statement that applicants worldwide are eligible; no country or visa entitlement is inferred.
- Himalayas has a documented API but is not implemented. Its original application links, attribution, expiration handling, and redistribution rules must be designed before adding it.
- LinkedIn prohibits scraping/automation through unapproved tools; its catalog route is manual review or a separately approved integration. This project adds no logged-in scraping.
- Google/GitHub are discovery/account platforms here. Immigration and general information resources are marked reference-only, not vacancy feeds.

Provider references: [Remotive](https://github.com/remotive-com/remote-jobs-api), [Arbeitnow](https://www.arbeitnow.com/blog/job-board-api), [Himalayas](https://himalayas.app/api), [LinkedIn](https://www.linkedin.com/help/linkedin/answer/a1341387/prohibition-of-scraping-software). These were reviewed; the remaining catalog names are a research backlog, not a verified link directory.

## Complete catalog

| Source | Groups | Countries/region | Status | Access |
|---|---|---|---|---|
| 104 Job Bank | country_boards | TW | research_required | manual_import |
| 1111 | country_boards | TW | research_required | manual_import |
| 51Job | country_boards | CN | research_required | manual_import |
| Absolventa | country_boards | DE | research_required | manual_import |
| Actiris | country_boards | BE | research_required | manual_import |
| ADEM | country_boards | LU | research_required | manual_import |
| aijobs.net | remote_boards | not scoped | research_required | manual_import |
| AMS | country_boards | AT | research_required | manual_import |
| Andela | talent_networks | not scoped | research_required | manual_import |
| ANPAL | country_boards | IT | research_required | manual_import |
| Apec | country_boards | FR | research_required | manual_import |
| APS Jobs | country_boards | AU | research_required | manual_import |
| Arbeidsplassen | country_boards | NO | research_required | manual_import |
| Arbeitnow | relocation | not scoped | fixture_tested | public_feed |
| Arbetsformedlingen | country_boards | SE | research_required | manual_import |
| Arc | talent_networks | not scoped | research_required | manual_import |
| Askable | ai_contract | not scoped | research_required | manual_import |
| Bayt | country_boards | MIDDLE_EAST | legacy_unverified | manual_import |
| BC Jobs | country_boards | CA | research_required | manual_import |
| Berlin Startup Jobs | country_boards | DE | research_required | manual_import |
| Blocket Jobb | country_boards | SE | research_required | manual_import |
| Boss Zhipin | country_boards | CN | research_required | manual_import |
| BrusselsJobs | country_boards | BE | research_required | manual_import |
| Built In | remote_boards, country_boards | US | research_required | manual_import |
| Bulldogjob | country_boards | PL | research_required | manual_import |
| CakeResume | country_boards | TW | research_required | manual_import |
| CareerCross | country_boards | JP | research_required | manual_import |
| CareerOne | country_boards | AU | research_required | manual_import |
| Careers.govt.nz | country_boards | NZ | reference_only | information |
| ChooseYourBoss | country_boards | FR | research_required | manual_import |
| Corriere Lavoro | country_boards | IT | research_required | manual_import |
| Crossover | talent_networks | not scoped | research_required | manual_import |
| CT Good Jobs | country_boards | HK | research_required | manual_import |
| Daijob | country_boards | JP | research_required | manual_import |
| derStandard Jobs | country_boards | AT | research_required | manual_import |
| Dice | accounts, country_boards | US | research_required | manual_import |
| Dubizzle Jobs | country_boards | MIDDLE_EAST | research_required | manual_import |
| Duunitori | country_boards | FI | research_required | manual_import |
| Dynamite Jobs | remote_boards | not scoped | research_required | manual_import |
| Eluta | country_boards | CA | research_required | manual_import |
| Empleate | country_boards | ES | research_required | manual_import |
| EthicalJobs | country_boards | AU | research_required | manual_import |
| EURES | relocation | not scoped | research_required | manual_import |
| Finn.no Jobb | country_boards | NO | research_required | manual_import |
| Fiverr | accounts | not scoped | research_required | manual_import |
| FlexJobs | remote_boards | not scoped | legacy_unverified | manual_import |
| France Travail | country_boards | FR | research_required | manual_import |
| Freelancer | accounts | not scoped | research_required | manual_import |
| G2i | talent_networks | not scoped | research_required | manual_import |
| GaijinPot Jobs | country_boards | JP | research_required | manual_import |
| GitHub | accounts | not scoped | discovery_only | manual_discovery |
| Glassdoor | remote_boards | not scoped | research_required | manual_import |
| Google | accounts | not scoped | discovery_only | manual_discovery |
| GradIreland | country_boards | IE | research_required | manual_import |
| Greenhouse | employer_feeds | not scoped | live_smoke_verified | employer_board |
| Gulf News Jobs | country_boards | MIDDLE_EAST | research_required | manual_import |
| GulfTalent | country_boards | MIDDLE_EAST | research_required | manual_import |
| Gun.io | talent_networks | not scoped | research_required | manual_import |
| Hacker News jobs | remote_boards | not scoped | research_required | manual_import |
| HelloWork | country_boards | FR | research_required | manual_import |
| Himalayas | remote_boards | not scoped | documented_not_implemented | public_api_research |
| IEFP | country_boards | PT | research_required | manual_import |
| Immigration info (Canada) | country_boards | CA | reference_only | information |
| Immigration NZ | country_boards | NZ | reference_only | information |
| Indeed | accounts | not scoped | research_required | manual_import |
| Indeed CH | country_boards | CH | research_required | manual_import |
| Indeed Pakistan | pakistan | PK | research_required | manual_import |
| Infoempleo | country_boards | ES | research_required | manual_import |
| InfoJobs | country_boards | ES | research_required | manual_import |
| InfoJobs IT | country_boards | IT | research_required | manual_import |
| IrishJobs | country_boards | IE | research_required | manual_import |
| ITJobs | country_boards | PT | research_required | manual_import |
| Jadarat | country_boards | MIDDLE_EAST | research_required | manual_import |
| Job Bank | country_boards | CA | research_required | manual_import |
| Job Market Finland | country_boards | FI | research_required | manual_import |
| Job-Room | country_boards | CH | research_required | manual_import |
| Jobat | country_boards | BE | research_required | manual_import |
| Jobbnorge | country_boards | NO | research_required | manual_import |
| Jobborse (Germany) | country_boards | DE | research_required | manual_import |
| Jobgether | remote_boards | not scoped | research_required | manual_import |
| Jobicy | remote_boards | not scoped | research_required | manual_import |
| Jobillico | country_boards | CA | research_required | manual_import |
| Jobindex | country_boards | DK | research_required | manual_import |
| Jobnet | country_boards | DK | research_required | manual_import |
| Jobrapido IT | country_boards | IT | research_required | manual_import |
| Jobs.ch | country_boards | CH | research_required | manual_import |
| Jobs.ie | country_boards | IE | research_required | manual_import |
| Jobs.lu | country_boards | LU | research_required | manual_import |
| Jobs.nzz.ch | country_boards | CH | research_required | manual_import |
| JobsDB HK | country_boards | HK | research_required | manual_import |
| JobsIreland | country_boards | IE | research_required | manual_import |
| Jobspresso | remote_boards | not scoped | research_required | manual_import |
| JobStreet | country_boards | SG | research_required | manual_import |
| Jobup.ch | country_boards | CH | research_required | manual_import |
| Jobware | country_boards | DE | research_required | manual_import |
| Just Join IT | relocation | not scoped | research_required | manual_import |
| Karriere.at | country_boards | AT | research_required | manual_import |
| Landing.jobs | relocation | not scoped | research_required | manual_import |
| Lavoro.gov | country_boards | IT | research_required | manual_import |
| Le Forem | country_boards | BE | research_required | manual_import |
| Lemon.io | talent_networks | not scoped | research_required | manual_import |
| LesJeudis | country_boards | FR | research_required | manual_import |
| Lever | employer_feeds | not scoped | fixture_tested | employer_board |
| Liepin | country_boards | CN | research_required | manual_import |
| LinkedIn | accounts | not scoped | manual_only | manual_import |
| Make it in Germany | country_boards | DE | research_required | manual_import |
| Mercor | ai_contract | not scoped | research_required | manual_import |
| micro1 | ai_contract | not scoped | research_required | manual_import |
| Monaco Economic Board | country_boards | MC | reference_only | information |
| Monster CA | country_boards | CA | research_required | manual_import |
| Monster FI | country_boards | FI | research_required | manual_import |
| Monster SE | country_boards | SE | research_required | manual_import |
| Monsterboard | country_boards | NL | research_required | manual_import |
| Moovijob | country_boards | LU | research_required | manual_import |
| Motore Lavoro | country_boards | IT | research_required | manual_import |
| Mustakbil | pakistan | PK | research_required | manual_import |
| MyCareersFuture | country_boards | SG | research_required | manual_import |
| Nationale Vacaturebank | country_boards | NL | research_required | manual_import |
| Naukrigulf | country_boards | MIDDLE_EAST | research_required | manual_import |
| NAV Arbeid | country_boards | NO | research_required | manual_import |
| Net-Empregos | country_boards | PT | research_required | manual_import |
| No Fluff Jobs | relocation | not scoped | research_required | manual_import |
| NoDesk | remote_boards | not scoped | research_required | manual_import |
| Ofir | country_boards | DK | research_required | manual_import |
| Oikotie Tyopaikat | country_boards | FI | research_required | manual_import |
| Pangian | employer_feeds | not scoped | degraded | legacy_compatible_feed |
| Pracuj.pl | country_boards | PL | research_required | manual_import |
| Proxify | talent_networks | not scoped | research_required | manual_import |
| Public Employment (Poland) | country_boards | PL | research_required | manual_import |
| Python.org jobs | remote_boards | not scoped | research_required | manual_import |
| Recruit.com.hk | country_boards | HK | research_required | manual_import |
| Relocate.me | relocation | not scoped | research_required | manual_import |
| Remote Front | remote_boards | not scoped | research_required | manual_import |
| Remote OK | remote_boards | not scoped | research_required | manual_import |
| Remote Rocketship | remote_boards | not scoped | research_required | manual_import |
| Remote.co | employer_feeds | not scoped | legacy_unverified | manual_import |
| Remotive | remote_boards | not scoped | fixture_tested | public_feed |
| RocketJobs | country_boards | PL | research_required | manual_import |
| Rozee.pk | pakistan | PK | research_required | manual_import |
| Sapo Emprego | country_boards | PT | research_required | manual_import |
| SEEK | country_boards | AU | research_required | manual_import |
| SEEK NZ | country_boards | NZ | research_required | manual_import |
| SEPE | country_boards | ES | research_required | manual_import |
| StepStone | country_boards | DE | research_required | manual_import |
| StepStone AT | country_boards | AT | research_required | manual_import |
| StepStone BE | country_boards | BE | research_required | manual_import |
| Subito Lavoro | country_boards | IT | research_required | manual_import |
| Sweden.se | country_boards | SE | reference_only | information |
| Tecnoempleo | country_boards | ES | research_required | manual_import |
| TheHub | country_boards | DK | research_required | manual_import |
| ThinkSpain Jobs | country_boards | ES | research_required | manual_import |
| Together Abroad | country_boards | NL | research_required | manual_import |
| Toptal | talent_networks | not scoped | research_required | manual_import |
| Trade Me Jobs | country_boards | NZ | research_required | manual_import |
| Turing | talent_networks | not scoped | research_required | manual_import |
| Undutchables | country_boards | NL | research_required | manual_import |
| Upwork | accounts | not scoped | research_required | manual_import |
| USAJOBS | country_boards | US | research_required | manual_import |
| VDAB | country_boards | BE | research_required | manual_import |
| VisaSponsor.jobs | relocation | not scoped | research_required | manual_import |
| Wantedly | country_boards | JP | research_required | manual_import |
| We Work Remotely | remote_boards | not scoped | research_required | manual_import |
| Welcome to the Jungle | relocation | not scoped | research_required | manual_import |
| Wellfound | remote_boards | not scoped | research_required | manual_import |
| Werk.nl | country_boards | NL | research_required | manual_import |
| Work in Denmark | country_boards | DK | research_required | manual_import |
| Work in Finland | country_boards | FI | research_required | manual_import |
| Work in Norway | country_boards | NO | research_required | manual_import |
| Workforce Australia | country_boards | AU | research_required | manual_import |
| Working Nomads | remote_boards | not scoped | research_required | manual_import |
| Workopolis | country_boards | CA | research_required | manual_import |
| Xing Jobs | country_boards | DE | research_required | manual_import |
| Y Combinator jobs | remote_boards | not scoped | research_required | manual_import |
| Yourator | country_boards | TW | research_required | manual_import |
| ZipRecruiter | remote_boards | not scoped | research_required | manual_import |

## Engineering contract for the next adapter

1. Verify the actual service identity, official documentation, and permitted access route. An account existing does not establish automated access permission.
2. Choose a documented API/feed or manual import. Define credentials outside source control only where an approved authenticated integration requires them.
3. Implement a pure fixture parser returning the shared Job schema. Preserve provider/source links; do not infer worldwide eligibility, salary currency, period, sponsorship, or employer-country from a vague location.
4. Add one bounded collector: fixed/validated destinations, request timeout, response/page/job caps, cooldown/cache, cancellation behavior, and explicit partial-coverage warnings.
5. Test schema drift, empty versus unavailable source, duplicates, invalid URLs, missing pay, country restrictions, rate limits, and attribution. Never substitute a success-looking empty search for a failed request.
6. Wire CLI options and dry-run exclusion; update catalog status from research to fixture-tested only after tests pass. Mark live verification separately with date and scope.
7. Document provider-specific data lifecycle, attribution, removal/expiry, and redistribution behavior. Avoid syncing feed snapshots to other job boards without permission.
8. Keep scoring/model logic independent of collection. All portal data is untrusted input. API-based matching remains optional; no applications or messages are sent automatically.

## Cache operations

Caches and attempt timestamps live under the selected local database directory/source_cache and are ignored by Git. Changing profile/query does not trigger a new request while the same feed snapshot is fresh. A failed request enters cooldown; stale data is not silently served as fresh. Concurrent refresh uses a local exclusive lock. A crashed process can leave a lock; verify no worker is active before manually removing that exact local lock file. This is a local CLI coordination mechanism, not a distributed rate limiter.

Do not publish cached live postings, account sessions, private CVs, or personal reports in the portfolio repository. Synthetic fixtures demonstrate connector behavior without requiring accounts.
