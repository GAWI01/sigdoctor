# Security boundary

SigDoctor is a local, read-only CLI prototype. It never enables logging, writes
registry/policy settings, installs services, runs detection payloads, downloads
rules, fetches rule references or uploads telemetry. Host observations can still
be wrong on a compromised host; this is not an attestation or anti-tamper tool.

Only a bounded UTF-8 local regular file is accepted. YAML tags, aliases, duplicate
keys, large/deep inputs and overly complex conditions are rejected. Known
unsupported modifiers are declined before pySigma can expand them. Such an
UNKNOWN result does not certify Sigma validity. Rule content never becomes a
subprocess command. Fixed system `wevtutil` commands use shell=False, a ten-second
timeout, XML output and at most one event. Output parsing is capped at 2 MiB.
The subprocess captures stdout/stderr in memory; the fixed one-event query bounds
normal event output. A compromised executable is outside the trust boundary.

UNC/device paths, mapped network drives and reparse points are rejected before
following them. Ordinary local paths are required. This does not defend against
a privileged adversary racing filesystem replacements during the check.

Raw event XML exists briefly in process memory. Script text, paths, identities
and event payloads are never persisted or emitted. The output contains the user
supplied rule metadata (including definition), policy value, capability states,
timestamps and error codes. Treat reports as operational information. Redirected
output is retained wherever the user chooses; SigDoctor has no analytics or
server-side retention. OS and security software may independently log execution.

To report a vulnerability, use this repository's GitHub private vulnerability
reporting feature if enabled. Otherwise open an issue requesting a private
contact route, without exploit payloads, credentials, event contents or personal
data. Private reporting availability has not been verified in this iteration.

Before wider release, validate controlled Windows enabled, disabled, protected,
permission-denied and policy-change scenarios. Do not automatically change a
user's logging configuration to perform tests.
