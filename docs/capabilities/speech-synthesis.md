# Speech synthesis (text-to-speech)

**Currency:** researched 2026-11-10 against official provider documentation
(URLs in Sources). Provider surfaces in this space change monthly; model names and limits below are as published on
the read date. Items marked *unverified* could not be confirmed on an official page at read time.

## 1. Scope and position in ocai

Text in, audio out. The capability is unary with an optional streaming shape: a `SynthesisRequest` yields one
`SynthesisResponse` (a `PartAudio` plus optional timing marks), or a stream of `SynthesisChunk`s that fold into the
same response. It does not cover duplex voice (see [realtime-voice.md](realtime-voice.md)); several providers now
steer new TTS integrations to their realtime products, which makes the interface-migration story (§6) directly
relevant.

Architecture hooks: `PartAudio` over the `Source` union (§3.1); the capability recipe (§11): identity as data, no
routing data in the request, voice as a provider-scoped `ProviderRef`, streaming ratchet with a per-capability fold
law, `Consumption` with open units (`characters`, `tokens`, `seconds`).

## 2. Provider survey

### 2.1 OpenAI (`/v1/audio/speech`)

- Endpoint `POST /v1/audio/speech`, bearer auth. Body: `model` (`tts-1`, `tts-1-hd`, `gpt-4o-mini-tts`,
  `gpt-4o-mini-tts-2025-12-15`, or free-form), `input` (max 4096 chars), `voice` (built-in name or `{"id":
  "voice_..."}` custom voice), `instructions` (max 4096 chars; not on `tts-1`/`tts-1-hd`), `response_format` (`mp3`
  default, `opus`, `aac`, `flac`, `wav`, `pcm`), `speed` (0.25 to 4.0), `stream_format` (`audio` default or `sse`;
  `sse` not on `tts-1`/`tts-1-hd`).
- Built-in voices: alloy, ash, ballad, coral, echo, fable, onyx, nova, sage, shimmer, verse, marin, cedar (marin/cedar
  recommended).
- Output: `Content-Type: application/octet-stream`; chunked transfer so playback can start early. PCM is 24 kHz,
  16-bit signed LE, headerless. SSE event names for `stream_format=sse` are *unverified* (not on the reference page).
- Timestamps: none.
- Voice identity: custom voices via `POST /v1/audio/voice_consents` (multipart `name`, `language`, `recording`;
  consent phrases from `GET /v1/audio/consent_phrases`) then `POST /v1/audio/voices` (multipart `name`,
  `audio_sample`, `consent`) returning a `voice_...` id; recording-based voices are sales-gated (20 per org).
  Prompt-to-voice (`POST /v1/audio/voices` JSON with `type: "prompt"`, `name`, `prompt`, `model`, `script_hint`) is GA
  but usable only in GPT-Live. Scopes `api.voices.read` / `api.voices.write`.
- SSML: none; style via `instructions` (prompt-based control).
- Pricing: `tts-1` $15 / 1M chars, `tts-1-hd` $30 / 1M chars, `gpt-4o-mini-tts` $0.60 / 1M text input tokens + $12 /
  1M audio output tokens.
- **Deprecation:** `tts-1`, `tts-1-hd`, `gpt-4o-mini-tts` shut down 2027-01-06; OpenAI recommends
  `gpt-realtime-2.1-mini` via the Realtime API, which `/v1/audio/speech` does not support. This is an interface
  migration (unary HTTP to duplex session), not a model swap.

### 2.2 ElevenLabs

- `POST /v1/text-to-speech/{voice_id}` (file) and `/stream` (chunked audio); header `xi-api-key`. Regional hosts
  (`api.us.`, `api.eu.residency.`, ...). Query: `output_format` (`mp3_22050_32` ... `mp3_44100_192`, `pcm_8000` ...
  `pcm_48000`, `wav_*`, `ulaw_8000`, `alaw_8000`, `opus_48000_*`; some tiers gated), `enable_logging`,
  `optimize_streaming_latency` (deprecated).
