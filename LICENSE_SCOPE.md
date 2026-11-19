# License scope / 적용 범위

Effective 2026-11-19. The maintainer authorized Apache-2.0 publication of original IteraGuard work. Copyright (c) 2026 IteraGuard contributors, each for their own contributions. This does not assert ownership of third-party or other contributors' rights.

Original project-authored code, configurations, tests and original documentation are licensed under Apache-2.0 (LICENSE), except material with its own notice or listed below. This covers our own contributions in arena/, integration/, rulebook/, linkguard/, tools/ and apps/, not embedded external data or copied works. Preserve original third-party notices. No trademark/endorsement rights are added.

## Exceptions: not newly relicensed as Apache-2.0
- models/**, apps/shared/nlp/**, apps/dist/web/nlp/**: model/vocabulary assets; retain existing CC-BY-SA-4.0 weight/head declarations and upstream rights. Base encoder provenance remains unverified.
- tools/nlp/data/**: authored synthetic records mixed with 3i4k CC-BY-SA-4.0 records; not an Apache-only dataset.
- internal/**, vendor/**, dmsg/**: historical snapshots, legacy skills and review/source materials; existing rights retained, full provenance/ownership audit pending.
- *.apk, *.zip, *.skill, apps/dist/**: historical distributions/fixtures; per-component licenses apply. Sidecars do not relicense or certify archives.
- data/**, tests_data/** and externally sourced media, documents, fonts, model assets or quoted text anywhere: original rights apply. Only original project-authored portions of synthetic fixtures are covered by the project grant.
- Installed dependencies, separately downloaded models and remote APIs retain their own licenses/service terms.

Unresolved means no additional permission is granted here, not that an existing upstream permission is revoked. No document here restricts rights already granted by an applicable license. Training on CC data alone is not treated as proof of automatic license propagation to all weights; existing weight declarations are retained.

## Distribution
Include LICENSE, NOTICE, LICENSE_SCOPE.md, THIRD_PARTY_NOTICES.md, applicable LICENSES/ texts and adjacent notices. Preserve original copyright/attribution; mark modified copied Apache files. Carry relevant original NOTICE contents where supplied. Before distributing legacy standalone packages, verify contents and rebuild with required notices or supply a complete accompanying license bundle. These documents do not certify all historical assets, commits, dependencies or contributor rights.
