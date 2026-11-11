# Code execution sandboxes — capability research

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

**Currency:** researched 2026-11-10 against official documentation. Sandbox
vendors reprice and rename quarterly (Deno Subhosting v1 shuts down
2026-07-20; Cloudflare's SDK moved from 0.x to 1.0; OpenAI moved containers to
per-20-minute-session billing on 2026-03-31). Items marked *unverified* rest
on third-party sources or pages not re-read on the read date.

Two unrelated things share the name:

1. **Provider-side code interpreters** that run *inside* a chat turn — a chat
   concern; they are `PartServerToolCall(kind="code_execution")` parts.
2. **Standalone sandboxes** that an agent runtime drives to execute tools —
   infrastructure for the platform tier, not a kernel capability.

## 1. Provider-side code interpreters (chat parts)

### 1.1 Exact payload shapes

**OpenAI Responses — `code_interpreter`.** Tool
`{"type":"code_interpreter","container":{"type":"auto","file_ids":[…],
"memory_limit":"1g|4g|16g|64g"}}` or `"container":"cntr_…"` (explicit).
Containers are created via `POST /v1/containers {name, memory_limit}`, expire
after 20 minutes idle (cannot be revived), and have a files sub-API (multipart
upload or `{file_id}`; list; download bytes). Output item
`code_interpreter_call {id, status, container_id, code, outputs[]}` — the
`outputs[]` element types (`logs`, `image`) come from the API reference and
were not re-read (*unverified*). Generated files surface on the message as
`annotations[] {type: container_file_citation, container_id, file_id,
filename, start_index, end_index}`. Python only; no network stated; 100 RPM
per org. Price: per container session (20 minutes) by memory tier — 1 GB
$0.03, 4 GB $0.12, 16 GB $0.48, 64 GB $1.92 (*unverified*; third-party).

**Anthropic Messages — `code_execution`.** Tool versions
`code_execution_20250522` (Python only, legacy), `code_execution_20250825`
(Bash + file ops), `code_execution_20260120` (adds REPL state persistence and
programmatic tool calling), `code_execution_20260521` (same runtime; 90-second
per-cell budget surfaced to the model). Request may carry a top-level
`container` id to reuse state; inputs reference Files API uploads with a
`{"type":"container_upload","file_id"}` content block. Response:
`server_tool_use {id, name: bash_code_execution, input {command}}` →
`bash_code_execution_tool_result {tool_use_id, content {type:
bash_code_execution_result, stdout, stderr, return_code, content[] {type:
code_execution_output, file_id}}}`; `server_tool_use {name:
text_editor_code_execution, input {command: view|create|str_replace, path, …}}`
→ `text_editor_code_execution_tool_result` with `*_view_result {file_type,
content, num_lines, start_line, total_lines}`, `*_create_result
{is_file_update}`, `*_str_replace_result {old_start, old_lines, new_start,
new_lines, lines}`. Errors arrive in-band as
`bash_code_execution_tool_result_error {error_code}` (`unavailable`,
`code_execution_exceeded`, `container_expired`, `too_many_requests`,
`execution_time_exceeded`, `invalid_tool_input` — list from the page, not all
re-read). The response carries a top-level `container {id, expires_at}`.
Files left in `$OUTPUT_DIR` are captured as `file_id`s and downloaded via the
Files API. The container has **no internet access**; container data is
retained up to 30 days (not ZDR-eligible). Code execution is free when the
request also uses `web_search_20260209`/`web_fetch_20260209` or later;
otherwise billed per container-hour after a free allowance (≈ $0.05/hour
after 1,550 hours, 5-minute minimum — *unverified*, third-party).

