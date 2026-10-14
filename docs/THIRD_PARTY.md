# Dependencies, licenses and distribution boundary

Inspected on 2026-10-14: installed package metadata and distributed license files,
[pySigma source/license](https://github.com/SigmaHQ/pySigma/tree/54e4077532d1ae654ed565b5a61b75e76e8f725a),
and upstream package pages. Versions below match requirements.lock. Direct runtime
dependencies are pySigma and PyYAML. Others are required transitively by pySigma,
even where this CLI does not use their features. Windows/CLI/XML code uses stdlib.

pyproject.toml pins both direct dependencies. requirements.lock pins the tested
runtime resolution; requirements-dev.lock adds exact development tools. Upgrades
require contract tests and renewed license review. Pins are not a security audit.

| Package/version | Why installed | License in metadata/notice | Redistribution implications |
|---|---|---|---|
| [pySigma 2.0.1](https://pypi.org/project/pySigma/2.0.1/) | Sigma validation/condition AST | LGPL-2.1-only | Keep library replaceable; preserve notices and LGPL source/distribution obligations. |
| [PyYAML 6.0.3](https://pypi.org/project/PyYAML/6.0.3/) | Safe YAML input and pySigma dependency | MIT | Preserve notices. |
| [diskcache 5.6.3](https://pypi.org/project/diskcache/5.6.3/) | pySigma caching; no SigDoctor cache instantiated | Apache-2.0 | Retain license/applicable notices; mark modifications. |
| [diskcache-stubs 5.6.3.6.20240818](https://pypi.org/project/diskcache-stubs/5.6.3.6.20240818/) | pySigma-declared type dependency | Apache-2.0 | Retain license/notices. |
| [typing_extensions 4.16.0](https://pypi.org/project/typing_extensions/4.16.0/) | Stub typing dependency | PSF-2.0 | Retain distributed license/notices. |
| [google-re2 1.1.20251105](https://pypi.org/project/google-re2/1.1.20251105/) | pySigma regex facilities; unsupported here | BSD-3-Clause (RE2 notice) | Preserve notices/non-endorsement; review bundled native components for redistribution. |
| [Jinja2 3.1.6](https://pypi.org/project/Jinja2/3.1.6/) | pySigma conversion facilities; unused here | BSD-3-Clause | Preserve notices/non-endorsement. |
| [MarkupSafe 3.0.4](https://pypi.org/project/MarkupSafe/3.0.4/) | Jinja2 dependency | BSD-3-Clause | Preserve notices/non-endorsement. |
| [jq 1.12.0](https://pypi.org/project/jq/1.12.0/) | pySigma transformations; unused here | BSD-2-Clause for Python binding | Preserve binding notice; bundled libjq/libonig have separate notices. |
| [packaging 26.3](https://pypi.org/project/packaging/26.3/) | pySigma version handling | Apache-2.0 OR BSD-2-Clause | Comply with a selected offered license and preserve notices. |
| [pyparsing 3.3.3](https://pypi.org/project/pyparsing/3.3.3/) | Sigma condition grammar | MIT | Preserve notices. |
| [requests 2.34.2](https://pypi.org/project/requests/2.34.2/) | pySigma dependency; no SigDoctor HTTP calls | Apache-2.0 | Preserve license/applicable notices. |
| [charset-normalizer 3.5.2](https://pypi.org/project/charset-normalizer/3.5.2/) | requests dependency | MIT | Preserve notices. |
| [idna 3.20](https://pypi.org/project/idna/3.20/) | requests dependency | BSD-3-Clause | Preserve notices/non-endorsement. |
| [urllib3 2.8.0](https://pypi.org/project/urllib3/2.8.0/) | requests dependency | MIT | Preserve notices. |
| [certifi 2026.7.22](https://pypi.org/project/certifi/2026.7.22/) | requests CA bundle | MPL-2.0 | Preserve license and covered-file source obligations when distributing. |
| [types-PyYAML 6.0.12.20260906](https://pypi.org/project/types-PyYAML/6.0.12.20260906/) | pySigma-declared type dependency | Apache-2.0 | Preserve notices. |

## Project license

The existing MIT license is unchanged. SigDoctor's independently authored code
imports an unmodified, separately installed LGPL library. This arrangement
appears compatible with retaining MIT for SigDoctor's own code; it does not
relicense pySigma or remove LGPL requirements. SigDoctor's wheel contains no
dependency code. See the actual
[LGPL-2.1 text](https://github.com/SigmaHQ/pySigma/blob/54e4077532d1ae654ed565b5a61b75e76e8f725a/LICENSE).

When redistributing dependencies, retain notices, provide required library
source/access to source, and preserve the user's ability to modify/replace the
LGPL component. A frozen executable or bundled installer has not been assessed
or produced. This is a distribution assessment, not a general legal opinion.

The [jq binding](https://github.com/mwilliamson/jq.py) bundles/builds native jq and
Oniguruma. Complete binary provenance/notices for those components and RE2 wheel
internals remain NOT VERIFIED for any future bundled installer. This task installs
upstream wheels locally; it does not vendor those binaries in SigDoctor artifacts.

## Rules and research

[SigmaHQ rules](https://github.com/SigmaHQ/sigma) use Detection Rule License 1.1.
The feasibility document links to 12 inspected rules at a fixed commit and records
our analysis. No upstream rules are copied into the package or fixtures. The
example and test event XML are self-authored. No real event payload is included.
Microsoft/Sigma documentation is referenced, not bundled.

Development tools are separate from runtime: pytest, ruff, mypy, build and
setuptools (MIT), with dependencies pinned in requirements-dev.lock. Their
environment is not shipped in the SigDoctor wheel. The official pure-Python
mypy wheel is selected explicitly because the native wheel hit Windows
application-control policy on the development host; no security policy was changed.
