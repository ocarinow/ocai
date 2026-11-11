# Web search and retrieval — capability research

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

**Currency:** researched 2026-11-10 against official documentation. This
surface is the fastest-moving one ocai touches: Perplexity retired Sonar
Chat Completions on 2026-09-27, Bing Search APIs were retired on 2025-08-11,
Brave dropped its free tier in 2026, xAI retired `search_parameters` for a
Responses-API tool. Items marked *unverified* rest on third-party sources or
pages not re-read on the read date.

The page has two halves because the two halves land in two different places:

1. **Search as a server tool inside chat** — a chat concern; it lands on
   `PartServerToolCall(kind="web_search")` + `PartText.annotations`.
2. **Standalone search / fetch APIs** — a candidate kernel capability.

## 1. Provider-side search tools inside chat APIs

### 1.1 Per-interface request knob and response citation shape

**OpenAI Responses (`web_search`).** Tool
`{"type":"web_search","search_context_size":"low|medium|high","user_location":
{"type":"approximate","country","city","region","timezone"},"filters":
{"allowed_domains":[…],"blocked_domains":[…]},"external_web_access":true,
"return_token_budget":"default|unlimited"}` (`web_search_preview` is legacy
and lacks `filters`/`external_web_access`). Output items: `web_search_call
{id, status, action {type: search|open_page|find_in_page, query|queries,
sources (with include: ["web_search_call.action.sources"])}}` followed by a
`message` whose `output_text` carries `annotations[] {type: url_citation,
url, title, start_index, end_index}`. Chat Completions only has search
models (`gpt-5-search-api`). Price: ≈ $10 / 1,000 calls (third-party;
*unverified* — the pricing page was not fetched). Several searches can occur
per request; billing is per search.

**Anthropic Messages (`web_search`, `web_fetch`).** Tool
`{"type":"web_search_20250305|web_search_20260209|web_search_20260318",
"name":"web_search","max_uses","allowed_domains"|"blocked_domains" (never
both),"user_location":{type approximate, city, region, country, timezone},
"allowed_callers","response_inclusion":"full|excluded"}`. Response blocks:
`server_tool_use {id, name: web_search, input {query}}`,
`web_search_tool_result {tool_use_id, content: [web_search_result {url,
title, encrypted_content, page_age}] | web_search_tool_result_error
{error_code: too_many_requests|invalid_tool_input|max_uses_exceeded|
query_too_long|request_too_large|unavailable}}`, then `text` blocks with
`citations[] {type: web_search_result_location, url, title, encrypted_index,
cited_text}`. `encrypted_content`/`encrypted_index` must be replayed verbatim
or the next request 400s. `usage.server_tool_use.web_search_requests`;
$10 / 1,000 searches. `stop_reason: pause_turn` can interrupt a long search
turn. `web_fetch_20250910…20260318` adds `{url}` input, result
`web_fetch_tool_result {content {type: web_fetch_result, url, content
{type: document, source {type: text|base64, media_type, data}, title},
retrieved_at}}`, `char_location` citations, `max_content_tokens`,
`url_sources`, `use_cache`; no charge beyond tokens; URLs must already appear
in context (`url_not_in_prior_context`).

**Gemini (Google Search grounding).** `generateContent`: `tools:
[{"googleSearch": {}}]` (legacy `googleSearchRetrieval {dynamicRetrievalConfig
{mode, dynamicThreshold}}`), optional `urlContext`. Response
`candidates[].groundingMetadata {webSearchQueries[], searchEntryPoint
{renderedContent, sdkBlob}, groundingChunks[] {web {uri, title}},
groundingSupports[] {segment {partIndex, startIndex, endIndex, text},
groundingChunkIndices[], confidenceScores[], renderedParts},
retrievalMetadata {googleSearchDynamicRetrievalScore}}` and
`urlContextMetadata {urlMetadata[] {retrievedUrl, urlRetrievalStatus}}`.
The newer Interactions API instead emits `google_search_call
{arguments.queries}`, `google_search_result {search_suggestions}` and
`url_citation {url, title, start_index, end_index}` annotations on
`model_output` text. Price: Gemini 3+ 5,000 free search requests/month then
$14 / 1,000; Gemini 2.5 and older billed per grounded prompt; default 1,500
RPD. `renderedContent` carries a display obligation (search suggestions).

