# Third-party notices / 외부 자료 고지

Checked 2026-11-19. Root LICENSE covers original project contributions only. A source license label does not prove this repository's bytes match the source.

| Component | Location/use | Terms and verification |
|---|---|---|
| Trillion Labs Zoro-1 | Operator-configured API / integration | Official model card: Apache-2.0 weights. Download access terms are separate. Actual operator checkpoint/revision and downloaded code/NOTICE require verification. |
| KoELECTRA, monologg and contributors | models/v46; apps/shared/nlp; apps/dist/web/nlp | Upstream repository Apache-2.0; local assets obtained via npm ONNX bundle, NOT byte-verified against upstream. Recorded changes: fine-tuning, int8 quantization and JSON/JS/base64 conversion. |
| kakaotalk-chat-analyzer-models@0.2.1, claudianus | Intermediate ONNX source recorded by model card | Version metadata reports MIT. Current upstream MIT copyright text preserved in LICENSES/kakaotalk-chat-analyzer-MIT.txt (Copyright (c) 2026 claudianus). Not proof of the exact historical tarball's complete terms; underlying model rights remain separate. |
| 3i4k, warnikchow and contributors | tools/nlp/data and training provenance | CC-BY-SA-4.0. Preserve credit/license and source fields. Changes: class filtering, added labels, JSONL conversion, split/combination with synthetic sentences. Existing fine-tuned weight/head CC-BY-SA declarations retained; no automatic legal conclusion about all trained weights. |
| Capacitor | apps/mobile/package.json | Installed dependencies retain their own licenses. Exact resolved versions and distributed binary contents need audit when building mobile packages. |
| Python/model libraries | requirements-generation.txt | Respective upstream licenses apply; dependency list is not a verified binary SBOM. |
| Jev and remote services | Optional API integration | Access, billing and service terms are separate; no model weights licensed by this notice. |
| Legacy skills, snapshots, documents, archives | internal/, vendor/, dmsg/, data/, tests_data/, APK/ZIP/skill | Original rights retained; component provenance audit pending; not newly Apache-only. |

## Original sources
- Apache: https://www.apache.org/licenses/LICENSE-2.0.txt (unchanged root LICENSE)
- Zoro-1: https://huggingface.co/trillionlabs/Zoro-1
- KoELECTRA: https://github.com/monologg/KoELECTRA/blob/master/LICENSE
- npm version metadata: https://registry.npmjs.org/kakaotalk-chat-analyzer-models/0.2.1
- Intermediate MIT: https://github.com/claudianus/kakaotalk-chat-analyzer/blob/main/LICENSE (blob 0e77c1a15d8e50a8fbebd0d141e29c79bad23a39)
- 3i4k creator/source: https://github.com/warnikchow/3i4k
- 3i4k license: https://github.com/warnikchow/3i4k/blob/master/LICENSE
- CC-BY-SA-4.0: https://creativecommons.org/licenses/by-sa/4.0/ (full text LICENSES/CC-BY-SA-4.0.txt)

## Historical packages
APK signatures, model hashes and ZIP contents were not rewritten. Sidecar notices do NOT insert missing notices inside archives, establish unknown rights or certify standalone downloads. For new standalone redistribution, resolve provenance and rebuild with all applicable notices and verified dependencies, or distribute a complete accompanying notice bundle. Never modify signed APK contents in place. Historical presence is not retroactive compliance clearance. No upstream NOTICE collection has been exhaustively verified.