**Gemini — `code_execution`.** `generateContent`: `tools:
[{"codeExecution": {}}]`; parts `executableCode {language, code}` and
`codeExecutionResult {outcome, output}` (outcome enum `OUTCOME_OK |
OUTCOME_FAILED | OUTCOME_DEADLINE_EXCEEDED` — *unverified* on the read date).
Interactions API: `tools: [{"type":"code_execution"}]`, steps
`code_execution_call {arguments.code}` and `code_execution_result {result}`.
Python only; 30-second runtime cap; up to 5 self-retries; fixed library set
(numpy, pandas, matplotlib, scipy, scikit-learn, opencv, pillow, sympy, …);
no custom installs; graphs come back as inline images; no extra charge —
generated code and results are billed as output tokens then re-billed as
input on the next pass.

**xAI** — `code_execution` / `code_interpreter` server tool, $5 / 1,000 calls
(`code_interpreter` not in the gRPC SDK); payload shape not re-read.

### 1.2 Mapping onto the chat IR

- `PartServerToolCall(kind="code_execution", call_id, status, payload)` with
  `payload` byte-faithful: OpenAI `{code, container_id}`, Anthropic
  `{name, input}`, Gemini `{language, code}`. Sub-tools (Anthropic
  `bash_code_execution` vs `text_editor_code_execution`) stay in `payload`,
  not in `kind` — `kind` is the industry-level family, the native tool name is
  the provider lane.
- `PartServerToolResult(call_id, is_error, payload)` where the payload keeps
  `stdout/stderr/return_code` (Anthropic), `outputs[]` (OpenAI) or
  `{outcome, output}` (Gemini) verbatim. A **non-normative convenience view**
  `ExecOutcome(stdout, stderr, exit_code, files[])` can be derived on read
  with declared `APPROXIMATED` for Gemini (single `output`, no exit code) —
  never baked into the part.
- Output files are `SourceRef`s (OpenAI container file ids, Anthropic
  `file_id`s) scoped to `(provider, interface)`; Gemini inline images are
  `PartImage` with a base64 `Source`.
- Container handles (`cntr_…`, Anthropic `container.id` + `expires_at`) are
  `ProviderRef(kind="container")` anchors on `ResponseInfo`; replaying them
  across providers is `UNSUPPORTED`-and-reported.
- In-band errors are `PartServerToolResult(is_error=True)` with the canonical
  code (`TransientError`-class for `unavailable`, `RateLimitError` for
  `too_many_requests`, a new open `execution_timeout` code for
  `execution_time_exceeded`/`OUTCOME_DEADLINE_EXCEEDED`) plus `native`.
- Usage: an open-code `container_seconds`/`sessions` dimension so OpenAI
  per-session and Anthropic per-hour billing land on the ledger without
  pretending to be tokens.
- Fixtures needed: one fold triple per interface (OpenAI
  `response.code_interpreter_call_code.delta/done` events — names
  *unverified*; Anthropic `content_block_start` of
  `bash_code_execution_tool_result`; Gemini `executableCode` part followed by
  `codeExecutionResult`).

## 2. Standalone sandboxes

### 2.1 Per-vendor lifecycle

- **E2B** — `Sandbox.create()` (Python `from e2b import Sandbox`; code
  interpreter variant `e2b_code_interpreter` adds `run_code()` with
  persistent state and rich outputs), `sandbox.commands.run(cmd)` →
  `stdout/stderr/exit_code`, `sandbox.files.*`, PTY, `kill()`, pause/resume
  (filesystem + memory snapshot kept indefinitely until killed). Templates
  define the start image. Internet on by default. Plans: Hobby $0 with a
  one-time $100 credit, 10 concurrent, 1-hour max session; Pro $150/month,
  100 concurrent (add-ons to 1,100), 24-hour max session; usage
  $0.000014 per vCPU-second and $0.0000045 per GiB-second; 1–8 vCPU, 1–8 GiB,
  default 2 vCPU / 4 GiB; CPU only.
- **Modal Sandboxes** — `modal.Sandbox.create(app=…, image=…, timeout, cpu,
  memory, volumes, secrets, runtime="gvisor"|"vm", readiness_probe, name,
  workdir)`; `sb.exec(*argv, timeout)` → process with `stdout`, `stderr`,
  `returncode`, `poll()`; `terminate()` (SIGKILL, 137); default max lifetime
  5 minutes, raisable to 24 hours; `idle_timeout`; filesystem snapshots to
  reusable images; GPU on gVisor only; billed `max(request, actual)` per
  second (≈ $0.00003942 per physical core-second — *unverified*).