**xAI Responses (`web_search`, `x_search`).** `tools: [{"type":"web_search",
"allowed_domains" (≤5) | "excluded_domains" (≤5), "enable_image_understanding",
"enable_image_search"}]`. Output: `web_search_call` items; `response.citations`
(every URL encountered); inline `[[N]](url)` markers in the text with
`output_text.annotations[] {type: url_citation, url, title ("N"),
start_index, end_index}`; `include: ["no_inline_citations"]` removes the
markers (annotations then lose positions). $5 / 1,000 web-search calls;
X search billed per post ($5 / 1k) and profile ($10 / 1k). The legacy
`search_parameters` Live Search is reported retired with HTTP 410
(*unverified* — no official notice found).

**Perplexity.** Sonar Chat Completions ("search as the model") ended on
2026-09-27 per the API reference; the shape was OpenAI-style `choices[]` plus
`citations[]` (URLs) and `search_results[] {title, url, date, last_updated,
snippet, source, place_metadata}` with `[N]` markers in the text. The
successor Agent API prices tools per invocation (details *unverified*).

**Zhipu / Z.ai (GLM).** Chat tool `{"type":"web_search","web_search":{
"enable","search_engine": search_std|search_pro|search_pro_sogou|
search_pro_quark,"search_result","search_prompt","count" (1–50),
"search_domain_filter","search_recency_filter","content_size"}}`; the text
carries `[来源：ref_N]` markers; a `web_search[]` result array (fields
`title, link, content, media, icon, refer, publish_date`) is reported by
community docs (*unverified*). Standalone search via SDK
`client.web_search.web_search(search_engine, search_query, count,
search_domain_filter, search_recency_filter, content_size)` returns
`search_result[] {title, link, content, icon, media, publish_date, refer}` +
`search_intent[] {intent, keywords, query}`; ¥0.01–0.05 per call.

**Qwen (Alibaba Model Studio).** `enable_search: true` + `search_options
{search_strategy: "agent", enable_source: true, forced_search (*unverified*)}`;
response `search_info.search_results[] {index, title, url}`; no spans.

### 1.2 Comparison

| Interface | Request knob | Call item | Results item | Citation anchor | Replay lane | Usage |
|---|---|---|---|---|---|---|
| OpenAI `/responses` | `web_search` tool: context size, location, domain filters | `web_search_call {action}` | `action.sources` (opt-in) | `url_citation {start_index, end_index}` on output text | item ids / `previous_response_id` | per call |
| Anthropic | `web_search_*`: `max_uses`, domains, location | `server_tool_use` | `web_search_tool_result[]` | `web_search_result_location {cited_text}` on a text block (no offsets) | `encrypted_content`, `encrypted_index` | `web_search_requests` |
| Anthropic fetch | `web_fetch_*`: domains, `max_content_tokens` | `server_tool_use {url}` | `web_fetch_result {document}` | `char_location` into the fetched document | — | `web_fetch_requests` |
| Gemini | `googleSearch` / `urlContext` | `webSearchQueries[]` | `groundingChunks[]` | `groundingSupports.segment {startIndex,endIndex}` | none | per request (3+) |
| xAI | `web_search`: domains, image flags | `web_search_call` | `response.citations` | `url_citation` on `[[N]](url)` markers | item ids | per call |
| Perplexity (legacy) | model choice + filters | — | `search_results[]` | `[N]` markers, no offsets | — | `num_search_queries` |
| Zhipu | `web_search` tool: engine, count, domain, recency | — | `web_search[]` (*unverified*) | `[来源：ref_N]` markers | — | per call |
| Qwen | `enable_search` + `search_options` | — | `search_info.search_results[]` | none | — | — |

### 1.3 Mapping onto the chat IR

- The call is a `PartServerToolCall(kind="web_search" | "web_fetch",
  call_id, status, payload=verbatim)`; results are `PartServerToolResult`
  with the verbatim result array as `payload`. Anthropic's in-band error
  object becomes `PartServerToolResult(is_error=True, payload={error_code})`
  — the wire shape that rule 8 demands for mid-turn tool errors.
