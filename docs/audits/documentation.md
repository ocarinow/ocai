# Documentation audit — 2026-11-11

Baseline: main `7dc0e06` (release following the CI-latency and EventStream changes).
This is an audit of repository documentation against that code revision, not a
new live-vendor certification. Concurrent public-library implementations are not
claimed as available until they are in the inspected baseline.

## Findings and corrections

| Finding | Correction | Code / verification evidence |
|---|---|---|
| Public navigation and search mixed user guides, roadmaps, ADRs, research and proposed products | Dedicated `docs/user/` publication root; contributor/design/research folders stay outside the site | `zensical.toml`, `scripts/docs_contract.py`, built output check |
| Main/Python guides described four or three packages and pending DeepSeek execution | Six distributions; qualified DeepSeek unary/streaming; independent AWS credentials and Bedrock host | `python/packages/*/pyproject.toml`, DeepSeek execution/streaming tests |
| Guides claimed packages were not on PyPI | Application installation uses published distributions; source checkout instructions remain separate | [PyPI ocai](https://pypi.org/pypi/ocai/json), [OpenAI](https://pypi.org/pypi/ocai-openai/json), [AWS](https://pypi.org/pypi/ocai-aws/json), checked 2026-11-11 |
| Feature matrix said interceptors were unary-only and observer events were not emitted | Updated qualified surface and explicit satellite boundaries | `test_stream_middleware.py`, `runtime/observe.py`, `test_gateway_qualification.py` |
| Citation/search/response-identity status predated merged WUs | Current support matrix cites owning fixtures and separates representation from qualification | Core citation/stream tests, Anthropic and DeepSeek conformance |
| Architecture summary omitted newer integrations | Updated summary; preserved detailed structural contract | Host adaptation, signing, Bedrock and EventStream tests |
| Platform design looked like executable product documentation | Proposed design moved out of site; user guide describes only status API/console and internal foundation | `platform/services/gateway/app/main.py`, management OpenAPI and console pages |
| API signatures and endpoint documentation were incomplete/manual | Source-parsed reference for public modules, signatures, declared fields/methods and re-exports; schema-derived HTTP reference | `scripts/docs_reference.py --check`; no runtime import/discovery |
| Stream example exhausted then folded the same stream | Owned stream lifetime and fold-before-exhaustion examples | Recorded sync/async documentation example tests |
| ADR index still described merged implementations as awaiting review | Updated implementation status; historical rationale unchanged | Merged PRs #69, #100–101, #106, #110, #112, #114, #116, #129–130 |
| Historical plans had dead links to removed pre-rearchitecture source | Preserved paths as historical literals, not live links | Repository Markdown link contract |
| Package extras omitted DeepSeek and blurred AWS/Bedrock installation | Corrected extras descriptions and package guide links | Published package metadata; documentation-only patch changeset |

## Scope and boundaries

The inventory below accounts for owned Markdown documentation, including package
READMEs, specification documents, decisions, plans and release history. Vendored
agent skills and tool adapter pointers are outside the product-document audit;
the repository's canonical contributor instructions remain in `AGENTS.md`.

User guides and current status summaries were compared with implementation,
exports, metadata, fixtures, service routes and the OpenAPI contract. Research is
retained as explicitly dated research, not refreshed into current vendor promises.
Archived plans and changelogs preserve history. No source snapshot can guarantee
future/live model availability. The full gate checks conformance and operational
fixtures; the documentation checks add source drift, examples, publication and links.

The API generator documents declarations and named bases; it does not claim to
flatten every inherited member or turn provisional types into provider support.
Source docstrings retain literal code examples. New provider qualification must
update the support matrix and its evidence alongside code changes.

## Tracking observation

The existing board sync's newly created draft returned no content ID before its
body update, and its PR replacement behavior differs from the draft-only written
protocol. Gateway cards were generated from plan entries through the existing
board helpers, with explicit initial bodies and statuses. This audit does not
claim the generic board synchronizer is repaired; its implementation/protocol
reconciliation is recorded separately from user documentation.

## Inventory at audit completion

| Source | Audience | Review treatment |
|---|---|---|
| [.agents/roles/honesty-reviewer.md](../../.agents/roles/honesty-reviewer.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [.changeset/documentation-package-guides.md](../../.changeset/documentation-package-guides.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [.github/PULL_REQUEST_TEMPLATE.md](../../.github/PULL_REQUEST_TEMPLATE.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [AGENTS.md](../../AGENTS.md) | Contributor/operator | Commands, ownership and status reconciled |
| [CLAUDE.md](../../CLAUDE.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | Contributor/operator | Commands, ownership and status reconciled |
| [README.md](../../README.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [SECURITY.md](../../SECURITY.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [docs/README.md](../README.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [docs/architecture.md](../architecture.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [docs/audits/documentation.md](documentation.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [docs/decisions/0001-agent-neutral-repo-layout.md](../decisions/0001-agent-neutral-repo-layout.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0002-branch-protection-and-typing-gate.md](../decisions/0002-branch-protection-and-typing-gate.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0003-ordered-item-modernization.md](../decisions/0003-ordered-item-modernization.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0004-catalog-composition-and-evidence.md](../decisions/0004-catalog-composition-and-evidence.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0005-revised-freeze-gate.md](../decisions/0005-revised-freeze-gate.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0006-platform-product-layout.md](../decisions/0006-platform-product-layout.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0007-governed-execution.md](../decisions/0007-governed-execution.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0008-integration-contract-additions.md](../decisions/0008-integration-contract-additions.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0009-platform-foundation.md](../decisions/0009-platform-foundation.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0010-versioning-and-releases.md](../decisions/0010-versioning-and-releases.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0011-authenticated-console-contract.md](../decisions/0011-authenticated-console-contract.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0012-shadcn-component-layer.md](../decisions/0012-shadcn-component-layer.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0013-platform-identity.md](../decisions/0013-platform-identity.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0014-host-selected-stream-framing.md](../decisions/0014-host-selected-stream-framing.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0015-stream-response-info.md](../decisions/0015-stream-response-info.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0016-provider-authentication-packages.md](../decisions/0016-provider-authentication-packages.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0017-host-error-outcomes.md](../decisions/0017-host-error-outcomes.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0018-host-fidelity-reports.md](../decisions/0018-host-fidelity-reports.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0019-host-response-adaptation.md](../decisions/0019-host-response-adaptation.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0020-distribution-roles.md](../decisions/0020-distribution-roles.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/0021-eventstream-framing.md](../decisions/0021-eventstream-framing.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/decisions/README.md](../decisions/README.md) | Decision record | Historical rationale retained; merged status reconciled |
| [docs/design/README.md](../design/README.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/README.md](../design/platform/README.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/authoring.md](../design/platform/authoring.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/compartments.md](../design/platform/compartments.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/decisions.md](../design/platform/decisions.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/delivery.md](../design/platform/delivery.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/evidence.md](../design/platform/evidence.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/execution.md](../design/platform/execution.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/gateway.md](../design/platform/gateway.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/identity.md](../design/platform/identity.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/products.md](../design/platform/products.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/security.md](../design/platform/security.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/design/platform/stack.md](../design/platform/stack.md) | Proposed design | Proposal status explicit; excluded from user site |
| [docs/development/README.md](../development/README.md) | Contributor/operator | Commands, ownership and status reconciled |
| [docs/development/ci.md](../development/ci.md) | Contributor/operator | Commands, ownership and status reconciled |
| [docs/development/documentation.md](../development/documentation.md) | Contributor/operator | Commands, ownership and status reconciled |
| [docs/development/releasing.md](../development/releasing.md) | Contributor/operator | Commands, ownership and status reconciled |
| [docs/plans/README.md](../plans/README.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/WU-EXAMPLE.md](../plans/WU-EXAMPLE.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/WU-TEMPLATE.md](../plans/WU-TEMPLATE.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/archive/README.md](../plans/archive/README.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/archive/original-README.md](../plans/archive/original-README.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/archive/v0.1-walking-skeleton.md](../plans/archive/v0.1-walking-skeleton.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/archive/v0.2-the-wedge.md](../plans/archive/v0.2-the-wedge.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/archive/v0.3-credibility.md](../plans/archive/v0.3-credibility.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/archive/v0.4-polyglot.md](../plans/archive/v0.4-polyglot.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/archive/v1.0-hardening.md](../plans/archive/v1.0-hardening.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/archive/v1.1-honest-economics.md](../plans/archive/v1.1-honest-economics.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/archive/v1.2-retrieval-complete.md](../plans/archive/v1.2-retrieval-complete.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/archive/v1.3-generative-media.md](../plans/archive/v1.3-generative-media.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/archive/v1.4-realtime-duplex.md](../plans/archive/v1.4-realtime-duplex.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/archive/v1.5-safety-and-eval.md](../plans/archive/v1.5-safety-and-eval.md) | Historical plan | Historical paths literal; not a current support claim |
| [docs/plans/ci-latency.md](../plans/ci-latency.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/core-modernization.md](../plans/core-modernization.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/documentation.md](../plans/documentation.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/gaps.md](../plans/gaps.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/gateway-readiness.md](../plans/gateway-readiness.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/horizon.md](../plans/horizon.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/integration-program.md](../plans/integration-program.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/m1-foundations.md](../plans/m1-foundations.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/m2-streaming.md](../plans/m2-streaming.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/m3-second-provider.md](../plans/m3-second-provider.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/platform-design.md](../plans/platform-design.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/platform-gateway-parity.md](../plans/platform-gateway-parity.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/platform-gateway.md](../plans/platform-gateway.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/platform-identity.md](../plans/platform-identity.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/platform-mvp.md](../plans/platform-mvp.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/plans/wu-20-catalog-conformance.md](../plans/wu-20-catalog-conformance.md) | Delivery plan | Template/link checks; roadmap remains authoritative |
| [docs/research/README.md](../research/README.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/README.md](../research/capabilities/README.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/agent-frameworks.md](../research/capabilities/agent-frameworks.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/batch-and-jobs.md](../research/capabilities/batch-and-jobs.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/caching-cost-and-rate-limits.md](../research/capabilities/caching-cost-and-rate-limits.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/code-execution-sandboxes.md](../research/capabilities/code-execution-sandboxes.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/document-understanding.md](../research/capabilities/document-understanding.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/embeddings.md](../research/capabilities/embeddings.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/evaluation.md](../research/capabilities/evaluation.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/files-and-assets.md](../research/capabilities/files-and-assets.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/fine-tuning.md](../research/capabilities/fine-tuning.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/gateways-and-routers.md](../research/capabilities/gateways-and-routers.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/guardrails-and-pii.md](../research/capabilities/guardrails-and-pii.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/hosting-and-aggregators.md](../research/capabilities/hosting-and-aggregators.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/hybrid-and-fulltext-search.md](../research/capabilities/hybrid-and-fulltext-search.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/identity-and-secrets.md](../research/capabilities/identity-and-secrets.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/image-generation.md](../research/capabilities/image-generation.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/ingestion-chunking-and-memory.md](../research/capabilities/ingestion-chunking-and-memory.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/managed-rag-and-file-search.md](../research/capabilities/managed-rag-and-file-search.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/model-catalog.md](../research/capabilities/model-catalog.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/moderation-and-safety.md](../research/capabilities/moderation-and-safety.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/music-and-sound.md](../research/capabilities/music-and-sound.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/observability.md](../research/capabilities/observability.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/prompt-management.md](../research/capabilities/prompt-management.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/realtime-voice.md](../research/capabilities/realtime-voice.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/rerank.md](../research/capabilities/rerank.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/speech-recognition.md](../research/capabilities/speech-recognition.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/speech-synthesis.md](../research/capabilities/speech-synthesis.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/tools-and-mcp.md](../research/capabilities/tools-and-mcp.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/vector-stores.md](../research/capabilities/vector-stores.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/video-generation.md](../research/capabilities/video-generation.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/vision-and-classification.md](../research/capabilities/vision-and-classification.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/capabilities/web-search-and-retrieval.md](../research/capabilities/web-search-and-retrieval.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/README.md](../research/providers/README.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/amazon-bedrock.md](../research/providers/amazon-bedrock.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/anthropic.md](../research/providers/anthropic.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/azure-openai.md](../research/providers/azure-openai.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/cohere.md](../research/providers/cohere.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/common-interface.md](../research/providers/common-interface.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/deepseek.md](../research/providers/deepseek.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/feature-matrix.md](../research/providers/feature-matrix.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/google-gemini.md](../research/providers/google-gemini.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/google-vertex.md](../research/providers/google-vertex.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/mistral.md](../research/providers/mistral.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/moonshot-kimi.md](../research/providers/moonshot-kimi.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/openai.md](../research/providers/openai.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/qwen.md](../research/providers/qwen.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/xai-grok.md](../research/providers/xai-grok.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/research/providers/zhipu-glm.md](../research/providers/zhipu-glm.md) | Dated research | Original source dates retained; excluded from user site |
| [docs/user/gateway-integration.md](../user/gateway-integration.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/guides/errors.md](../user/guides/errors.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/guides/fidelity.md](../user/guides/fidelity.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/guides/providers.md](../user/guides/providers.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/guides/streaming.md](../user/guides/streaming.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/guides/tools.md](../user/guides/tools.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/index.md](../user/index.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/libraries/README.md](../user/libraries/README.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/libraries/go.md](../user/libraries/go.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/libraries/python/README.md](../user/libraries/python/README.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/libraries/typescript.md](../user/libraries/typescript.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/platform/README.md](../user/platform/README.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/platform/client.md](../user/platform/client.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/platform/operations.md](../user/platform/operations.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/provider-feature-matrix.md](../user/provider-feature-matrix.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/reference/README.md](../user/reference/README.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/management.md](../user/reference/management.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-anthropic.md](../user/reference/ocai-anthropic.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-aws.md](../user/reference/ocai-aws.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-bedrock.md](../user/reference/ocai-bedrock.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-chat.md](../user/reference/ocai-chat.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-convert.md](../user/reference/ocai-convert.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-core.md](../user/reference/ocai-core.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-deepseek.md](../user/reference/ocai-deepseek.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-embedding.md](../user/reference/ocai-embedding.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-openai.md](../user/reference/ocai-openai.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-runtime.md](../user/reference/ocai-runtime.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-vectorstore.md](../user/reference/ocai-vectorstore.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/reference/ocai-wire.md](../user/reference/ocai-wire.md) | User API reference | Generated from source / OpenAPI; drift checked |
| [docs/user/spec/README.md](../user/spec/README.md) | User guide | Reconciled against current APIs; marked examples executed |
| [docs/user/writing-a-plugin.md](../user/writing-a-plugin.md) | User guide | Reconciled against current APIs; marked examples executed |
| [examples/ocai-contrib-echo/README.md](../../examples/ocai-contrib-echo/README.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [go/README.md](../../go/README.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [platform/README.md](../../platform/README.md) | Contributor/operator | Commands, ownership and status reconciled |
| [platform/packages/nuxt-ui/README.md](../../platform/packages/nuxt-ui/README.md) | Repository documentation | Audience/link inventory; see role in documentation map |
| [python/README.md](../../python/README.md) | Contributor/operator | Commands, ownership and status reconciled |
| [python/packages/ocai-anthropic/CHANGELOG.md](../../python/packages/ocai-anthropic/CHANGELOG.md) | Release history | Retained as immutable release history |
| [python/packages/ocai-anthropic/README.md](../../python/packages/ocai-anthropic/README.md) | Package documentation | Source/package metadata comparison; no runtime changes |
| [python/packages/ocai-aws/CHANGELOG.md](../../python/packages/ocai-aws/CHANGELOG.md) | Release history | Retained as immutable release history |
| [python/packages/ocai-aws/README.md](../../python/packages/ocai-aws/README.md) | Package documentation | Source/package metadata comparison; no runtime changes |
| [python/packages/ocai-bedrock/CHANGELOG.md](../../python/packages/ocai-bedrock/CHANGELOG.md) | Release history | Retained as immutable release history |
| [python/packages/ocai-bedrock/README.md](../../python/packages/ocai-bedrock/README.md) | Package documentation | Source/package metadata comparison; no runtime changes |
| [python/packages/ocai-core/CHANGELOG.md](../../python/packages/ocai-core/CHANGELOG.md) | Release history | Retained as immutable release history |
| [python/packages/ocai-core/README.md](../../python/packages/ocai-core/README.md) | Package documentation | Source/package metadata comparison; no runtime changes |
| [python/packages/ocai-deepseek/CHANGELOG.md](../../python/packages/ocai-deepseek/CHANGELOG.md) | Release history | Retained as immutable release history |
| [python/packages/ocai-deepseek/README.md](../../python/packages/ocai-deepseek/README.md) | Package documentation | Source/package metadata comparison; no runtime changes |
| [python/packages/ocai-openai/CHANGELOG.md](../../python/packages/ocai-openai/CHANGELOG.md) | Release history | Retained as immutable release history |
| [python/packages/ocai-openai/README.md](../../python/packages/ocai-openai/README.md) | Package documentation | Source/package metadata comparison; no runtime changes |
| [spec/README.md](../../spec/README.md) | Specification | Normative/proposal distinction retained; conformance gate |
| [spec/canonical-json.md](../../spec/canonical-json.md) | Specification | Normative/proposal distinction retained; conformance gate |
| [spec/extensions/README.md](../../spec/extensions/README.md) | Specification | Normative/proposal distinction retained; conformance gate |
| [spec/interfaces/README.md](../../spec/interfaces/README.md) | Specification | Normative/proposal distinction retained; conformance gate |
| [spec/proposals/ordered-items/README.md](../../spec/proposals/ordered-items/README.md) | Specification | Normative/proposal distinction retained; conformance gate |
| [spec/schema/README.md](../../spec/schema/README.md) | Specification | Normative/proposal distinction retained; conformance gate |
| [tasks/README.md](../../tasks/README.md) | Contributor/operator | Commands, ownership and status reconciled |
| [typescript/README.md](../../typescript/README.md) | Repository documentation | Audience/link inventory; see role in documentation map |