- Body: `text`, `model_id` (default `eleven_multilingual_v2`), `language_code`, `voice_settings` (`stability` 0.5,
  `similarity_boost` 0.75, `style` 0, `use_speaker_boost` true, `speed` 1.0, `clone_strength`),
  `pronunciation_dictionary_locators` (max 3: `pronunciation_dictionary_id`, `version_id`), `seed` (0..4294967295,
  best-effort), `previous_text` / `next_text`, `previous_request_ids` / `next_request_ids` (max 3; request stitching),
  `apply_text_normalization` (`auto|on|off`), `apply_language_text_normalization`, `use_pvc_as_ivc`, `audio_effects`.
- Timestamps: `POST .../with-timestamps` returns `audio_base64`, `alignment` and `normalized_alignment`, each
  `{characters[], character_start_times_seconds[], character_end_times_seconds[]}`; `.../stream/with-timestamps`
  streams JSON objects of the same shape (`StreamingAudioChunkWithTimestampsResponseModel`). Whether streamed times
  are chunk-relative or absolute is *unverified* for HTTP; for the WebSocket API the docs say chunk-relative.
- WebSocket input streaming: `wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input` with query
  `model_id`, `output_format`, `inactivity_timeout` (20, max 180), `sync_alignment`, `auto_mode`,
  `enable_ssml_parsing`, `seed`. First message `{"text": " ", "voice_settings", "generation_config":
  {"chunk_length_schedule": [120,160,250,290]}, "pronunciation_dictionary_locators", "xi-api-key"}`; then `{"text",
  "try_trigger_generation", "flush"}`; `{"text": ""}` closes. Server messages: `{"audio": base64, "alignment":
  {"chars", "charStartTimesMs", "charDurationsMs"}, "normalizedAlignment"}` and `{"isFinal": true}`.
- Models: `eleven_v4` (10k chars), `eleven_v4_turbo`, `eleven_v3` (5k chars), `eleven_v3_conversational`,
  `eleven_multilingual_v2` (10k), `eleven_flash_v2_5` (40k), `eleven_flash_v2` (30k); turbo models deprecated. Audio
  tags for expressive control on v4 turbo / v3 conversational.
- Voice cloning: IVC `POST /v1/voices/add` (multipart `name`, `files`, `remove_background_noise`, `description`,
  `labels`) returns `voice_id`, `requires_verification`. PVC and voice design endpoints exist (not read).
- Pronunciation dictionaries: `POST /v1/pronunciation-dictionaries/add-from-file` (PLS file) returns `id`,
  `version_id`.
- SSML: only via `enable_ssml_parsing` on the WebSocket API (verified there; HTTP SSML support *unverified*).
- Errors: 422 with `detail[{loc,msg,type}]`; 400/404 for audio effects.
- Pricing: per character; $0.08 / 1k chars multilingual, $0.04 / 1k chars Flash/Turbo/v4 Turbo/v3 Conversational. Plan
  concurrency 4..40.

### 2.3 Google Cloud Text-to-Speech and Gemini TTS

- `POST https://texttospeech.googleapis.com/v1/text:synthesize`. Body: `input` (`text`, `ssml`, `markup` [HD voices
  only], `multiSpeakerMarkup`, `customPronunciations`, `prompt` [controllable models]), `voice` (`languageCode`
  required, `name`, `ssmlGender`, `customVoice{model, reportedUsage}`, `voiceClone{voiceCloningKey}`), `audioConfig`
  (`audioEncoding` LINEAR16 [WAV header], MP3 [32 kbps], OGG_OPUS, MULAW, ALAW; `speakingRate` 0.25..2.0, `pitch`
  -20..20, `volumeGainDb` -96..16, `sampleRateHertz`, `effectsProfileId[]`), `advancedVoiceOptions
  {lowLatencyJourneySynthesis}`. Response `audioContent` (base64).
- Timepoints: v1beta1 `enableTimePointing: ["SSML_MARK"]` returns `timepoints[{markName, timeSeconds}]` for SSML
  `<mark>` tags.
- Streaming: gRPC bidirectional `StreamingSynthesize`: first message `streaming_config{voice,
  streaming_audio_config{audio_encoding, sample_rate_hertz, speaking_rate}, custom_pronunciations}`, then
  `input{text, markup, multi_speaker_markup or prompt}`; responses carry `audio_content` (headerless LINEAR16
  24 kHz). Only PCM/ALAW/MULAW/OGG_OPUS; no `ssml` field in streaming input.