- Citations become `PartText.annotations[]` **only when the offsets validate
  against the decoded text** (§3.1): OpenAI and xAI `start_index/end_index`
  and Gemini `segment.startIndex/endIndex` are checked against the part's
  text (index unit — code point vs UTF-16 vs byte — is per edge and must be
  fixture-pinned); Anthropic citations attach to a whole text block, so the
  span is the block; marker-only schemes (Perplexity `[N]`, Zhipu
  `[来源：ref_N]`, xAI with `no_inline_citations`) carry no validated span and
  ride a censused extension. Text is never rewritten to strip markers.

### 1.4 Chat IR gaps at the research date

1. **A canonical citation annotation.** `Annotation(kind="url_citation",
   start, end, url, title, cited_text?, source: ref into the sibling
   `PartServerToolResult` payload, native)`; `kind` open; `DeltaAnnotation`
   already exists for streaming.
2. **Server-tool configuration on `ChatRequest.tools`.** A
   `ServerTool(kind="web_search", allowed_domains, blocked_domains,
   user_location, max_uses?, context_size?)` entry. Three-lane law: domain
   allow/block lists (OpenAI, Anthropic, xAI, Zhipu, Perplexity) and
   `user_location` (OpenAI, Anthropic) qualify as first-class; `max_uses`,
   `search_context_size`, `search_engine`, `dynamicThreshold` are censused
   extensions; `allowed_callers`/`response_inclusion` are `provider_options`.
3. **Replay lanes.** `encrypted_content`/`encrypted_index` and OpenAI item
   ids are `ProviderRef` anchors on `PartServerToolResult`/`Annotation`
   (§2.4) — scoped to `(provider, interface)`, `UNSUPPORTED`-and-reported on
   crossing, never silently dropped (dropping them breaks the next turn).
4. **A `search_requests` consumption dimension** (open-code unit, §11 step 9)
   so the ledger can price Anthropic `web_search_requests`, xAI per-call,
   Gemini per-request and Perplexity `num_search_queries` on one axis.
5. **Display obligations as data.** Gemini `searchEntryPoint.renderedContent`
   and Anthropic's "citations must be shown" terms belong in a censused
   extension plus a `CapabilityProfile` key, not in prose.
6. **Fold-triple fixtures** for `response.output_text.annotation.added`,
   Anthropic `content_block_start` of `web_search_tool_result`, and Gemini
   grounding delivered only on the last chunk.

## 2. Standalone search and retrieval APIs

### 2.1 Per-provider shapes

- **Tavily** — `POST https://api.tavily.com/search`, bearer `tvly-…`. Request
  `query`, `search_depth: basic|advanced|fast|ultra-fast`, `topic: general|
  news|finance`, `max_results` (0–20), `chunks_per_source` (1–3),
  `include_answer` (bool | basic|advanced), `include_raw_content` (bool |
  markdown|text), `include_images`, `include_domains` (≤300) /
  `exclude_domains` (≤150), `include_domains_mode: restrict|prefer`,
  `time_range`, `start_date`/`end_date`, `country`, `auto_parameters`,
  `include_usage`, `max_age_hours`. Response `query, answer?, images[],
  results[] {title, url, content, score, raw_content?, published_date,
  favicon, id}, response_time, request_id, usage {credits}`. 1 credit per
  basic/fast/ultra-fast request, 2 for advanced; 429 with `Retry-After`,
  432/433/434 plan-limit codes. Sibling endpoints: extract, crawl, map.
- **Exa** — `POST https://api.exa.ai/search`, `x-api-key` or bearer. Request
  `query`, `type: auto|lite|deep-lite|deep` (legacy `instant|fast|
  deep-reasoning`; `neural`/`keyword` no longer listed), `category`,
  `numResults` (1–100), `includeDomains`/`excludeDomains` (≤1,200),
  `startPublishedDate`/`endPublishedDate`, `contents {text, highlights,
  summary, extras, maxAgeHours, snapshotAsOf, livecrawlTimeout}`,
  `userLocation`, `moderation`, `additionalQueries`, `outputSchema`. Response
  `requestId, results[] {id, title, url, publishedDate, author, image,
  favicon, text, highlights, summary, subpages, entities, extras},
  costDollars {total, search {neural, keyword}, contents {text, highlights,
  summary}}, searchTime, warnings`. No `score` in the current schema.
  Siblings `/contents`, `/findSimilar` (`/answer` and `/research` not on the
  read-date page). Per-request `costDollars` is the price signal.
