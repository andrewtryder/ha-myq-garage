# Changelog

## [1.4.0](https://github.com/andrewtryder/ha-myq-garage/compare/v1.3.0...v1.4.0) (2026-07-24)


### Features

* add entity translations, icons, and workflow security checks ([#28](https://github.com/andrewtryder/ha-myq-garage/issues/28)) ([bf6219a](https://github.com/andrewtryder/ha-myq-garage/commit/bf6219a233a180a619732a2dcf2b539f84185db5))
* add reconfigure, repair issue, and redacted diagnostics ([#26](https://github.com/andrewtryder/ha-myq-garage/issues/26)) ([2b70b0b](https://github.com/andrewtryder/ha-myq-garage/commit/2b70b0bea9a0852a61f7cd680b4e99c64ebaa937))
* allow manual removal of stale garage devices ([#27](https://github.com/andrewtryder/ha-myq-garage/issues/27)) ([057dbe9](https://github.com/andrewtryder/ha-myq-garage/commit/057dbe991605c1a8be0ba9546b53860d9a4230c8))
* extract myq-garage-api package for dependency transparency ([#29](https://github.com/andrewtryder/ha-myq-garage/issues/29)) ([4e797d6](https://github.com/andrewtryder/ha-myq-garage/commit/4e797d62991f7b344580830f7ed4bc72aed2d4f2))


### Bug Fixes

* require /info verification for identified reauth ([#24](https://github.com/andrewtryder/ha-myq-garage/issues/24)) ([c99790c](https://github.com/andrewtryder/ha-myq-garage/commit/c99790c3a80137bebfc55b9eebabacdee8345061))

## [1.3.0](https://github.com/andrewtryder/ha-myq-garage/compare/v1.2.0...v1.3.0) (2026-07-24)


### Features

* harden post-1.2.0 migration, reauth, discovery, and CI ([2c17542](https://github.com/andrewtryder/ha-myq-garage/commit/2c17542fd54153e0b8ff7aa37773b2adbaf577b9))


### Bug Fixes

* drop coverage artifact upload that fails with 403 ([01223b8](https://github.com/andrewtryder/ha-myq-garage/commit/01223b86235070e8aa8a44172bdaeaaac12d3bb5))
* regenerate test lockfile for Linux CI ([b266c9c](https://github.com/andrewtryder/ha-myq-garage/commit/b266c9cb9d9baaac11f2aaad1eacbdea2a58eff3))

## [1.2.0](https://github.com/andrewtryder/ha-myq-garage/compare/v1.1.1...v1.2.0) (2026-07-24)


### Features

* meet HACS Silver quality readiness requirements ([c859c4e](https://github.com/andrewtryder/ha-myq-garage/commit/c859c4ef5fdec0878fa91a27cd0c5537750b0050))
* meet HACS Silver quality readiness requirements ([4c92bad](https://github.com/andrewtryder/ha-myq-garage/commit/4c92badaba4fd0571902df3d488a58cbabf68c30))


### Bug Fixes

* pre-1.2.0 release blockers ([#15](https://github.com/andrewtryder/ha-myq-garage/issues/15)) ([298fc9a](https://github.com/andrewtryder/ha-myq-garage/commit/298fc9a1ef42135bb6dac6de0ebf9bcd46aab1cd))

## [1.1.1](https://github.com/andrewtryder/ha-myq-garage/compare/v1.1.0...v1.1.1) (2026-07-24)


### Bug Fixes

* replace aioresponses with AsyncMock for aiohttp 3.14 ([e770369](https://github.com/andrewtryder/ha-myq-garage/commit/e7703691440f09be7e698fcce52d32015d57be16))
* replace aioresponses with AsyncMock for aiohttp 3.14 ([b63be95](https://github.com/andrewtryder/ha-myq-garage/commit/b63be958b4ef4035002e3930978017b50b747dfb))

## [1.1.0](https://github.com/andrewtryder/ha-myq-garage/compare/v1.0.1...v1.1.0) (2026-06-19)


### Features

* add configurable scan interval via options flow ([f6486d1](https://github.com/andrewtryder/ha-myq-garage/commit/f6486d1d2fad56d3aad69d64718c621926c9eebf))
* add configurable scan interval via options flow ([5214ff7](https://github.com/andrewtryder/ha-myq-garage/commit/5214ff7e34195224490e4015ed66f96cd662beb5))

## [1.0.1](https://github.com/andrewtryder/ha-myq-garage/compare/v1.0.0...v1.0.1) (2026-06-18)


### Bug Fixes

* prevent duplicate config entries via unique_id ([595667f](https://github.com/andrewtryder/ha-myq-garage/commit/595667f4963609fe08dc04bc441b0c476ca1f6ae))

## 1.0.0 (2026-06-18)


### ⚠ BREAKING CHANGES

* First production release of the MyQ Garage integration.

### Features

* initial MyQ Garage release with brand assets and local dev environment ([9a9ad28](https://github.com/andrewtryder/ha-myq-garage/commit/9a9ad28903a8ab01f12cd469759e007f39f7f24c))


### Bug Fixes

* HACS validation errors and Python 3.14 test failure ([4e23269](https://github.com/andrewtryder/ha-myq-garage/commit/4e232694c668f5a9eb387dbbe92929e9e9436e8e))
* ignore HACS repository topics and description validation ([96f0fab](https://github.com/andrewtryder/ha-myq-garage/commit/96f0faba5be4d8d7a93224120638a21f3fa87751))
* resolve hacs.json schema failures and add missing test dependency ([e1e392c](https://github.com/andrewtryder/ha-myq-garage/commit/e1e392c77ea35ba1893bf52bb186fba01a3d4fe0))