- Voice families: Standard, WaveNet, Neural2, Studio, Polyglot, Chirp-HD, Chirp 3: HD (`en-US-Chirp3-HD-Aoede`, 30
  voices, 53 locales; SSML for synchronous requests only, `speaking_rate` only, `[pause]` tags in `markup`), Chirp 3
  Instant Custom Voice (allow-listed; `POST v1beta1/voices:generateVoiceCloningKey` with `reference_audio`,
  `voice_talent_consent`, `consent_script`, `language_code` returns a client-held `voiceCloningKey`).
- Limits: 5,000 bytes per request; RPM quotas per family (Chirp3 200, Neural2 1000, Studio 500); 100 concurrent
  streaming sessions.
- Gemini TTS (AI Studio page at read time): models `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`; the documented
  path is the Interactions API (`POST /v1beta/interactions` with `response_format: {"type": "audio"}`,
  `generation_config.speech_config` as `[{"voice": "Kore"}]` or `{"speakers": [...]}`, `speech_metadata.style` per
  turn, inline `<laugh>` tags, `stream: true` emitting `step.delta`). Output WAV 24 kHz mono 16-bit (unary) or
  headerless `audio/l16` (streaming); `audio/mulaw`, `audio/alaw` at 8 kHz optional. 30 studio voices + extended
  library; custom `voice_...` ids (200 per project, 1-year TTL). The older `generateContent` +
  `speechConfig.voiceConfig.prebuiltVoiceConfig` path is *unverified* as still documented. Cloud TTS quotas page lists
  `gemini-2.5-flash-tts` 150 QPM and `gemini-2.5-pro-tts` 125 QPM.

### 2.4 Azure Speech (Foundry Tools)

- REST `POST https://{region}.tts.speech.microsoft.com/cognitiveservices/v1` (or
  `{resource}.cognitiveservices.azure.com`). Headers `Ocp-Apim-Subscription-Key` or `Authorization: Bearer` (STS token
  from `/sts/v1.0/issueToken`, 10 min), `Content-Type: application/ssml+xml`, `X-Microsoft-OutputFormat`,
  `User-Agent`. Body is SSML (`<speak>` with `<voice name="en-US-JennyNeural">`); custom voice endpoints add
  `?deploymentId=`.
- Output formats: streaming `raw-*-pcm` (8k..48k), `audio-*-mp3`, `ogg-*-opus`, `webm-*-opus`,
  `raw-8khz-8bit-mono-mulaw/alaw`, `g722`, `amr-wb`; non-streaming `riff-*-pcm`. 24 kHz native, 48 kHz high-fidelity.
- Voices: `GET /tts/cognitiveservices/voices/list` returns `ShortName`, `Locale`, `StyleList`, `SampleRateHertz`,
  `WordsPerMinute`, `VoiceType`.
- Word boundaries and visemes: Speech SDK events only (`WordBoundary` with `AudioOffset` in 100 ns ticks, `Duration`,
  `Text`, `TextOffset`, `WordLength`, `BoundaryType` Word|Punctuation|Sentence; `VisemeReceived` with `AudioOffset`,
  `VisemeId` [22 ids], `Animation` SVG or 55-value blend-shape frames; `BookmarkReached` for `<bookmark>`). The SDK
  speaks a WebSocket protocol (`wss://{region}.tts.speech.microsoft.com/cognitiveservices/websocket/v2` for input text
  streaming, `SpeechSynthesisRequestInputType.TextStream`, no SSML in that mode). The wire protocol is not documented
  for third-party clients; an ocai adapter would have to reverse it (*not permitted* under the no-SDK rule without a
  documented protocol) or stay REST-only.
- Limits: 10 min audio per request; 50 `<voice>`/`<audio>` tags; 64 KB SSML per WebSocket turn; 30 TPS default (S0).
  Status codes 400/401/415/429/502/503.
- Pricing: per character; the quotas page uses $15 / 1M chars for estimation.

### 2.5 Amazon Polly