- **Brave** — `GET https://api.search.brave.com/res/v1/web/search`,
  `X-Subscription-Token`. Params `q`, `country`, `search_lang`, `ui_lang`,
  `count` (≤20), `offset` (≤9), `safesearch: off|moderate|strict`,
  `freshness: pd|pw|pm|py|YYYY-MM-DDtoYYYY-MM-DD`, `extra_snippets`,
  `goggles`, `enable_rich_callback`. Response `query {original,
  more_results_available}, web {results[] {title, url, description,
  extra_snippets, …}}, locations, rich`; verticals (`news`, `videos`,
  `infobox`, `summarizer`) exist but were not on the read-date page. Free
  tier removed in 2026; $5 / 1,000 requests with $5 monthly credit; Answers
  $4 / 1,000 + tokens (*unverified*; dashboard and docs disagree).
- **Serper** — `POST https://google.serper.dev/search`, `X-API-KEY`
  (endpoint/auth from memory; the landing page shows only payloads —
  *unverified*). Response `knowledgeGraph, organic[] {title, link, snippet,
  position, date?, sitelinks?}, peopleAlsoAsk, relatedSearches`; verticals
  images/news/places/videos/shopping/scholar/patents/autocomplete. 2,500 free
  queries; per-1,000 price not on the page.
- **SerpApi** — `GET https://serpapi.com/search?engine=google&q=…&api_key=…`
  (`output: json|html|md`, `location`, `gl`, `hl`, `tbm`, `tbs`, `start`,
  `no_cache`, `async`). Response `search_information, organic_results[]
  {position, title, link, displayed_link, snippet, snippet_highlighted_words,
  sitelinks, source, favicon}, knowledge_graph, related_questions,
  related_searches, pagination, serpapi_pagination`. Plans not on the page.
- **Bing** — Bing Search v7 and Custom Search were retired on 2025-08-11
  (Microsoft lifecycle announcement; calls return 410). The successor,
  Grounding with Bing Search, is a tool inside Azure AI Agents whose raw
  results are not exposed to developers; ≈ $14 / 1,000 transactions
  (*unverified*). Treat Bing as **not available** for a standalone edge.
- **You.com** — `POST https://ydc-index.io/v1/search`, `X-API-Key`. Request
  `query`, `count` (1–100), `offset` (0–9), `country`, `language`,
  `safesearch`, `freshness`, `include_domains`/`exclude_domains`/
  `boost_domains`, `knowledge: core`, `strict_operators`, `extraction
  {extraction_mode: highlights|full_page, extraction_source: blend|cache|
  fetch, highlights.total_max_tokens, full_page.extraction_formats}`,
  `crawl_timeout`. Response `results {web[] {url, title, description,
  snippets[], thumbnail_url, page_age, contents, favicon_url}, knowledge[]},
  metadata {search_uuid, query, latency}`. Price not on the page.
- **Firecrawl** — `POST https://api.firecrawl.dev/v2/search`, bearer.
  Request `query` (≤500 chars), `limit` (1–100), `sources: web|images|news|
  alexandria`, `categories: developer|gov|research|pdf`, `includeDomains`/
  `excludeDomains`, `tbs`, `location`, `country`, `timeout`, `scrapeOptions
  {formats: markdown|html|rawHtml|links|screenshot|json|summary,
  onlyMainContent, waitFor, actions}`. Response `success, data {web[] {url,
  title, description, markdown?, html?, links?, metadata?}, news[] {title,
  snippet, url, date, imageUrl, position}, images[]}, creditsUsed, id,
  warning`. Siblings `/v2/scrape`, `/v2/crawl` (+ `GET /v2/crawl/{id}`),
  `/v2/extract`, `/v2/map` (shapes not re-read — *unverified*).
