# First PowerShell slice

The approved brief is `SIGDOCTOR_CODEX_PROMPT.md`; feasibility narrows the first
iteration to native Windows PowerShell 5.1 ScriptBlockText. Python >=3.11,<4,
src-layout package, argparse CLI, pySigma behind an adapter, one bundled JSON
telemetry profile (human-readable, standard library loading). No web service,
rule execution, remediation, network operations or extra commands.

## Contracts and ownership

`load_rule(Path) -> RuleRequirements` safely bounds input, validates with pySigma,
forces condition parsing and derives fields from active condition leaves.
The domain model contains ID/title/logsource/definition, active fields, display
fields, tags/MITRE IDs, explicit event IDs, input SHA-256, and unresolved reasons.
Third-party objects never leave the adapter. DIRECT means a rule assertion;
DERIVED means a profile assertion; neither is host evidence.

`load_profile() -> TelemetryProfile` loads the single validated internal profile.
It specifies logsource, provider/channel/event, field mapping, capabilities,
references and limits. No user-supplied profiles or plugin system.

`WindowsProbe.collect() -> tuple[Evidence, ...]` reads machine registry policy
and uses fixed `wevtutil` argument arrays to get XML channel configuration and
the newest matching event within 24 hours. Probe dependencies are injectable.
Evidence records capability, state, source, observation time, bounded safe
details and error code. Missing registry policy is UNKNOWN, never DISABLED.
HKCU-only policy cannot establish host-wide logging. HKLM 64-bit view is explicit.
Only an explicit DWORD 0/1 establishes the machine policy state.

Only `evaluate(rule, profile, evidence) -> Assessment` determines final readiness.
`check_rule` orchestrates those steps. Terminal and JSON render the same result;
neither reclassifies it. JSON has `schema_version: "1"`, rule, requirements,
evidence, scope, limitations and result with status/reasons. Errors have stable
codes and sanitized messages, never raw YAML/event bodies or traceback by default.

## Supported semantics and decisions

Supported source: product windows with category ps_script and no service, or
service powershell with explicit 4104 and no conflicting category. It means a
Windows PowerShell 5.1 assessment, never all installed PowerShell providers.
Only the default `sigma` taxonomy, absent or explicit, is supported. Other
taxonomies return UNKNOWN before probing because they can redefine field names,
values and logsource names; no taxonomy transformation is performed.
Native ScriptBlockText string predicates, AND/OR/NOT on that field, normal string
wildcards and contains/startswith/endswith/all are sufficient. Explicit EventID
is supported only as positive equality to 4104 in a conjunction; ambiguous event
branches/negation and non-native/custom fields give UNKNOWN. Top-level fields
do not become requirements. Unsupported transformations, field references,
unbound keyword searches and null/exists semantics give UNKNOWN.

Modifier keys are checked before pySigma constructs a rule, because construction
can eagerly expand values. Known unsupported modifiers (including in unused
selectors) return UNKNOWN with an explicit incomplete-validation note. Unknown
modifier names are input errors. Allowed modifier chains have at most four items.
No safety decision relies on pySigma condition-tree parent pointers.

| Evidence / support | Decision |
|---|---|
| Unsupported rule semantics/source or host platform | UNKNOWN; do not probe unrelated sources |
| Required full-logging policy or channel explicitly disabled | BLIND, for the scoped provider only |
| Core policy or channel unknown/error | UNKNOWN, regardless of historical events |
| Policy and channel enabled; recent plaintext field observed | READY within stated scope |
| Policy/channel enabled; no recent event, field unresolved, encryption, or observation failure | PARTIAL |

BLIND describes absence of a required comprehensive logging capability, not a
claim that no 4104 event can ever occur. Suspicious-script automatic logging and
other providers do not establish full logging. Historical evidence cannot repair
disabled current configuration. Encrypted content cannot establish plaintext
field availability. A missing/empty field in one sample is unresolved, not proof
of permanent absence. Duplicate contradictory observations must not become READY.

## Safety and time

One UTF-8 YAML document, <=256 KiB, bounded nodes/depth/condition complexity;
reject aliases, explicit tags, duplicate keys and non-regular/remote input paths.
Reject lexical UNC/device syntax and mapped drives before file access; inspect
ancestors from the root to reject symlinks/reparse points without resolving them.
Never execute rule values or fetch references. Probe commands have fixed targets,
10-second timeout, XML output and one-event bound; parsing is size-bounded.
Only metadata/field presence survives event parsing. No payloads are printed,
persisted or sent. All timestamps UTC. A snapshot is not an atomic Windows
transaction: concurrent changes, cached policies in existing processes, event
fragmentation/reassembly, protected logging and tampering are stated limits.

## Errors, exits and tests

Exit 0: assessment completed (including BLIND/UNKNOWN). Exit 2: invalid input or
CLI usage. Exit 1: tool/internal/profile failure. Permission errors and probe
timeouts are structured evidence, not crashes. Unsupported Linux rules produce
an UNKNOWN assessment. No special CI status codes in this iteration.

Test the brief's A–E scenarios through rule → adapter → profile → injected host
evidence → evaluator → terminal/JSON, plus fail-closed conditions, unused
selectors, malformed YAML, permissions, stale/foreign/encrypted events, bounded
parsing and subprocess safety. Windows integration is opt-in and read-only;
record observed outcomes without altering policies or fabricating readiness.