- `POST /v1/speech` (SigV4). Body: `Engine` (`standard|neural|long-form| generative`), `LanguageCode`, `LexiconNames`
  (max 5), `OutputFormat` (`json|mp3|ogg_opus|ogg_vorbis|pcm|mulaw|alaw`), `SampleRate` (mp3/vorbis 8000..48000; pcm
  8000/16000; opus 48000; mulaw/alaw 8000), `SpeechMarkTypes` (`sentence|ssml|viseme|word`, max 4), `Text`, `TextType`
  (`ssml|text`), `VoiceId`.
- Response: `Content-Type` per format; `x-amzn-RequestCharacters` header; body is the audio stream, or line-delimited
  JSON speech marks when `OutputFormat=json`: `{"time": ms, "type": word|sentence|viseme|ssml, "start": byte, "end":
  byte, "value": ...}`. Speech marks are a separate request from audio (metadata instead of audio).
- Limits: 6,000 chars total / 3,000 billed per `SynthesizeSpeech`; `StartSpeechSynthesisTask` 200,000 / 100,000 (S3
  output). Errors: `TextLengthExceededException`, `InvalidSsmlException`, `MarksNotSupportedForFormatException`,
  `EngineNotSupportedException`, ...
- SSML: full; speech marks on standard/neural/long-form only.

### 2.6 Cartesia (Sonic)

- `POST /tts/bytes` with `Cartesia-Version: 2026-08-14` (only accepted value on the read date) and bearer auth. Body:
  `model_id` (`sonic-3.6`, `sonic-3.5`, `sonic-3`, `sonic-latest`), `transcript`, `voice` (id string or `{id}`),
  `output_format` (`container` wav|mp3|raw; `encoding` pcm_f32le|pcm_s16le| pcm_mulaw|pcm_alaw; `sample_rate`
  8000..48000; `bit_rate` for mp3), `language` or `locale` (not both), `accent`, `normalization`,
  `pronunciation_dict_id`, `generation_config{volume 0.5..2, speed 0.6..1.5, emotion}`. Response: audio bytes.
- WebSocket `wss://api.cartesia.ai/tts/websocket?cartesia_version=...` (`X-API-Key` header or `access_token` query).
  Request: `context_id`, `model_id`, `transcript`, `voice`, `output_format` (raw only), `continue`,
  `max_buffer_delay_ms` (0..5000), `flush`, `add_timestamps`, `add_phoneme_timestamps`, `use_normalized_timestamps`,
  `cancel`. Responses (all with `context_id`): `chunk{data base64, done, status_code, step_time}`,
  `timestamps{word_timestamps{words[], start[], end[]}}`, `phoneme_timestamps`, `flush_done{flush_id}`, `done`,
  `error{status_code, title, message}`. Contexts concatenate transcript chunks into one audio.
- Cloning: 10 s clip (60 s on Sonic 3.6+), 16 MB max; Clone Voice API takes clip, name, language (field names
  *unverified*).

### 2.7 Deepgram Aura

- `POST https://api.deepgram.com/v1/speak?model=aura-2-thalia-en` with `Authorization: Token <key>` and body `{"text":
  "..."}`. Query: `encoding` (`linear16|flac|mulaw|alaw|mp3|opus|aac`), `sample_rate`, `container` (`none|wav|ogg`),
  `bit_rate`, `callback`, `tag`, `mip_opt_out`, `speed`. Limit 2,000 chars (413 otherwise). Headers `dg-char-count`,
  `dg-request-id`, `dg-model-name`, `dg-model-uuid`.
- WebSocket `wss://api.deepgram.com/v1/speak` (`model`, `encoding` linear16|mulaw|alaw, `sample_rate`, `speed`):
  client `{"type":"Speak","text"}`, `Flush`, `Clear`, `Close`; server binary audio, `Metadata{request_id, model_name,
  model_version, model_uuid}`, `Flushed{sequence_id}`, `Cleared{sequence_id}`, `Warning{description, code}`.
- Models: Aura-1 (English), Aura-2 (en, es, de, fr, nl, it, ja; naming `aura-2-<voice>-<lang>`). Pricing $0.030 / 1k
  chars.

### 2.8 PlayHT