- **Daytona** — `daytona.create(CreateSandboxFromSnapshotParams(snapshot, …))`
  or from an image (tag/digest required), `Resources(cpu, memory, disk)`
  (default 1 vCPU / 1 GB / 3 GiB; org cap 4 / 8 / 10), `env_vars`, labels,
  ephemeral flag; `sandbox.process.code_run(code)`, `process.exec`,
  sessions; `fs` upload/download; git; LSP; preview links; REST
  `POST https://app.daytona.io/api/sandbox` with bearer. Regions `us`, `eu`
  (`earth` for GPU). "<90 ms" start claim. Pricing not on the page.
- **Vercel Sandbox** — Firecracker microVMs, GA; JS `@vercel/sandbox` and
  Python `vercel.sandbox` SDKs plus a `sandbox` CLI; default image
  `vercel/sandbox/universal` (Node LTS, Python 3.14, coding agents) or custom
  OCI images from Vercel Container Registry; persistent sandboxes (auto-save
  on stop) and snapshots; Secure Compute for static egress; "Active CPU"
  billing — idle CPU is nearly free, provisioned memory is billed (1 vCPU /
  2 GB in `iad1` ≈ $1.05/day idle, $4.09/day busy). Method signatures
  (`runCommand`, `writeFiles`, `domain(port)`) not re-read (*unverified*).
- **Cloudflare Sandbox SDK / Containers** — `@cloudflare/sandbox` (0.x
  documented; 1.0 is current) on Durable Objects + Containers (microVM per
  instance, own kernel and network; HTTP only via your Worker). Reference
  sections: lifecycle, commands with streaming, files, inotify watching,
  code interpreter (Python/JavaScript), ports/preview URLs,
  `sandbox.tunnels.get(port)` (`*.trycloudflare.com`), S3-compatible storage
  mounts, R2 backups, sessions, browser terminal. Requires Workers Paid;
  per-second vCPU/memory/disk billing (rates not re-read). Dynamic Workers
  (`env.LOADER.load`, `globalOutbound: null`) are the isolate-level tier.
- **Fly Machines** — REST `POST /v1/apps/{app}/machines {config {image,
  guest {cpu_kind, cpus, memory_mb, gpu_kind, size}, env, services,
  auto_destroy, restart {policy, max_retries}, mounts, files {guest_path,
  raw_value|secret_name}, init {exec, cmd, entrypoint, tty, swap_size_mb}},
  region, lease_ttl, skip_launch}`; `POST …/{id}/start|stop|suspend`,
  `GET …/{id}/wait?state=…&timeout=`, `DELETE …/{id}?force`; exec endpoint
  exists but was not on the read-date page (*unverified*); one volume per
  machine; suspend snapshots memory; billed per second while started plus
  rootfs/volumes.
- **Deno Sandbox** (replaces Subhosting; v1 API shuts down 2026-07-20) —
  `@deno/sandbox` (JSR/npm) and `deno-sandbox` (PyPI); `Sandbox.create({
  region: ams|ord, memory, allowNet: […], secrets, lifetime})`,
  ``sandbox.sh`…` `` / `spawn`, `await using` or `close()`; Linux microVM,
  2 vCPU, 768–4096 MB (1.2 GB default), 10 GB ephemeral disk, lifetime up to
  30 minutes, 5 concurrent per org by default; outbound network
  allowlist-only; secrets injected only on approved egress; volumes for
  durability; launch-blog pricing $0.05 per CPU-hour, $0.016 per GiB-hour,
  $0.20 per GiB-month (*unverified*; third-party figures differ).
