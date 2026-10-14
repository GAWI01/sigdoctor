# SigDoctor feasibility — 2026-10-14

Follow-up: controlled real Windows A/B/C/D1/D2 CLI scenarios subsequently matched
the expected readiness statuses on a disposable Windows Server 2025 host.
See [Windows validation](WINDOWS_VALIDATION.md) for independent evidence,
rollback and limits. The original conclusion remains a deliberately narrow
scope; these experiments do not establish end-to-end detection effectiveness.

## Hypothesis and inspection

A supported Sigma rule can be mapped to concrete telemetry requirements and
compared with local Windows evidence without implying that an attack will be
detected. This is a feasibility assessment, not validation of detection efficacy.

Starting repository: `57e21c6` (`main`), README, Python ignore file, MIT license.
The initial local repository had no commits, files, or remote; fetched that public
repository and created `codex/powershell-slice`. No user changes were overwritten.
No AGENTS.md was found in the checkout or its ancestor directories. The two
provided briefs are preserved at the repository root. No push or release occurred.

## Sources and important limits

Sources inspected on 2026-10-14:

* [Sigma specification 2.1.0](https://github.com/SigmaHQ/sigma-specification/blob/main/specification/sigma-rules-specification.md):
  detection predicates and conditions determine inputs; top-level `fields` is a
  display suggestion, not a detection prerequisite. A condition can contain
  alternatives, negation, or unused selectors. Taking every field as universally
  mandatory can produce false BLIND results. Tags are labels, not host evidence.
* [Sigma logsource documentation](https://sigmahq.io/docs/basics/log-sources.html):
  product/category/service jointly identify the source; definition is free-form
  onboarding guidance. It must not be executed or treated as a machine-checkable
  policy. Backend field transformations remain outside a local-host assessment.
* [pySigma source](https://github.com/SigmaHQ/pySigma/tree/54e4077532d1ae654ed565b5a61b75e76e8f725a)
  and [PyPI metadata](https://pypi.org/pypi/pysigma/2.0.1/json): current 2.0.1 requires
  Python >=3.11,<4 and is LGPL-2.1-only. `SigmaRule.from_dict` and the resolved
  `SigmaCondition.parsed` tree provide a suitable adapter boundary. Condition
  parsing is lazy and must explicitly be forced. Dependency footprint is larger
  than a YAML loader, but replacing Sigma parsing would create a worse maintenance
  burden. Keep the library replaceable and unmodified; do not vendor it.
* [Microsoft Windows PowerShell logging](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_logging?view=powershell-5.1):
  Windows PowerShell uses Microsoft-Windows-PowerShell/Operational, event 4104.
  HKLM ScriptBlockLogging policy enables comprehensive logging for new sessions.
  Protected Event Logging can encrypt the content. Existing sessions, historical
  events and policy changes prevent an unconditional guarantee.
* [PowerShell 7 logging](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_logging_windows?view=powershell-7.6):
  different PowerShellCore provider, policy and configuration files. Do not infer
  its readiness from the Windows PowerShell channel.
* [Sigma ps_script guide](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/documentation/logsource-guides/windows/category/ps_script.md):
  confirms both providers. Its field-section headings say 4103 despite identifying
  4104 above; use Microsoft/provider evidence rather than copying that heading.
* [4688](https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-4688)
  and [Audit Process Creation](https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/audit-process-creation):
  process auditing and command-line inclusion are separate prerequisites.
* [4624](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4624),
  [4625](https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-4625),
  [Audit Logon](https://learn.microsoft.com/windows/security/threat-protection/auditing/audit-logon):
  success/failure settings, event version and machine role matter; a channel alone
  cannot establish the needed event/field availability.
* [Sysmon](https://learn.microsoft.com/sysinternals/downloads/sysmon): event 1 is a
  process source with richer fields, but installation does not establish filter
  coverage. Do not equate it with Security 4688.
* [wevtutil](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/wevtutil):
  supports structured XML channel queries and bounded event queries. This avoids
  localized display text and commands assembled from rule input.

## Representative rule study

Inspected 12 rules at SigmaHQ/sigma commit
`7d8b152a5fc062ebd309f62ae4d8276aca2786af`. This is a purposive sample across the
proposed families and counterexamples, not an estimate of overall rule coverage.
No upstream rules are bundled. Test fixtures must be independently authored.

In the table, **P** means a shared ps_script profile deriving Windows PowerShell
4104, Script Block Logging, channel state and plaintext ScriptBlockText; **E**
means local HKLM policy, channel XML and a recent 4104 field observation. For each
P row the provider is a declared assessment scope, not something the abstract
category uniquely proves. Even a READY answer excludes backend translation,
forwarding, fragment reassembly, tampering and detection efficacy.

| Rule | Direct facts and apparent needs | Generic derivation / knowledge needed | Unsafe inference / verification / honest classification |
|---|---|---|---|
| [AADInternals cmdlets](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/powershell/powershell_script/posh_ps_aadinternals_cmdlets_execution.yml) | windows/ps_script; ScriptBlockText contains alternatives | Extract active field; P | Cannot infer execution or capture of every invocation. E permits scoped READY; missing E remains unresolved. |
| [Browser login data](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/powershell/powershell_script/posh_ps_access_to_browser_login_data.yml) | ScriptBlockText; all-of selectors and contains/all | Resolve selectors, same field; P | No need to inspect browser files. E verifies telemetry only, not whether both strings survive fragmentation. |
| [AD module import](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/powershell/powershell_script/posh_ps_active_directory_module_dll_import.yml) | OR of selectors on ScriptBlockText | Both branches share field; P | Do not infer AD module installation. E can establish the scoped capability. |
| [AMSI pattern](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/powershell/powershell_script/posh_ps_amsi_bypass_pattern_nov22.yml) | One ScriptBlockText contains/all selection | P, not rule-specific hardcoding | Logging does not prove resistance to bypass. E supports capability assessment only. |
| [Clear history](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/powershell/powershell_script/posh_ps_clear_powershell_history.yml) | Mixed wildcard selectors/AND/OR; ScriptBlockText | Resolved AST still uses one field; P | History settings are not logging evidence. E supports scoped classification without interpreting script contents. |
| [Screen capture](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/powershell/powershell_script/posh_ps_capture_screenshots.yml) | ScriptBlockText contains one string | P | No screenshot/access probe required. E sufficient for scoped telemetry status, not capture effectiveness. |
| [7-Zip compression](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/process_creation/proc_creation_win_7zip_password_compression.yml) | process_creation; alternative Image/Description/OriginalFileName plus CommandLine | Generic AST fields; provider/branch-specific profile needed | Union is not mandatory field set. 4688 policy + command-line setting or Sysmon filtering/fields needed. UNKNOWN in first slice. |
| [AddinUtil child](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/process_creation/proc_creation_win_addinutil_uncommon_child_process.yml) | ParentImage and negated Image filter | Parent/child mapping and filter semantics | Event presence alone insufficient. Need provider/version and actual parent fields. UNKNOWN in first slice. |
| [New credentials](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/builtin/security/account_management/win_security_susp_logon_newcredentials.yml) | security; EventID 4624; LogonType 9 | Event-to-audit profile, success policy | Cannot infer all logon types from one sample. Policy and local event evidence needed. UNKNOWN in first slice. |
| [Failed logon reasons](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/builtin/security/win_security_susp_failed_logon_reasons.yml) | 4625 OR 4776; Status/SubStatus; negative SID filter | Alternative event schemas, audit categories and roles | 4625 alone cannot prove both branches. Needs failure audit and credential-validation mapping. UNKNOWN. |
| [Anonymous account](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/builtin/security/win_security_susp_local_anon_logon_created.yml) | security; 4720; SamAccountName | Account management, not logon | A filename containing logon must not select a 4624 profile. Appropriate audit subcategory/fields needed. UNKNOWN. |
| [Sysmon configuration](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/rules/windows/sysmon/sysmon_config_modification.yml) | sysmon; EventID 16 | Distinct Sysmon event profile | Sysmon Event 1 or installation cannot prove configuration-event availability. Service/channel/event evidence needed. UNKNOWN. |

## Competing approaches

1. [WELA](https://github.com/Yamato-Security/WELA/tree/0d4f45480f43e3bd0964dd9371ce5e16a60f5c37)
   audits/configures Windows logging, offers baseline and Sigma coverage outputs,
   and expects administrative privileges. Inspected README and command source.
   It is a strong existing choice for broad logging audits. SigDoctor should not
   recreate its baseline reporting or configuration features.
2. [SigmaHQ logsource checker](https://github.com/SigmaHQ/sigma/blob/7d8b152a5fc062ebd309f62ae4d8276aca2786af/documentation/tools/sigma-logsource-checker.py)
   is directly rule-first: accepts rule folders, extracts fields/event IDs, and
   optionally compares gpresult XML. Its PowerShell path uses policy settings;
   inspected code does not verify recent local 4104 plaintext fields or live
   channel state. This invalidates a claim that rule-first mapping itself is new.
3. [Rustinel Sigma support](https://docs.rustinel.io/sigma/) and
   [limitations](https://docs.rustinel.io/limitations/) describe an endpoint
   detection engine with doctor diagnostics and inert-rule counts. Relevant prior
   art, but adopting an agent/execution engine conflicts with this CLI boundary.

A static prerequisite explainer is cheap but mostly duplicates SigmaHQ's tool.
A general multi-provider host readiness engine demands branch-aware field maps,
normalization knowledge and substantially more validation. Choose the middle:
one local, read-only, evidence-bearing PowerShell capability assessment.
Competitors were inspected, not installed or benchmarked; user value and demand
remain NOT VERIFIED. No claim that this search exhausts all competitors.

## Kill criteria assessment

1. Rule-specific hardcoding: not necessary for the six sampled ps_script rules;
   one field/profile mapping serves them. Broader rules would need more knowledge.
2. Backend separation: possible for native plaintext ScriptBlockText capability;
   impossible to infer end-to-end detection/normalization. Narrow the promise.
3. Existing tool substantially better at the same workflow: not established for
   the bounded live evidence workflow; strong overlap blocks novelty claims.
4. False confidence: material risk. Fail closed on unsupported fields, provider
   ambiguity, missing core evidence, encrypted content and malformed data.
5. New detection framework: avoid by assessing capability, not matching rules or
   implementing Sigma execution, provider alternatives or rule-by-rule patches.
6. Windows testability: this environment is Windows with Python 3.13. Read-only
   probes are testable here. Controlled enabled/disabled/denied hosts still need
   separate validation; fakes are not real-host proof.
7. Backend specificity: the selected native provider permits a bounded contract;
   anything involving normalized SIEM fields is UNKNOWN.

## Decision

Proceed only with a prototype for Windows PowerShell 5.1 / native 4104
ScriptBlockText. A result must name that scope, including on BLIND. PowerShell 7,
arbitrary fields, event alternatives, process creation and authentication are
not implemented. READY requires configured logging, an enabled channel and a
recent usable field observation; no event is not proof of disabled logging.
Only this small hypothesis passes; general Windows Sigma readiness does not.
Do not expand without controlled real-host validation and evidence of user value.

PROCEED WITH NARROWER SCOPE