- `POST https://api.play.ht/api/v2/tts/stream`, headers `AUTHORIZATION: Bearer`, `X-USER-ID`. Body: `text`, `voice`
  (manifest URL id), `voice_engine` (`PlayDialog-turbo|PlayDialog|Play3.0-mini|PlayHT2.0-turbo| PlayHT2.0|PlayHT1.0`),
  `output_format` (`mp3|mulaw|wav|ogg|flac`), `quality`, `speed` 0.1..5, `sample_rate` 8000..48000, `seed`,
  `temperature`, `emotion`, `voice_guidance`, `style_guidance`, `text_guidance`, `language`; PlayDialog adds
  `voice_2`, `turn_prefix(_2)`. Limits 20,000 chars (Play3.0-mini) / 2,000 others. Errors JSON `error_message`,
  `error_id`. No timestamps; WebSocket *unverified*.

### 2.9 Hume (Octave) — status unverified

Every `dev.hume.ai` TTS and changelog URL fetched on 2026-11-10 served the new "Audio Decisions API" (launched
2026-11-02) instead of TTS content, and the site index listed only Audio Decisions and Expression Measurement. A
search snippet claimed TTS and EVI access ends 2026-11-13; this could not be confirmed on an official page. Treat Hume
TTS (`POST /v0/tts`, `utterances` with `description`-driven voice design) as **not a candidate** until status is
confirmed.

### 2.10 MiniMax (T2A v2)

- `POST https://api.minimax.io/v1/t2a_v2`, bearer. Body: `model` (`speech-2.8-hd|turbo`, `speech-2.6-*`,
  `speech-02-*`, `speech-01-*`), `text` (10,000 chars; `<#x#>` pause markers, inline pinyin/IPA), `stream`,
  `voice_setting{voice_id, speed 0.5..2, vol, pitch -12..12, emotion}`, `audio_setting{sample_rate, bitrate, format
  mp3|pcm|flac|wav|pcmu_raw| pcmu_wav|opus, channel}`, `pronunciation_dict`, `timbre_weights`, `language_boost`,
  `subtitle_enable`, `subtitle_type` (sentence|word| word_streaming), `output_format` (`hex|url`). Response
  `data.audio` (hex), `data.status` 1|2, `extra_info{audio_length, usage_characters, ...}`, `base_resp{status_code,
  status_msg}` (1002 rate limit, 1004 auth, 2013 params). Streaming: same shape per chunk;
  `stream_options.exclude_aggregated_audio`.

### 2.11 Local peers: Piper and Kokoro

- Piper (`OHF-Voice/piper1-gpl`, GPL; the original `rhasspy/piper` MIT repo archived 2025-10-06): `pip install
  piper-tts`; `PiperVoice.load(onnx)`, `synthesize(text)` yields chunks with `sample_rate`, `sample_width`,
  `sample_channels`, `audio_int16_bytes`; `SynthesisConfig{volume, length_scale, noise_scale, noise_w_scale,
  normalize_audio, speaker_id}`; HTTP `python3 -m piper.http_server -m <voice>` exposes `POST /synthesize` (JSON
  `text`, `voice`, `speaker`, `length_scale`, ...) returning WAV, plus `GET /voices`, `GET /info`. espeak-ng
  phonemization.
- Kokoro (82M, Apache-2.0, 24 kHz): `KPipeline(lang_code)` yields `(graphemes, phonemes, audio)` per split; voices
  such as `af_heart`. Kokoro-FastAPI exposes OpenAI-compatible `POST /v1/audio/speech` (mp3/wav/opus/flac/aac/pcm,
  streaming), voice mixing `af_bella(2)+af_sky(1)`, and `/dev/captioned_speech` with word timestamps.
- Both fit the port as in-process adapters (`route=None`, `host="in-process"`); the OpenAI-compatible server shape of
  Kokoro-FastAPI means the OpenAI codec can be reused with a different `Binding`.

## 3. Comparison table