- **Docker-based local** — the in-process/local peer: `docker run --rm
  --network none --memory … --cpus … -v …` plus `docker exec`; no wire
  dialect, same port. Reference implementation target for conformance.
- **WebAssembly runtimes** — *Pyodide* 314.x: CPython on WebAssembly for
  browser/Node (`loadPyodide`, `runPython`, `runPythonAsync`, package loading
  via micropip); main-thread blocking unless in a Worker; networking only via
  the host's `fetch`. *Wasmtime*: standalone runtime for Wasm, WASI and the
  Component Model (Bytecode Alliance), embeddable from Rust/C/Python/Go/.NET,
  capability-based (no ambient filesystem/network), configurable CPU/memory
  limits via fuel/epochs and `ResourceLimiter` (API names *unverified*).

### 2.2 Comparison

| Vendor | Create | Exec result | Files | Timeout / lifetime | Network | Persistence | Billing |
|---|---|---|---|---|---|---|---|
| E2B | SDK `Sandbox.create` (templates) | `stdout, stderr, exit_code`; `run_code` rich outputs | `files.*`, PTY | 1 h (Hobby) / 24 h (Pro) | on by default | pause/resume incl. memory | vCPU-s + GiB-s + plan |
| Modal | `Sandbox.create(image, …)` | process `stdout/stderr/returncode` | volumes, fs snapshots | 5 min default, ≤ 24 h, `idle_timeout` | configurable (`block_network` *unverified*) | filesystem snapshots | per-second `max(request, actual)` |
| Daytona | `daytona.create(snapshot|image)` | `code_run`, `exec`, sessions | `fs.*`, git, LSP | auto-stop/archive intervals | yes; preview links | archive / snapshots | per vCPU-h, GiB-h, disk (*unverified*) |
| Vercel | SDK/CLI, images from VCR | `runCommand` (*unverified*) | write/read, Drives, S3 FUSE | session timeout; persistent by default | yes; Secure Compute | auto-save, snapshots | Active CPU + provisioned memory |
| Cloudflare | `getSandbox` (DO) | exec with streaming | files, inotify, R2 backup | `sleepAfter` | via Worker; egress billed | backups | vCPU-s, GiB-s, disk (Workers Paid) |
| Fly Machines | REST create | exec endpoint (*unverified*) | volumes (1 per machine) | until stop; suspend | yes | volumes, suspend snapshot | per-second while started |
| Deno Sandbox | `Sandbox.create` | `sh`/`spawn` | volumes | ≤ 30 min | allowlist only | volumes | CPU-h + GiB-h (*unverified*) |
| Docker local | `docker run` | `docker exec` | bind mounts | host policy | `--network none` | volumes | none |
| Pyodide / Wasmtime | in-process | return value / traps | virtual FS / preopens | fuel/epochs | host-mediated | none | none |

## 3. Canonical proposal — a platform execution port, not a kernel capability

**Litmus reasoning.** §11 admits a capability when an *AI* operation has
provider-varying *wire dialects* whose conversion loses something worth
reporting. Sandboxes fail both halves: "run this command with this stdin and
return stdout/stderr/exit code" has no semantic variance to census (every
vendor returns the same triple), and the differences are infrastructure
(lifecycle, billing, networking), not meaning. A `FidelityReport` for
`docker exec` → `sb.exec` would be empty by construction. They are
therefore **built ON ocai**: the platform's agent runtime and tool registries
own them, the kernel contributes substrate (`CallResult`, `CallContext`,
`Consumption`, `ProviderRef`) so executions are still ledgered and
attributable. The provider-side interpreters are the opposite case: they live
inside a chat response, vary per interface, and lose information in
conversion — they are chat parts (section 1), already provided for by
`PartServerToolCall`.

**Minimal execution-port contract the platform needs** (so tool execution is
pluggable across local Docker, E2B, Modal, Daytona, Vercel, Cloudflare, Fly,
Deno, Wasm):

