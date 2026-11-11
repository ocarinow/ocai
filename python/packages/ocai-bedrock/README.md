# ocai-bedrock

Bedrock hosting for ocai, separate from shared AWS authentication and semantic
provider codecs. This package owns InvokeModel addressing, native host errors and
response metadata/effects. It performs no discovery and imports no provider SDK.

```python
import ocai.chat
from ocai.aws import SigV4Credential
from ocai.bedrock import Bedrock

model = ocai.chat.model(
    "anthropic/us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    host=Bedrock(region="us-east-1"),
    credentials=SigV4Credential(
        access_key="synthetic-access-key", secret_key="synthetic-secret-key",
        region="us-east-1",
    ),
)
```

Install the Anthropic codec and AWS credential packages separately or use the
`anthropic` and `aws` extras. The application supplies credentials explicitly;
ocai-aws delegates signing to AWS-maintained code. Users do not import its SDK.

Qualified unary surface: text, function tools, trait-declared version/beta body
placement, encoded identifiers, native errors and response metadata/guardrail
accounting. Explicit profile aliases affect capability lookup only. No model-ID
heuristic is used. Existing preflight profiles include dialect-wide wildcard
declarations; those and coverage_complete are not hosted-model qualification
(G-15). Verify deployment support independently of dialect declarations.

`beta` is an explicit tuple of body beta values; it does not silently enable any
feature. Version/beta conflicts fail before I/O. Binding-level arbitrary headers
are transmitted as explicit caller data, not qualified as feature relocations.
Use the host's beta field or trait-declared feature mappings for that purpose.

Configure guardrail identifier/version together. Recognized trace assessments
separate blocked output (ContentFilterError) from masking (reported semantic
shift). An intervention without sufficient trace is reported as unclassified;
it is never guessed to be blocked or unmodified. FidelityPolicy can reject those
shifts. HostEvidence retains native headers/body and host metadata; traces can
contain original content, so application exporters must redact them. Passive
observers omit this evidence.

Streaming, Converse, media, managed prompts, regional discovery and compatibility
endpoints are not qualified here. Streaming fails before I/O. Recorded tests prove
wire behavior without live keys; they do not establish service/account access.

| Surface | Recorded qualification |
|---|---|
| Text and system instruction | Exact body, canonical text/finish and input/output usage, both drivers |
| Function tools | Custom tool schema, auto selection, returned call identity/arguments and finish |
| Routing and beta | Encoded identifier, explicit version and beta placement; no beta feature availability claim |
| Errors | Header-only throttle/access/model error and body native codes; unknown codes preserved |
| Guardrails | Explicit blocking, output masking, uncertain intervention, caller fidelity rejection |
| Metadata | Host body fields and latency/tier headers retained; future host/dialect fields separated |
| Excluded | Streaming, Converse, media, managed prompts, regional/model discovery, live availability |

The recordings are synthetic, hand-authored against the AWS research sources in
`docs/providers/amazon-bedrock.md` section 16. They reuse the existing Anthropic
conversion graph. There is no new semantic edge or canonical revision.
