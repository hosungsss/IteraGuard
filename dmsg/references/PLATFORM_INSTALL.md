# Cross-platform installation: one core, different clients

**Permanent internal skill ID**: `dmsg`; **invocation convention**: `/dmsg`; **archive file**: `dmsg.skill` (ZIP-compatible) and `dmsg.zip` (identical bytes). **Version changes never rename the ID.** No platform can guarantee native slash-command activation solely because a file was uploaded as an ordinary chat attachment.

## Claude

- Claude Code: unpack `dmsg/` into your repository `.claude/skills/dmsg/` or user directory `~/.claude/skills/dmsg/`. Use `/dmsg` if the client exposes user-invocable skills; otherwise ask Claude to use the installed `dmsg` skill.
- claude.ai with eligible skill uploads: Settings → Features → custom Skills → upload **`dmsg.zip`**. The `.skill` filename is not a documented universal import format. Installation availability varies with plan and code execution.

## Grok Build (terminal/agent product, not all Grok web clients)

- Unpack to `.grok/skills/dmsg/` or `~/.grok/skills/dmsg/`; the Grok Build docs specify these folders and user-invocable `/dmsg`. It also reads Claude Code skill directories in compatible environments. A normal Grok chat without this feature cannot be forced to register a native slash command by uploading a ZIP.

## OpenAI

- OpenAI API hosted Skills and Plugins use directories with `SKILL.md`, and ZIP with a **single top-level folder** is supported. Use `dmsg.zip` through the advertised API upload/Skills workflow, or put the directory in your agent sandbox.
- ChatGPT consumer UI may not expose general arbitrary `.skill` upload. If the account has no skills installer, supply `dmsg/SKILL.md` and references to the chat/project as instructions. This is *manual adaptation*, not native install or guaranteed `/dmsg` recognition.

## Portable defaults

- YAML contains only cross-platform required `name` and `description`; other user-invocable flags are omitted for portability.
- Scripts are Python standard-library, no external API keys, installs, or writes to third parties.
- No proprietary font or external secret bundled; local skill does not grant phone/bank permissions.
- Confirm host import and execution **on each platform**; a ZIP structure validation is not the same as vendor acceptance.

Official documentation: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview ; https://developers.openai.com/api/docs/guides/tools-skills ; https://docs.x.ai/build/features/skills-plugins-marketplaces .
