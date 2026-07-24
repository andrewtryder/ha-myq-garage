# Security Policy

## Supported Versions

This project follows [semantic versioning](https://semver.org/) via `release-please`. Only the latest published release is actively supported with security fixes.

## Reporting a Vulnerability

Please do **not** open a public GitHub issue for security vulnerabilities.

Instead, report vulnerabilities privately using GitHub's [private vulnerability reporting](https://github.com/andrewtryder/ha-myq-garage/security/advisories/new) feature:

1. Go to the [Security tab](https://github.com/andrewtryder/ha-myq-garage/security) of this repository.
2. Select **Report a vulnerability**.
3. Provide as much detail as possible: affected version(s), reproduction steps, and potential impact.

You should expect an initial response within 7 days. If the report is confirmed, a fix will be prepared and released, and the advisory will be published (with credit to the reporter, unless anonymity is requested) once a patched version is available.

## Scope

This integration communicates with a companion API over HTTPS using a Bearer API key that you control. It does not talk to MyQ's own cloud service directly. Vulnerabilities in your own companion API implementation are outside the scope of this repository; please report those to that project instead.