```python
class SandboxPort(Protocol):
    def create(self, spec: SandboxSpec, *, ctx: CallContext | None = None) -> CallResult[SandboxHandle]: ...
    def exec(self, handle: SandboxHandle, req: ExecRequest, *, ctx=None) -> CallResult[ExecResult]: ...
    def put_file(self, handle, path: str, source: Source, *, ctx=None) -> CallResult[FileRef]: ...
    def get_file(self, handle, path: str, *, ctx=None) -> CallResult[Source]: ...
    def destroy(self, handle, *, ctx=None) -> CallResult[None]: ...
    # optional, profile-gated: snapshot/restore, expose_port, stream_exec
```

- `SandboxSpec(image | template, cpu, memory_mb, disk_mb, network:
  none|allowlist|open, allowlist[], env, secrets (explicit `ApiKey`-style,
  applied at the leaf), timeout_s, idle_timeout_s, workdir)`.
- `ExecRequest(argv | shell | code+language, stdin, env, cwd, timeout_s,
  max_output_bytes)`; `ExecResult(stdout, stderr, exit_code, duration_ms,
  truncated, timed_out, files_out[]: FileRef)`.
- `SandboxHandle` is a `ProviderRef(kind="sandbox")` (vendor id + region +
  expiry); `FileRef` a `SourceRef`. Both honour the scoped-crossing rule.
- `Consumption` dimensions `cpu_seconds`, `memory_gib_seconds`, `sessions`
  (open codes) so E2B, Modal, Vercel and OpenAI containers share one ledger
  axis without rescaling.
- Errors through the shared taxonomy: quota/concurrency → `RateLimitError`,
  vendor 5xx → `TransientError`, timeouts → `execution_timeout` (new open
  code), image/template not found → `InvalidRequestError`.
- Async-twin methods (`acreate`, `aexec`, …) per the port convention; the
  Docker adapter is the conformance reference, since it has no wire.

## 4. Priority

- **P0 (kernel, chat):** golden fixtures and censuses for `code_interpreter_call`,
  `bash_code_execution_tool_result`/`text_editor_code_execution_tool_result`,
  and `executableCode`/`codeExecutionResult`, with fold triples. Without them
  the `/responses` migration proof silently drops interpreter output.
- **P2 (platform):** the `SandboxPort` above, Docker-local first, E2B second
  (cleanest SDK, explicit per-second rates), Modal third (snapshots, GPU).
  Effort M; no spec/ schema (not a capability), but a conformance suite for
  the port semantics (exit-code fidelity, truncation flags, timeout
  reporting).
- **P3:** Wasm in-process runners (Pyodide/Wasmtime) as zero-infrastructure
  peers for pure-Python tools.

## 5. Unverified / open

- OpenAI `code_interpreter_call.outputs[]` element shapes, streaming event
  names, and per-session prices; Anthropic container-hour price and free
  allowance; Gemini `outcome` enum values.
- Modal `block_network`/`cidr_allowlist` and per-second rate; Vercel SDK
  method names and limits; Cloudflare 1.0 API names and rates; Fly `exec`
  endpoint shape; Deno Sandbox current pricing; Wasmtime limiter API names.

## Sources (read 2026-11-10)

- https://developers.openai.com/api/docs/guides/tools-code-interpreter
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool
- https://aistudio.google.com/docs/code-execution
- https://aistudio.google.com/api-reference/generate-content
- https://docs.x.ai/developers/pricing
- https://docs.e2b.dev/
- https://e2b.dev/pricing
- https://modal.com/docs/guide/sandbox
- https://www.daytona.io/docs/en/getting-started/
- https://vercel.com/docs/vercel-sandbox
- https://developers.cloudflare.com/sandbox/
- https://developers.cloudflare.com/sandbox/api/
- https://docs.fly.io/machines/api/machines-resource
- https://docs.deno.com/subhosting/manual/
- https://docs.deno.com/sandbox/
- https://deno.com/blog/introducing-deno-sandbox
- https://pyodide.org/en/stable/usage/index.html
- https://docs.wasmtime.dev/introduction.html
