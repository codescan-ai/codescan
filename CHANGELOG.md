# Changelog

## Unreleased

### Features

* **Externalized system prompts.** The three built-in prompts (`security`,
  `performance`, `clean_code`) now live as Markdown under `core/prompts/`
  instead of being Python string constants. Iterate on prompts without
  touching source.
* **`--prompt-file PATH`** — supply a custom system prompt from disk,
  overriding the built-in.
* **`--prompt-preset {security,performance,clean_code}`** — select which
  built-in prompt to use when `--prompt-file` is not supplied. Defaults
  to `security`.
* **Full-directory scan hygiene.** `_scan_files` now skips common junk
  directories (`.git`, `node_modules`, `__pycache__`, `.venv`, `dist`, ...)
  and files whose extension isn't a recognised source-code type. Adds a
  256 KiB per-file cap to keep large generated files off the wire.
* **`--exclude-dir NAME`** (repeatable) and **`--max-file-bytes N`** to
  override the defaults.

### Bug Fixes

* **Security prompt tightened.** Added rules 6–9 targeting the classes of
  false positive that surfaced in real-world scans: unverified claims
  about external functions, language-level-guarantee violations, missing
  taint provenance, and speculative-connective hedging ("if the value
  is ever ...", "may return a string", etc.). Fixed a stale "five checks"
  reference — there are now nine.
* Skip binary/non-UTF-8 files quietly instead of catching `Exception`
  and logging a warning.

## [0.1.4](https://github.com/codescan-ai/codescan/compare/v0.1.3...v0.1.4) (2026-08-17)


### Bug Fixes

* migrate pydantic-ai Agent API from result_type to output_type ([#62](https://github.com/codescan-ai/codescan/issues/62)) ([efc0ae2](https://github.com/codescan-ai/codescan/commit/efc0ae24b08278f9bddaeb7d65972001dac0e032)), closes [#61](https://github.com/codescan-ai/codescan/issues/61)

## [0.1.3](https://github.com/codescan-ai/codescan/compare/v0.1.2...v0.1.3) (2026-06-15)


### Bug Fixes

* set dummy OPENAI_API_KEY fallback for custom providers and correct Ollama endpoint ([#60](https://github.com/codescan-ai/codescan/issues/60)) ([c5defc7](https://github.com/codescan-ai/codescan/commit/c5defc72316c1cabbdbffcafa1cbbf6a1f385ca8)), closes [#59](https://github.com/codescan-ai/codescan/issues/59)


### Documentation

* update README for v0.1.2 with V2 agent scanner and diff-aware analysis ([55177b9](https://github.com/codescan-ai/codescan/commit/55177b90229bba072318d43d9d2f456cb8965c71))

## [0.1.2](https://github.com/codescan-ai/codescan/compare/v0.1.1...v0.1.2) (2026-04-13)


### Documentation

* clarify and improve custom AI server examples ([#43](https://github.com/codescan-ai/codescan/issues/43)) ([a461cd1](https://github.com/codescan-ai/codescan/commit/a461cd12b3a8ee38389c547c8f70141f099ea249))
* update some section in the README and retrive the workflow  badges ([bd59433](https://github.com/codescan-ai/codescan/commit/bd594331965d2810d14e6678a3f163f1e9a56ab6))
* update some sections in the README and retrieve the workflow badges ([0868d21](https://github.com/codescan-ai/codescan/commit/0868d21cccf85c3514cdea9c7a49360c831c1e83))

## [0.1.1](https://github.com/codescan-ai/codescan/compare/v0.1.0...v0.1.1) (2024-08-28)


### Bug Fixes

* make some changes to the README file ([89ab458](https://github.com/codescan-ai/codescan/commit/89ab45890e7954e7ea339283907877fb148877b1))

## 0.1.0 (2024-08-28)


### Features

* add a changelog and update the MANIFEST ([d042034](https://github.com/codescan-ai/codescan/commit/d042034f1b22b808f97318599d90c7a57e8d05ed))
* add an issue template folder ([73d579b](https://github.com/codescan-ai/codescan/commit/73d579b490f16faac726f655ca7a6dce32a9c7be))