- **Jina Reader** — `GET https://r.jina.ai/{url}` (read) and
  `GET https://s.jina.ai/?q=…` (search); optional bearer key raises limits
  (20 RPM keyless → 500 RPM free key → 5,000 premium; search needs a key,
  100 RPM). Headers `X-Engine`, `X-Respond-With` (`readerlm-v2`),
  `X-Target-Selector`, `X-Remove-Selector`, `X-Timeout`, `X-No-Cache`,
  `X-With-Links-Summary`, `X-With-Images-Summary`, `X-With-Generated-Alt`,
  `X-Token-Budget`, `X-Locale`, `X-Proxy-Url`, `Accept: application/json`.
  JSON body returns URL, title, content, timestamp (field names not on the
  page — *unverified*). Token-billed; search costs a flat ≥ 10,000 tokens.
- **Perplexity Search API** — `POST https://api.perplexity.ai/search`,
  bearer. Request `query` (string | array), `max_results` (1–50; >20 needs
  `search_type: people`), `max_tokens`, `max_tokens_per_page`, `country`,
  `search_type: web|fast|people`, `search_domain_filter` (≤20),
  `search_recency_filter: hour|day|week|month|year`,
  `search_after_date_filter`/`search_before_date_filter` (MM/DD/YYYY),
  `last_updated_*_filter`, `search_language_filter`. Response `id, results[]
  {title, url, snippet, date, last_updated}, server_time`. Price not on page.
- **Linkup** — `POST https://api.linkup.so/v1/search`, bearer (402 returns
  x402 USDC payment details). Request `q`, `depth: flash|fast|standard|deep`,
  `outputType: searchResults|sourcedAnswer|structured`,
  `structuredOutputSchema`, `includeImages`, `includeInlineCitations`,
  `includeSources`, `fromDate`/`toDate`, `includeDomains` (≤100) /
  `excludeDomains`, `maxResults`. Response `results[] {type: text|image,
  name, url, content, favicon}` or `answer, sources[] {name, url, snippet,
  favicon}` or the schema object (+ `sources` when requested). 429 covers
  both rate and credit exhaustion.

### 2.2 Comparison

| Provider | Verb | Auth | Query knobs | Domain filter | Date filter | Result fields | Score | Content | Unit |
|---|---|---|---|---|---|---|---|---|---|
| Tavily | POST JSON | bearer | depth, topic, max_results | include/exclude | range, dates, max_age | title, url, content, published_date, favicon | yes | raw_content md/text | credits/request |
| Exa | POST JSON | key | type, category, numResults | include/exclude | published dates | title, url, publishedDate, author, text, highlights, summary | no | text/highlights/summary | dollars/request |
| Brave | GET | token | count, offset, freshness, goggles | none (operators) | freshness | title, url, description, extra_snippets | no | snippets | $/1k requests |
| Serper | POST JSON | key | num, gl, hl, tbs | site: operator | tbs | title, link, snippet, position, date | no | snippet | credits |
| SerpApi | GET | key | engine, tbm, tbs, start | site: operator | tbs | position, title, link, snippet, sitelinks | no | snippet | plans |
| Bing | retired 2025-08-11 | — | — | — | — | — | — | — | — |
| You.com | POST JSON | key | count, offset, freshness | include/exclude/boost | freshness | url, title, description, snippets, page_age | no | highlights/full_page | $/1k (*unverified*) |
| Firecrawl | POST JSON | bearer | limit, sources, categories, tbs | include/exclude | tbs | url, title, description (+scrape) | no | markdown/html via scrape | credits |
| Jina | GET | bearer optional | q, headers | `X-Site` (*unverified*) | none | url, title, content | no | full page markdown | tokens |
| Perplexity Search | POST JSON | bearer | max_results, search_type | domain filter | recency, before/after, last_updated | title, url, snippet, date, last_updated | no | snippet | per request (*unverified*) |
| Linkup | POST JSON | bearer | depth, outputType, maxResults | include/exclude | from/to | name, url, content | no | content / answer | credits |

### 2.3 Canonical IR proposal — `search`

The dialects vary exactly where the litmus test looks: request verb and
addressing (GET params vs JSON), query knobs (depth/type/topic), filter
vocabularies (domains, recency enums, date formats), result fields
(`content` vs `snippet` vs `description`; `published_date` vs `date` vs
`page_age`), scoring (only Tavily), optional answers, and billing units
(credits, dollars, tokens, requests). That is a capability.

