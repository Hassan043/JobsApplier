# Repository ownership and provenance

The working folder originally pointed to https://github.com/itxhas/JobsApplier and had `af603ba` as its checked-out initial commit; the old remote also advertised `8ca9174`. This explains the prior owner/author labels. Repository ownership and commit authorship are separate concepts.

The maintained portfolio source is the new modular `job_assistant` implementation, synthetic examples, evaluation infrastructure, tests, and current documentation. The new repository is under Hassan043 and its new commits use the account's GitHub noreply identity.

The original commit has not been renamed or falsely attributed. Original history and uncommitted changes were preserved in an ignored local backup and a local archive branch before creating the clean main history. Only the new main branch is intended to be pushed; do not push archive branches or use `git push --all`.

Legacy Python scrapers, the old Sheets path, historical PDF documentation, personal CVs, local configuration, sessions, and reports remain local and are excluded from the published portfolio branch. No upstream license was asserted or changed; this cleanup does not relicense upstream material.

The historical local backup lives under data/git-backup, which is ignored and must never be published. A new clone contains the maintained v2 workflow only. Documentation referring to preserved legacy files is historical context, not a claim those files ship in the new repository.