| Provider | Transport | Formats (sample rates) | Timing marks | Voice identity | SSML | Limit / request | Unit |
|---|---|---|---|---|---|---|---|
| OpenAI `/audio/speech` | HTTP chunked, SSE | mp3, opus, aac, flac, wav, pcm 24k | none | names + `voice_...` ids | no (`instructions`) | 4096 chars | chars / tokens |
| ElevenLabs | HTTP, HTTP chunked, WS input stream | mp3, pcm 8k-48k, wav, ulaw/alaw 8k, opus | character alignment (HTTP + WS) | `voice_id`, IVC/PVC | WS only (`enable_ssml_parsing`) | 5k-40k by model | chars |
| Google Cloud TTS | HTTP, gRPC bidi | LINEAR16, MP3, OGG_OPUS, MULAW, ALAW | SSML `<mark>` timepoints (v1beta1) | `name`, `customVoice`, `voiceClone` key | yes (not streaming, not Chirp3 streaming) | 5,000 bytes | chars |
| Gemini TTS | HTTP (Interactions), streamed `step.delta` | wav/l16 24k, mulaw/alaw 8k | none | prebuilt names, `voice_...` | no (style metadata, inline tags) | not stated | tokens |
| Azure Speech | HTTP, SDK WebSocket | pcm 8k-48k, mp3, opus, webm, mulaw/alaw, g722 | SDK-only word boundary, viseme, bookmark | `ShortName`, `deploymentId` | yes (required body) | 10 min audio, 64 KB WS | chars |
| Amazon Polly | HTTP | mp3, ogg_vorbis, ogg_opus 48k, pcm 8k/16k, mulaw, alaw | speech marks (separate json request) | `VoiceId` | yes | 3,000 billed / 6,000 | chars |
| Cartesia | HTTP, WS | wav/mp3/raw; pcm f32/s16, mulaw, alaw 8k-48k | word + phoneme (WS) | voice id, clones | no | not stated | unverified |
| Deepgram Aura | HTTP chunked, WS | linear16, mulaw, alaw, mp3, opus, aac, flac | none | model name encodes voice | no | 2,000 chars | chars |
| PlayHT | HTTP stream | mp3, mulaw, wav, ogg, flac | none | manifest URL | no | 2,000 / 20,000 | unverified |
| MiniMax | HTTP, SSE | mp3, pcm, flac, wav, pcmu, opus | subtitles (sentence/word) | `voice_id`, timbre mix | no (markers) | 10,000 chars | chars |
| Piper / Kokoro | in-process, local HTTP | pcm/wav 22k / 24k | Kokoro-FastAPI word timestamps | local voice file | no | n/a | none |

## 4. Canonical IR proposal (`ocai.tts`, revision `2026-11` draft)

Identity: `Capability("tts")`; shapes `("tts","request")`, `("tts","response")`, `("tts","chunk")`. Canonical nodes at
`NodeId("ocai","ocai","2026-11", shape)`.

```
SynthesisRequest(IRObject)
  input:   SpeechInput            # text: str | ssml: str | parts: list[PartText]
  config:  SynthesisConfig
  extensions

SynthesisConfig(IRObject)
  voice:        ProviderRef(kind="voice")      # provider-scoped; never a bare string
  format:       AudioFormat(encoding, sample_rate, channels, bitrate, container)
  speed:        float | None                  # verbatim; out-of-range -> APPROXIMATED
  language:     str | None                    # BCP-47
  instructions: str | None                    # style prompt lane (OpenAI, Gemini, Hume)
  timing:       set[TimingKind] | None        # requested marks: word|sentence|character|viseme|mark|phoneme
  seed:         int | None
  lexicons:     list[ProviderRef(kind="lexicon")]   # pronunciation dictionaries
  provider_options                            # destination-scoped passthrough (three-lane law)

SynthesisResponse(IRObject)
  audio:   PartAudio                # Source = base64 | url | SourceRef; mime + format metadata
  marks:   list[TimingMark]         # TimingMark(kind, text, start_s, end_s | None, offset: TextSpan | None, native)
  finish:  FinishInfo               # complete | truncated (Azure 10-min cut) | error
  usage:   Usage                    # Consumption(unit="characters" | "tokens" | "seconds", ...)
  info:    ResponseInfo             # request id anchors as ProviderRef
```

Decisions:

- **Voice as `ProviderRef`.** `alloy`, `en-US-JennyNeural`, an ElevenLabs `voice_id`, a Google `voiceCloningKey`, a
  Kokoro mix string are all provider-scoped identities. A voice leaving its `(provider, interface)` scope is
  UNSUPPORTED-and-reported; the front door may offer a *voice mapping table* as application data, never a silent
  substitution. The model (`tts-1`, `eleven_flash_v2_5`, `sonic-3`) is the routing resource bound at the front door
  (`ocai.tts.synthesizer("elevenlabs/eleven_flash_v2_5", voice=VoiceRef(...))`), per recipe step 3.
