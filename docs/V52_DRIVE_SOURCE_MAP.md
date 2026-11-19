# Google Drive source survey, read-only

Supplied root: `https://drive.google.com/drive/folders/1CosYeNIQUJQLNuOYx5PzjGLsdj0hWfMY?hl=ko`.

Connector listing on 2026-11-10 returned **33 direct children**. Versioned folders include v3.1.0, v3.4/3.5/3.6/4.0–4.9/5.0/5.1 and support folders `Package`, `Back Data`, `Trida textbook`, `iteraguard`. Root also contains `LATEST_VERSION.json`, `README.md`, early PRD/SystemPrompt, named .skill versions, team guide. The v5.1 folder lists **44 direct children**, primarily source directories and current metadata/README/APK/dmsg archives.

**Latest source decision:** user-uploaded v5.1 ZIP, verified locally (876 entries; CRC passes; SHA-256 recorded in architecture document), is the canonical editable baseline. Drive v5.1 and earlier folders were inspected at the *metadata* level, not recursively downloaded, content-audited, or blended. The appropriate use of historical versions is verified back-reference and compatible positive capability reuse, not unconditional file copying. No Google Drive modifications were made.

**Selection rule:** Adopt an idea only if it closes a known gap, preserves current interfaces and improves performance/safety on an independently held-out dataset. No auto-promotion from older/redundant versions. Ask the team for exact legacy feature diffs when relevant and preserve historical evidence.