- **Identity:** `Capability("search")`, operations `search` and `fetch`;
  shapes `("search","search.request")`, `("search","search.response")`,
  `("search","fetch.request")`, `("search","fetch.response")`. Package
  `ocai.search`, core-only imports.
- **`SearchRequest(query, max_results, filters: SearchFilters(include_domains,
  exclude_domains, published_after, published_before, recency: open code,
  country, language, safe_search), content: ContentRequest(mode: snippet|full,
  format: markdown|text|html, max_chars) | None, effort: open code
  (fast|standard|deep), provider_options)`** — no engine/model in the request;
  the resource is bound at the front door (`"tavily/search"`,
  `"exa/auto"`, `"brave/web"`).
- **`SearchResponse(results[]: SearchResult(url, title, snippet, content?,
  score?, published_at?, author?, rank, native, extensions), answer:
  SearchAnswer(text, citations[]) | None [provisional], related_queries?,
  extensions)`**; `usage = Consumption(search_requests=1, credits?, tokens?)`
  with `currency` reserved for Exa `costDollars`.
- **`FetchRequest(source: Source(url), format, max_chars, provider_options)`
  / `FetchResponse(document: PartDocument | text, title, retrieved_at,
  links[]?)`** covers Jina Reader, Firecrawl scrape, Tavily extract, Exa
  contents, You.com full_page — and is the same shape Anthropic's
  `web_fetch_result.document` decodes to, so a local HTTP+readability
  adapter is a legitimate in-process peer.
- **Declared loss:** `score` `ABSENT` everywhere but Tavily; `rank` is
  positional; recency enums (`pd` vs `day` vs `hour`) are `SemanticShift`s;
  `effort` mapping (Tavily depth, Exa type, Linkup depth, Perplexity
  search_type) is a per-edge `SemanticShift` with the native value kept;
  answers are provider-generated and never synthesized by ocai; Jina's
  token billing is reported as `tokens`, not rescaled to requests.
- **Verdict:** kernel capability, **P1**, effort **S–M** (two dataclass
  families, six edges to cover the variance). **First provider: Tavily**
  (JSON, bearer, LLM-oriented result shape, explicit usage), then **Brave**
  (GET + classic SERP shape proves the variance), then **Exa** (contents and
  `findSimilar` exercise `fetch`). Half 1 is **P0** inside the chat IR: the
  flagship `/responses` migration cannot be honest without `url_citation`
  annotations and replay anchors.

## 3. Unverified / open

- OpenAI web-search list price and streaming event names; index unit of
  `start_index` (code point vs UTF-16) for OpenAI and xAI.
- xAI `search_parameters` retirement notice; Perplexity Agent API tool shape.
- Zhipu chat-response `web_search[]` array; Qwen `forced_search`.
- Serper endpoint path and auth header; Brave current plan names; You.com,
  Perplexity Search and Firecrawl list prices; Jina JSON field names.
- Grounding with Bing Search price.

## Sources (read 2026-11-10)

- https://developers.openai.com/api/docs/guides/tools-web-search
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool
- https://aistudio.google.com/docs/grounding
- https://aistudio.google.com/api-reference/generate-content
- https://docs.x.ai/docs/guides/live-search
- https://docs.x.ai/docs/tools/citations
- https://docs.x.ai/developers/pricing
- https://docs.perplexity.ai/api-reference/chat-completions-post
- https://docs.perplexity.ai/api-reference/search-post
- https://docs.bigmodel.cn/cn/guide/tools/web-search
- https://www.alibabacloud.com/help/en/model-studio/web-search
- https://docs.tavily.com/documentation/api-reference/endpoint/search
- https://docs.exa.ai/reference/search
- https://api-dashboard.search.brave.com/app/documentation/web-search/query
- https://api-dashboard.search.brave.com/documentation/pricing
- https://serper.dev/
- https://serpapi.com/search-api
- https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement
- https://you.com/docs/api-reference/search
- https://docs.firecrawl.dev/api-reference/endpoint/search
- https://jina.ai/reader/
- https://docs.linkup.so/pages/documentation/api-reference/endpoint/post-search