- **SSML.** Native on Google, Azure, Polly; absent on OpenAI, Cartesia, Deepgram, Gemini. `SpeechInput.ssml` is
  first-class (three interfaces with congruent semantics), but every edge to a non-SSML interface declares a
  `SemanticShift("ssml.stripped")` and either fails admission or, if the caller opts in via `provider_options`, strips
  tags with `APPROXIMATED`. Provider-specific markup (`markup` pause tags, MiniMax `<#x#>`, v3 audio tags) rides
  censused extensions.
- **Timing marks** are one open-kind list. Character alignment (ElevenLabs), word timestamps (Cartesia,
  Kokoro-FastAPI), SSML marks (Google, Polly `ssml`), visemes (Azure, Polly) all map onto `TimingMark`; absence is
  reported ABSENT when requested, never faked by estimation.
- **Instructions lane.** OpenAI `instructions`, Gemini `speech_metadata.style` / `prompt`, Hume `description` are
  congruent enough for a first-class `instructions`; ElevenLabs `voice_settings` and Cartesia `generation_config`
  (`emotion`, `volume`) are provider extensions.
- **Format.** `AudioFormat` is an open-code record; the codec maps it to the provider's enum (`mp3_44100_128`,
  `raw-24khz-16bit-mono-pcm`, ...). A combination the provider cannot produce fails admission; nothing is resampled by
  ocai.
- **Usage.** `characters` is the dominant unit (Polly `x-amzn-RequestCharacters`, Deepgram `dg-char-count`, MiniMax
  `usage_characters`); OpenAI `gpt-4o-mini-tts` and Gemini bill tokens; GPT-Live bills seconds. All are open
  `Consumption` units.

## 5. Streaming shape and fold law

`SynthesisChunk(type, seq, delta, end, raw_event)` with `ChunkType` values `audio` (delta `DeltaBlob(bytes)`), `mark`
(delta `DeltaMark(TimingMark)`), `streamStop` carrying `StreamEnd(usage, finish, report)`. `DeltaBlob` is the existing
declared-but-unaccumulated chat delta; this capability gives it its accumulator.

**Fold law (normative):**

```
fold(chunks).audio.bytes == b"".join(c.delta.bytes for c in chunks if c.type == "audio")
fold(chunks).marks       == sorted(rebase(c.delta.mark) for c in chunks if c.type == "mark")
fold(chunks).usage/finish/report == StreamEnd fields
```

and `fold(stream(req)) == complete(req)` **byte-for-byte for the audio payload when the streaming and unary operations
are the same wire operation delivered with chunked transfer** (OpenAI, ElevenLabs `/stream`, Azure, Deepgram REST,
PlayHT): the fixture pair is the recorded chunk sequence and the recorded body. For socket interfaces (ElevenLabs
stream-input, Cartesia, Deepgram WS) there is no unary twin of the same request; the fixture pair is the frame log and
the concatenated bytes, and the edge declares `SemanticShift("stream.no_unary_twin")`. Container formats are only
foldable by concatenation if the provider streams one container (raw PCM, MP3 frames, Ogg pages from one muxer); `wav`
chunks each carrying a RIFF header fail the law and must be declared, which is why `pcm`/`raw` is the recommended
streaming format everywhere. `rebase` converts chunk-relative mark times (ElevenLabs WebSocket `charStartTimesMs`) to
absolute times by accumulating chunk durations; absolute-time marks (Cartesia `start[]`) pass through. Aborted streams
seal `finish.reason = "incomplete"`.

## 6. Priority, effort, first provider

- **Priority P1.** TTS is table stakes for every voice product built on ocai and the simplest audio capability to
  certify (unary HTTP, chunked bytes). Not P0 because chat and embeddings already carry the kernel.
- **Effort:** 3 WUs. (1) IR + port + schemas + fold-triple harness for `DeltaBlob` (reusable by STT and realtime). (2)
  First provider edge with EdgeContract, recorded wire pairs, chunked and timestamped fixtures. (3) Second provider
  for the cross-provider UNSUPPORTED/ABSENT proofs (voice ref scope, SSML shift, marks absence).
- **First provider: ElevenLabs HTTP** (`/v1/text-to-speech/{voice_id}`, `/stream`, `/stream/with-timestamps`). It
  exercises voice `ProviderRef`, per-character marks, chunked fold, pronunciation-dictionary refs, request stitching
  anchors, and per-character billing in one interface, with stable docs. **Second: OpenAI `/v1/audio/speech`** despite
  its 2027-01-06 shutdown, because the mandated successor (`gpt-realtime-2.1-mini` over the Realtime API) is exactly
  the interface-migration proof ocai sells: the `tts` port stays, the edge target changes from a unary HTTP node to a
  session-backed node whose facade owns the fan-in. Third: Google Cloud TTS (SSML + timepoints + gRPC bidi) or
  Deepgram (cheapest WS fixture set).
- Local peers (Piper, Kokoro) land as in-process adapters once the port exists; Kokoro-FastAPI reuses the OpenAI codec
  with a custom host.

## 7. Open questions and unverified items

- OpenAI `stream_format=sse` event names and usage payload (*unverified*).
- ElevenLabs HTTP SSML support and whether `/stream/with-timestamps` times are absolute (*unverified*); Cartesia clone
  API field names (*unverified*).
- Hume TTS availability (see §2.9).
- Gemini `generateContent` TTS path status after the Interactions API move.
- PlayHT WebSocket and pricing units; Deepgram WS text limits.
- Azure word-boundary events are SDK/WebSocket-only; REST gives audio only.

## Sources

Read 2026-11-10 unless stated.

- https://developers.openai.com/api/docs/api-reference/audio/createSpeech
- https://developers.openai.com/api/docs/guides/text-to-speech
- https://developers.openai.com/api/docs/guides/custom-voices
- https://developers.openai.com/api/docs/pricing
- https://elevenlabs.io/docs/api-reference/text-to-speech/convert
- https://elevenlabs.io/docs/api-reference/text-to-speech/stream
- https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
- https://elevenlabs.io/docs/api-reference/text-to-speech/stream-with-timestamps
- https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-stream-input
- https://elevenlabs.io/docs/overview/models
- https://elevenlabs.io/docs/api-reference/voices/ivc/create
- https://elevenlabs.io/docs/api-reference/pronunciation-dictionaries/create-from-file
- https://elevenlabs.io/pricing/api
- https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/text/synthesize
- https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1beta1/text/synthesize
- https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/SynthesisInput
- https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/VoiceSelectionParams
- https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/AudioConfig
- https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/AudioEncoding
- https://docs.cloud.google.com/text-to-speech/docs/reference/rpc/google.cloud.texttospeech.v1beta1
- https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd
- https://docs.cloud.google.com/text-to-speech/docs/chirp3-instant-custom-voice
- https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types
- https://docs.cloud.google.com/text-to-speech/quotas
- https://aistudio.google.com/docs/speech-generation
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis-viseme
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-lower-speech-synthesis-latency
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits
- https://docs.aws.amazon.com/polly/latest/dg/API_SynthesizeSpeech.html
- https://docs.aws.amazon.com/polly/latest/dg/speechmarks.html
- https://docs.aws.amazon.com/polly/latest/dg/output.html
- https://docs.cartesia.ai/api-reference/tts/bytes
- https://docs.cartesia.ai/api-reference/tts/tts
- https://docs.cartesia.ai/build-with-cartesia/capability-guides/clone-voices
- https://developers.deepgram.com/reference/text-to-speech-api/speak
- https://developers.deepgram.com/reference/text-to-speech/speak-streaming
- https://developers.deepgram.com/docs/text-to-speech
- https://developers.deepgram.com/docs/tts-models
- https://deepgram.com/pricing
- https://docs.play.ht/reference/api-generate-tts-audio-stream
- https://dev.hume.ai/changelog (served Audio Decisions content only)
- https://platform.minimax.io/docs/api-reference/speech-t2a-http
- https://github.com/rhasspy/piper
- https://github.com/OHF-Voice/piper1-gpl (README, docs/API_PYTHON.md, docs/API_HTTP.md)
- https://github.com/hexgrad/kokoro
- https://github.com/remsky/Kokoro-FastAPI
