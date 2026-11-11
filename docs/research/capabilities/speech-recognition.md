# Speech recognition (speech-to-text / transcription)

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

**Currency:** researched 2026-11-10 against official provider documentation (URLs in Sources). The surface is
churning: OpenAI shuts down the Whisper / `gpt-4o-transcribe` family on 2027-02-26 in favour of `gpt-transcribe` and
`gpt-live-transcribe`; AssemblyAI retired LeMUR; Deepgram added Flux; Mistral shipped Voxtral Realtime 3. Items marked
*unverified* could not be confirmed on an official page at read time.

## 1. Scope: two modes, one transcript

Every provider exposes the same two modes and they are structurally different wire shapes:

1. **Batch** — a file (upload or URL) in, a transcript out; synchronous (OpenAI, Groq, Azure fast transcription,
   Google `recognize`, ElevenLabs Scribe) or an async job (AssemblyAI, Gladia, Speechmatics, Rev.ai, Amazon
   Transcribe, Azure batch, Google `batchRecognize`), modelled as submit / poll / fetch `Operation`s anchored by
   `ProviderRef(kind="job")` (recipe step 6); the facade owns the polling fan-out and declares it as a `SemanticShift`.
2. **Streaming** — audio frames pushed over a socket, interim and final transcript events pulled back: ocai's first
   duplex session (recipe step 8), sharing its transport primitive with [realtime-voice.md](realtime-voice.md).

Both modes produce one `Transcript`; the fold law (§5) says what a streaming session must fold to.

## 2. Provider survey

### 2.1 OpenAI

- `POST /v1/audio/transcriptions` (multipart): `file` (flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm; 25 MB),
  `model` (`gpt-transcribe` recommended; `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`,
  `gpt-4o-transcribe-diarize` deprecated, shutdown 2027-02-26), `language` / `languages[]`, `prompt`, `keywords[]`,
  `response_format` (`json` default, `text`, `srt`, `verbose_json`, `vtt`, `diarized_json`), `temperature`,
  `timestamp_granularities[]` (`word`, `segment`; `verbose_json` only), `include[]` (`logprobs`), `stream`,
  `chunking_strategy` (`auto` or `server_vad{...}`), `known_speaker_names[]` / `known_speaker_references[]` (max 4).
- Responses: `json` -> `{text, languages[{code}], logprobs[], usage}`; `verbose_json` -> `{language, duration, text,
  words[{word, start, end}], segments[{id, seek, start, end, text, tokens, temperature, avg_logprob,
  compression_ratio, no_speech_prob}], usage}`; `diarized_json` -> `{task, duration, text, segments[{id, start, end,
  text, speaker, type}], usage}`. `usage` is `{type: "tokens", input_tokens, input_token_details{audio_tokens,
  text_tokens}, output_tokens, total_tokens}` or `{type: "duration", seconds}`. Streaming a file (`stream: true`): SSE
  `transcript.text.delta{delta, logprobs}`, `transcript.text.segment`, `transcript.text.done{text, logprobs, usage}`.
- Live audio: Realtime transcription session, `wss://api.openai.com/v1/realtime?intent=transcription`, then
  `session.update` with `session.type = "transcription"`, `audio.input.format{type: "audio/pcm", rate: 24000}` (also
  `audio/pcmu`, `audio/pcma`), `audio.input.transcription{model: "gpt-live-transcribe" | "gpt-transcribe", prompt,
  keywords, languages, delay: minimal|low|medium|high|xhigh}`, `audio.input.turn_detection` (`server_vad{threshold,
  prefix_padding_ms, silence_duration_ms, idle_timeout_ms}`, `semantic_vad{eagerness}`, or `null` for
  `gpt-live-transcribe`), `audio.input.noise_reduction{type: near_field|far_field}`. Client
  `input_audio_buffer.append{audio}`, `.commit`, `.clear`; server `input_audio_buffer.committed{item_id}`,
  `.speech_started{audio_start_ms, item_id}`, `.speech_stopped{audio_end_ms}`,
  `conversation.item.input_audio_transcription.delta{delta}`, `.completed{transcript, languages, usage}`, `.failed`,
  `error`. Completions may arrive out of order (correlate by `item_id`); `gpt-live-transcribe` returns no word
  timestamps, speakers, confidences or language predictions.
- Pricing: Whisper $0.006/min; `gpt-4o-transcribe` $2.50 / 1M audio input tokens (about $0.006/min); mini $1.25.
  `gpt-transcribe` pricing not captured.

### 2.2 Deepgram

- Pre-recorded `POST https://api.deepgram.com/v1/listen` (`Authorization: Token`), body binary or `{"url"}`. Query:
  `model` (`nova-3`, `nova-3-medical`, `nova-2`, `whisper-*`), `language` (`multi` for code-switching),
  `diarize_model` (`latest|v1|v2`; `diarize` deprecated), `punctuate`, `smart_format`, `paragraphs`, `utterances`,
  `utt_split`, `keyterm` (Nova-3), `multichannel`, `numerals`, `profanity_filter`, `redact`, `search`, `replace`,
  `detect_entities`, `sentiment`, `topics`, `intents`, `summarize`, `callback`, `tag`, `encoding`, `sample_rate`.
- Response: `metadata{request_id, model_info, duration, channels, diarize_info{model_uuid, arch}}`,
  `results.channels[].alternatives[]{transcript, confidence, words[{word, start, end, confidence, punctuated_word,
  speaker, speaker_confidence, language}], paragraphs}`, `results.utterances[]` with `speaker` (*partly unverified*).
- Live `wss://api.deepgram.com/v1/listen`: query `model`, `language`, `encoding`, `sample_rate`, `channels`,
  `multichannel`, `interim_results`, `endpointing` (default 10 ms), `utterance_end_ms`, `vad_events`, `smart_format`,
  `punctuate`, `diarize_model`, `keyterm`, `numerals`, `redact`. Client: binary audio, `{"type":"KeepAlive"}`,
  `Finalize`, `CloseStream`, `Configure`. Server: `Results{type, channel_index, duration, start, is_final,
  speech_final, from_finalize, channel.alternatives[]{transcript, confidence, words[{word, start, end, confidence,
  punctuated_word, speaker}]}, metadata}`, `Metadata{request_id, sha256, created, duration, channels}`,
  `UtteranceEnd{channel, last_word_end}`, `SpeechStarted{channel, timestamp}`, `Error{variant, description, message}`.
- Flux (turn-based streaming for agents): `wss://api.deepgram.com/v2/listen`, `model=flux-general-en|flux-general-multi`,
  `encoding` (linear16, linear32, mulaw, alaw, opus, ogg-opus), `eot_threshold` (0.7), `eager_eot_threshold`,
  `eot_timeout_ms` (5000), `keyterm`. Client: binary, `CloseStream`, `ForceEndTurn`, `Configure`. Server:
  `Connected{request_id, sequence_id}`, `TurnInfo{event: StartOfTurn|Update|EagerEndOfTurn|TurnResumed|EndOfTurn,
  turn_index, audio_window_start, audio_window_end, transcript, words[{word, confidence, start, end}],
  end_of_turn_confidence, trigger: model|manual|timeout}`, `Warning`, `FatalError`.
- Pricing: Nova-3 streaming $0.0077/min, pre-recorded $0.0043/min (multilingual higher).

### 2.3 AssemblyAI

- `POST https://api.assemblyai.com/v2/transcript` (`authorization` header; EU host `api.eu.assemblyai.com`):
  `audio_url` (required), `speech_models` (`universal-3-5-pro`, `universal-2`), `language_code` /
  `language_detection`, `speaker_labels`, `speakers_expected`, `punctuate`, `format_text`, `disfluencies`,
  `multichannel`, `keyterms_prompt`, `custom_spelling`, `prompt` (Universal-3.5 Pro), `filter_profanity`,
  `redact_pii*`, `sentiment_analysis`, `entity_detection`, `audio_start_from` / `audio_end_at` (ms), `webhook_url`.
- Transcript object: `id`, `status` (`queued|processing|completed|error`), `text`, `words[{text, start, end,
  confidence, speaker}]` (ms), `utterances[{text, start, end, confidence, speaker, words}]`, `confidence`,
  `audio_duration`, `language_code`, `error`. Poll `GET /v2/transcript/{id}` or webhook. File limits *unverified*.
- Streaming v3 `wss://streaming.assemblyai.com/v3/ws` (`Authorization` key header, or `token` query from a
  temporary-token endpoint; regional hosts): query `sample_rate` (8000-96000), `encoding` (`pcm_s16le`, `pcm_mulaw`,
  `opus`, `ogg_opus`, `aac`), `format_turns`, `end_of_turn_confidence_threshold`, `min_turn_silence`,
  `max_turn_silence`, `keyterms_prompt`, `language_detection`, `speaker_labels`. Default model `universal-3-6-pro`.
  Client: binary 20-1000 ms chunks, `UpdateConfiguration`, `ForceEndpoint`, `KeepAlive`, `Terminate`. Server:
  `Begin{id, expires_at}`, `Turn{turn_order, turn_is_formatted, end_of_turn, transcript, end_of_turn_confidence,
  words[{text, start, end, confidence, word_is_final}], utterance}`, `SpeechStarted`, `SpeakerRevision`, `Heartbeat`,
  `Termination{audio_duration_seconds, session_duration_seconds}`. 3-hour session max.
- LeMUR is **retired** (sunset 2026-03-31 per AssemblyAI's migration FAQ); the replacement is the OpenAI-compatible
  LLM Gateway (`https://llm-gateway.assemblyai.com/v1/chat/completions`), a chat capability, not transcription.

### 2.4 Google Cloud Speech-to-Text v2

- `POST https://speech.googleapis.com/v2/{recognizer}:recognize` (`projects/{p}/locations/{l}/recognizers/_`, OAuth
  `cloud-platform`). Body: `config` (`RecognitionConfig`: `autoDecodingConfig` or `explicitDecodingConfig{encoding:
  LINEAR16, MULAW, ALAW, AMR, AMR_WB, FLAC, MP3, OGG_OPUS, WEBM_OPUS, MP4_AAC, M4A_AAC, MOV_AAC; sampleRateHertz;
  audioChannelCount}`, `model` (`chirp_3`, `latest_short`, ...), `languageCodes[]` (`["auto"]` detects),
  `features{profanityFilter, enableWordTimeOffsets, enableWordConfidence, enableAutomaticPunctuation,
  multiChannelMode: SEPARATE_RECOGNITION_PER_CHANNEL, diarizationConfig{minSpeakerCount, maxSpeakerCount} ("not
  currently used"), maxAlternatives 0-30}`, `adaptation`, `translationConfig`, `denoiserConfig`), `configMask`,
  `content` (base64) or `uri` (gs://). Response: `results[{alternatives[{transcript, confidence, words[{startOffset,
  endOffset, word, confidence, speakerLabel}]}], channelTag, resultEndOffset, languageCode}]`, `metadata{requestId,
  totalBilledDuration}`.
- `StreamingRecognize` (gRPC bidi only): first message `streaming_config{config, config_mask,
  streaming_features{enable_voice_activity_events, interim_results, voice_activity_timeout{speech_start_timeout,
  speech_end_timeout}}}`, then `audio` (25 KB max per message). Responses: `results[{alternatives, is_final,
  stability, result_end_offset, channel_tag, language_code}]`, `speech_event_type` (`SPEECH_ACTIVITY_BEGIN`,
  `SPEECH_ACTIVITY_END`, `END_OF_SINGLE_UTTERANCE`), `speech_event_offset`, `metadata`. `BatchRecognize` (15 files)
  for long audio. Chirp 3: `recognize` under 1 min, `batchRecognize` up to 1 h (20 min with word timestamps),
  streaming with utterance-level timestamps; word confidence "isn't truly a confidence score"; `us`/`eu`.

### 2.5 Azure Speech (Foundry Tools)

- Fast transcription (synchronous): `POST https://{resource}.cognitiveservices.azure.com/speechtotext/transcriptions:transcribe?api-version=2025-10-15`,
  multipart `audio` (or `{"audioUrl"}` in the definition) + `definition` JSON `{locales[], diarization{enabled,
  maxSpeakers}, channels[], phraseList{phrases[]}, profanityFilterMode: None|Masked|Removed|Tags}`. Response
  `{durationMilliseconds, combinedPhrases[{channel, text}], phrases[{channel, speaker, offsetMilliseconds,
  durationMilliseconds, text, words[{text, offsetMilliseconds, durationMilliseconds}], locale, confidence}]}`. Audio
  under 5 h / 500 MB; 600 requests/min shared with batch. Models: Azure Transcribe, Azure LLM Speech, `MAI-Transcribe-2`.
- Batch: `POST .../speechtotext/transcriptions:submit?api-version=2024-11-15` with `contentUrls[]` or
  `contentContainerUrl`, `locale`, `displayName`, `model{self}`, `properties{wordLevelTimestampsEnabled,
  displayFormWordLevelTimestampsEnabled, diarizationEnabled, diarization{speakers{minCount, maxCount}} (< 36),
  punctuationMode, profanityFilterMode, channels[], destinationContainerUrl, timeToLiveHours (6 h-31 d),
  languageIdentification{candidateLocales[], mode}}`. Status `NotStarted|Running|Succeeded|Failed`; `GET .../files`
  lists `kind: Transcription|TranscriptionReport`. Result JSON: `combinedRecognizedPhrases[{channel, lexical, itn,
  maskedITN, display}]`, `recognizedPhrases[{recognitionStatus, channel, speaker, offset, duration, offsetInTicks,
  nBest[{confidence, lexical, itn, maskedITN, display, displayWords[], words[{word, offset, duration, confidence}]}],
  locale}]`. 1 GB per file, 1,000 files per request, 240 min with diarization.
- Real-time: Speech SDK only (undocumented WebSocket protocol) or the REST short-audio endpoint; not reachable under
  the no-SDK rule except via REST. `mai-transcribe-2-streaming` is exposed through Voice Live (realtime page).

### 2.6 Amazon Transcribe

- Batch `StartTranscriptionJob` (SigV4): `TranscriptionJobName`, `Media{MediaFileUri}` (S3), `MediaFormat` (mp3,
  mp4, wav, flac, ogg, amr, webm, m4a), `MediaSampleRateHertz` 8000-48000, one of `LanguageCode` |
  `IdentifyLanguage` | `IdentifyMultipleLanguages`, `OutputBucketName`/`OutputKey`, `Settings{ShowSpeakerLabels,
  MaxSpeakerLabels, ChannelIdentification, ShowAlternatives, MaxAlternatives, VocabularyName, VocabularyFilterName}`,
  `ContentRedaction`, `Subtitles{Formats: srt|vtt}`, `ToxicityDetection`. Response `TranscriptionJob
  {TranscriptionJobStatus: QUEUED|IN_PROGRESS|COMPLETED|FAILED, Transcript{TranscriptFileUri}, FailureReason}`.
  Output JSON: `results.transcripts[{transcript}]`, `results.items[{id, start_time, end_time,
  alternatives[{confidence, content}], type: pronunciation|punctuation, speaker_label}]`,
  `results.audio_segments[{id, transcript, start_time, end_time, items[]}]`. Quotas *unverified*.
- Streaming `StartStreamTranscription` over HTTP/2 event stream or WebSocket (SigV4 presigned): headers
  `x-amzn-transcribe-language-code`, `-sample-rate` (8000-48000), `-media-encoding` (`pcm|ogg-opus|flac`),
  `-show-speaker-label`, `-enable-channel-identification` + `-number-of-channels` (2),
  `-enable-partial-results-stabilization` + `-partial-results-stability` (`low|medium|high`), PII redaction, language
  identification, vocabularies, `-session-id`, `-session-resume-window` (1-300 min), `-transcript-format`
  (`spoken|written`). Client `AudioEvent{AudioChunk}` (50-200 ms chunks). Server `TranscriptEvent{Transcript{Results[
  {ResultId, StartTime, EndTime, IsPartial, Alternatives[{Transcript, Items[{StartTime, EndTime, Type, Content, Speaker,
  Confidence, Stable}]}], ChannelId, LanguageCode}]}}`; errors 400 `BadRequestException`, 409 `ConflictException`,
  429 `LimitExceededException`, 503 `ServiceUnavailableException`.

### 2.7 Gladia

- `POST https://api.gladia.io/v2/pre-recorded` (`x-gladia-key`): `audio_url`, `model` (`solaria-1` default, async +
  live; `solaria-3` async, 5 languages), `diarization` + `diarization_config{number_of_speakers, min_speakers,
  max_speakers}`, `language_config{languages[], code_switching}`, `translation`, `subtitles`, `summarization`,
  `custom_vocabulary`, `pii_redaction`, `sentences`, `named_entity_recognition`, `callback_config{url, method}`.
  201 -> `{id, result_url}`; the `GET /v2/pre-recorded/{id}` result schema is *unverified* (not on the read page).
- Live: `POST /v2/live` with `model`, `encoding` (`wav/pcm`), `sample_rate`, `bit_depth`, `channels` (up to 8),
  `language_config`, `messages_config{receive_partial_transcripts}` -> `{id, url}` (reconnectable). Client: binary or
  `{"type":"audio_chunk","data":{"chunk": base64}}`, `{"type":"stop_recording"}`. Server `transcript{type, session_id,
  data{id, is_final, utterance{text, start, end, language, channel}}}`; partials share `data.id` and replace earlier
  text. 3-hour session; `GET /v2/live/{id}` for the result.

### 2.8 Speechmatics

- Batch `POST https://eu1.asr.api.speechmatics.com/v2/jobs` (Bearer), multipart `data_file` or
  `config.fetch_data{url}` + `config` JSON `{type: "transcription", transcription_config{language, output_locale,
  model|operating_point: standard|enhanced|melia-1, additional_vocab[{content, sounds_like}], punctuation_overrides,
  diarization: none|speaker|channel, speaker_diarization_config{speaker_sensitivity, speakers[{label,
  speaker_identifiers}]}, enable_entities}, notification_config[], summarization_config, translation_config, ...}`.
  201 `{id}`; status `created|done|rejected|deleted`. `GET /v2/jobs/{id}/transcript?format=json-v2|txt|srt` returns
  `{format, job{id, duration}, metadata{transcription_config, language_pack_info{word_delimiter, writing_direction}},
  results[{type: word|punctuation|entity, start_time, end_time, channel, is_eos, attaches_to, alternatives[{content,
  confidence, language, speaker, display{direction}}]}], speakers, ...}`. Speaker labels `S1`, `S2`, ...
- Real-time `wss://global.rt.speechmatics.com/v2/` (Bearer or `?jwt=`): `StartRecognition{audio_format{type:
  raw|file, encoding: pcm_s16le|pcm_f32le|mulaw, sample_rate}, transcription_config{language, enable_partials,
  max_delay, diarization, additional_vocab}}`, binary `AddAudio`, `EndOfStream{last_seq_no}`. Server
  `RecognitionStarted{id}`, `AudioAdded{seq_no}`, `AddPartialTranscript`, `AddTranscript{metadata{start_time,
  end_time, transcript}, results[...]}` (batch item shape), `EndOfTranscript`, `Error{type, reason}`; codes 4001-4013.

### 2.9 Rev.ai

- Async `POST https://api.rev.ai/speechtotext/v1/jobs` (Bearer): `media_url`, `source_config{url, auth_headers}` or
  multipart media (2 GB); `transcriber` (`machine|human`), `language`, `skip_diarization`, `speaker_channels_count`,
  `speakers_count`, `diarization_type` (`standard|premium`), `skip_punctuation`, `remove_disfluencies`,
  `filter_profanity`, `custom_vocabularies`, `custom_vocabulary_id`, `delete_after_seconds`, `notification_config`;
  human-only `verbatim`, `rush`. Status `in_progress|transcribed|failed`. `GET /jobs/{id}/transcript` with `Accept:
  application/vnd.rev.transcript.v1.0+json` returns `{monologues[{speaker, elements[{type: text|punct|unknown, value,
  ts, end_ts, confidence}]}]}`; captions `application/x-subrip` / `text/vtt`. 17 h max; billed per second.
- Streaming `wss://api.rev.ai/speechtotext/v1/stream?access_token=...&content_type=audio/x-raw;layout=interleaved;rate=16000;format=S16LE;channels=1`
  plus `language`, `custom_vocabulary_id`, `detailed_partials`, `enable_speaker_switch`, `max_segment_duration_seconds`.
  Binary audio in; JSON `{"type": "connected"}` then `partial` / `final` hypotheses (fields *unverified*); 3 h/stream.

### 2.10 Groq (Whisper)

- `POST https://api.groq.com/openai/v1/audio/transcriptions` (OpenAI-compatible): `file` | `url`, `model`
  (`whisper-large-v3` $0.111/h, `whisper-large-v3-turbo` $0.04/h), `language`, `prompt`, `response_format`
  (`json|verbose_json|text`), `timestamp_granularities[]`. 25 MB free / 100 MB dev tier. Reuses the OpenAI codec.

### 2.11 Mistral Voxtral

- Batch: `POST https://api.mistral.ai/v1/audio/transcriptions` (path inferred from the documented base URL): `file` |
  `file_url`, `model` (`voxtral-mini-latest` = Voxtral Mini Transcribe 2; up to 3 h per request), `language` (not
  combinable with `timestamp_granularities`), `timestamp_granularities` (`segment|word`), `diarize`, `context_bias`,
  `stream`. Response `text` plus timestamped segments (field names *unverified*). 13 languages.
- Realtime `wss://api.mistral.ai/v1/audio/transcriptions/realtime?model=voxtral-mini-transcribe-realtime-3` (Bearer):
  client `session.update` (`audio_format.sample_rate`, `target_streaming_delay_ms` 80-1200 or 2400, `diarize`,
  `turn_detection`), `input_audio.append{audio: base64}`, `input_audio.end`. Server `session.created|updated`,
  `transcription.text.delta{text}` (append-only), `transcription.segment{text, speaker_id, start, end}` (diarized),
  `turn.start|eager_end|resume|end`, `transcription.done{text, segments, language, model, usage}`, `error`.

### 2.12 ElevenLabs Scribe

- `POST https://api.elevenlabs.io/v1/speech-to-text` (multipart, `xi-api-key`): `model_id` (example `scribe_v2`; v3
  API ids *unverified*), `file` | `source_url` (5 GB / 2 GB; up to 15 h), `language_code`, `tag_audio_events`,
  `num_speakers` (32), `diarize`, `timestamps_granularity` (`word|character`), `additional_formats[]`,
  `file_format` (`pcm_s16le_16|other`), `webhook*`, `use_multi_channel` (5), `keyterms` (1,000),
  `entity_detection/redaction`. Response `{language_code, language_probability, text, words[{text, type:
  word|spacing|audio_event, start, end, logprob, speaker_id, characters, channel_index}], transcription_id,
  audio_duration_secs}`; multichannel returns `transcripts[]`.
- Realtime (Scribe v3 Live / v2 Realtime) is WebSocket-based with silence VAD committing segments and draft speaker
  labels on partials; endpoint and message schema *unverified*. Pricing $0.20/h batch, $0.22/h realtime.

### 2.13 Local peers: whisper.cpp and faster-whisper

- whisper.cpp (MIT, ggml models): `whisper-server` exposes an OpenAI-like `POST /inference`, `whisper-stream` for
  microphones, experimental word timestamps (`-ml 1`) and tinydiarize `[SPEAKER_TURN]` markers. faster-whisper (MIT,
  CTranslate2): `WhisperModel(size, device, compute_type)`, `transcribe(audio, beam_size, language, vad_filter,
  word_timestamps)` yields segments (`start`, `end`, `text`, `words[{start, end, word}]`) plus `info{language,
  language_probability}`. Both are batch-only in-process adapters; windowed "streaming" is not the streaming port.

## 3. Comparison table

| Provider | Batch | Streaming | Diarization | Word times | Confidence | Interim events | Unit |
|---|---|---|---|---|---|---|---|
| OpenAI | sync HTTP (+SSE) | WS realtime session | `diarized_json` (deprecated model) | `verbose_json` (deprecated) | logprobs | `...transcription.delta` | tokens / seconds |
| Deepgram | sync HTTP | WS (+Flux turns) | `diarize_model` | yes (s) | yes | `is_final` / `speech_final` | minutes |
| AssemblyAI | async job | WS v3 | `speaker_labels` | yes (ms) | yes | `Turn.end_of_turn` | hours |
| Google v2 | sync / batch job | gRPC bidi | `diarizationConfig` | `enableWordTimeOffsets` | optional | `is_final`, `stability` | billed duration |
| Azure | sync fast / async batch | SDK only | `diarization` | yes (ms / ticks) | yes | n/a | hours |
| Amazon | async job | HTTP/2, WS | `ShowSpeakerLabel` | yes (s) | yes | `IsPartial`, `Stable` | seconds |
| Gladia | async job | WS | `diarization` | yes | yes | `is_final` + shared `data.id` | minutes |
| Speechmatics | async job | WS | `diarization: speaker` | yes | yes | `AddPartialTranscript` | hours |
| Rev.ai | async job | WS | `diarization_type` | yes (`ts`) | yes | `partial` / `final` | seconds |
| Groq | sync HTTP | none | none | yes | Whisper metrics | none | hours |
| Mistral | sync HTTP | WS | `diarize` | segment/word | none stated | append-only deltas + turns | minutes |
| ElevenLabs | sync HTTP / webhook | WS (unverified) | up to 32 | word/char | logprob | partial vs committed | hours |
| whisper.cpp / faster-whisper | in-process | none | none / turn markers | yes | Whisper metrics | none | none |

## 4. Canonical IR proposal (`ocai.transcription`, revision `2026-11` draft)

Identity: `Capability("transcription")`; shapes `("transcription","request")`, `("transcription","response")`,
`("transcription","stream.request")`, `("transcription","chunk")`, plus `("transcription","job")` for async legs.

```
TranscriptionRequest(IRObject)
  audio:    PartAudio                     # Source = base64 | url | SourceRef (provider upload id)
  config:   TranscriptionConfig
  extensions

TranscriptionConfig(IRObject)
  languages:    list[str] | None          # BCP-47; [] = detect
  diarize:      DiarizationConfig | None  # enabled, min_speakers, max_speakers, known_speakers: list[ProviderRef]
  timestamps:   set[TimestampKind] | None # segment | word | character
  prompt:       str | None                # context / style prompt
  vocabulary:   list[str] | ProviderRef   # keyterms inline, or a provider lexicon ref (Amazon, Rev.ai, Speechmatics)
  channels:     ChannelMode | None        # mixed | separate
  punctuate / smart_format: bool | None; provider_options

Transcript(IRObject)
  text: str; language: str | None; duration_s: float | None
  segments:  list[Segment]                # Segment(id, start_s, end_s, text, speaker, confidence, channel,
                                          #         words: list[Word], language, native)
  speakers:  list[Speaker] | None         # Speaker(label, ref: ProviderRef | None)
  finish: FinishInfo; usage: Usage (unit = seconds | tokens | ...); info: ResponseInfo
  extensions                              # alternatives (nBest), logprobs, entities, sentiment, ...

Word = (text, start_s, end_s, confidence | None, speaker | None, kind: word | punctuation | audio_event | spacing)
```

Decisions:

- **One transcript, segments-first.** Every provider has a segment-like unit (OpenAI segments, Deepgram and
  AssemblyAI utterances, Azure phrases, Amazon audio_segments, Speechmatics `is_eos` items, Rev.ai monologues);
  `text` is derived but stored (join rules differ; Speechmatics publishes `word_delimiter`).
- **Times in seconds as floats**, converted from ms (AssemblyAI, Azure) and ticks (Azure 100 ns) by the codec with
  the native value preserved in `native`; never rounded beyond the source precision.
- **Speakers are open string labels** (`A`, `0`, `S1`, `agent`) with an optional `ProviderRef` for identified
  speakers (OpenAI known speakers, Speechmatics `speaker_identifiers`); relabelling is a `SemanticShift`, never silent.
- **Confidence is optional and provider-defined** (Chirp 3's "isn't truly a confidence score"; OpenAI gives logprobs);
  nothing is rescaled; logprobs and `nBest` alternatives ride censused extensions.
- **Async jobs** are `Operation`s: `submit -> CallResult[JobHandle]`, `poll -> CallResult[JobStatus]`,
  `fetch -> CallResult[Transcript]`, each with its own `Route`; the facade's `transcribe()` composes them and reports
  the fan-out. Subtitle formats (srt, vtt) are views derived from segments; native srt stays in `raw`.

## 5. Streaming shape and fold law

Streaming is a session: the client pushes `AudioFrame(bytes, t_ms)` (plus `commit` / `end` controls) and receives
`TranscriptChunk`s:

```
TranscriptChunk(type, seq, segment: Segment | None, delta: DeltaText | None,
                event: SpeechEvent | None, end: StreamEnd | None, raw_event)
ChunkType: interim | final | speech_started | speech_ended | turn_end | revision | streamStop
```

`interim` carries a provisional `Segment` (same `id` as the final it precedes when the provider correlates them:
Gladia `data.id`, AssemblyAI `turn_order`, OpenAI `item_id`, Amazon `ResultId`); `final` the committed segment;
`revision` (AssemblyAI `SpeakerRevision`, Deepgram `from_finalize`) re-emits a final segment by id; `delta` serves
append-only providers (OpenAI, Mistral). `StreamEnd(usage, finish, report)` closes the session.

**Fold law (normative):**

```
finals = last-wins-by-id([c.segment for c in chunks if c.type in {final, revision}])
fold(chunks).segments == sorted(finals, key=(start_s, seq))
fold(chunks).text     == join(seg.text for seg in segments)     # join rule declared per edge
fold(chunks).usage / finish / report == StreamEnd fields
interim chunks never survive the fold; a stream aborted before StreamEnd seals finish.reason = "incomplete"
```

`fold(stream(session)) == complete(request)` is **not** claimed across modes (streaming and batch models differ); the
paired fixtures for a streaming edge are the recorded frame log and the provider's own end-of-session transcript where
one exists (Gladia `GET /v2/live/{id}`, Mistral `transcription.done`), otherwise the folded transcript with the join
rule asserted. PART_STOP analogue: a `final` segment's `text` equals the accumulation of its `delta`s.

## 6. Priority, effort, first provider

- **Priority P1 for batch, P2 for streaming.** Batch transcription is the most-used audio capability for enterprise
  workloads (meetings, calls, compliance) and is unary HTTP or a job port, both already modelled by the kernel.
  Streaming is P2 because it introduces the duplex transport primitive; it should land before realtime voice.
- **Effort:** 5 WUs. (1) IR + schemas + `Transcript` conformance. (2) Batch edge for the first provider with recorded
  pairs and diarization fixtures. (3) Async `Job` operations + facade polling with one job-based provider. (4)
  `DuplexTransport` + streaming chunk union + fold-triple harness. (5) Second streaming provider (interim/final proof).
- **First provider: Deepgram.** One vendor covers both modes with explicit, stable JSON (`words[]` with
  `start`/`end`/`confidence`/`speaker`, `is_final`/`speech_final`), per-minute billing, a small fixture surface, and a
  WebSocket protocol documented for third-party clients (Azure's is not). **Second: OpenAI `gpt-transcribe`** for the
  ubiquitous OpenAI-compatible shape (reused by Groq and local servers) and because the `whisper-1` to
  `gpt-transcribe` shutdown is another migration proof. **Third: AssemblyAI** (job port + turn-based streaming).

## 7. Open questions and unverified items

- OpenAI `gpt-transcribe` pricing and whether word timestamps survive the deprecation of `verbose_json`-only models;
  Deepgram, AssemblyAI and Amazon Transcribe file/duration quotas.
- Gladia result schema; Rev.ai streaming element fields; ElevenLabs realtime Scribe endpoint and v3 model ids; Mistral
  batch response fields; Google v2 diarization availability per method (the Chirp 3 page is inconsistent).

## Sources

Read 2026-11-10.

- https://developers.openai.com/api/docs/api-reference/audio/createTranscription
- https://developers.openai.com/api/docs/guides/speech-to-text
- https://developers.openai.com/api/docs/guides/realtime-transcription
- https://developers.openai.com/api/docs/guides/realtime-vad
- https://developers.openai.com/api/docs/pricing
- https://developers.deepgram.com/reference/speech-to-text-api/listen
- https://developers.deepgram.com/reference/speech-to-text-api/listen-streaming
- https://developers.deepgram.com/reference/speech-to-text/listen-flux.md
- https://developers.deepgram.com/docs/diarization.md
- https://developers.deepgram.com/docs/models-languages-overview
- https://deepgram.com/pricing
- https://www.assemblyai.com/docs/api-reference/transcripts/submit
- https://www.assemblyai.com/docs/api-reference/streaming-api/streaming-api
- https://assemblyai.com/docs/faq/how-do-i-switch-from-lemur-to-llm-gateway
- https://docs.cloud.google.com/speech-to-text/v2/docs/reference/rest/v2/projects.locations.recognizers/recognize
- https://docs.cloud.google.com/speech-to-text/v2/docs/reference/rpc/google.cloud.speech.v2
- https://docs.cloud.google.com/speech-to-text/v2/docs/streaming-recognize
- https://docs.cloud.google.com/speech-to-text/v2/docs/chirp_3-model
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/fast-transcription-create
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/batch-transcription-create
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/batch-transcription-get
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits
- https://docs.aws.amazon.com/transcribe/latest/APIReference/API_StartTranscriptionJob.html
- https://docs.aws.amazon.com/transcribe/latest/APIReference/API_streaming_StartStreamTranscription.html
- https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html
- https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html
- https://docs.gladia.io/api-reference/v2/pre-recorded/init
- https://docs.gladia.io/chapters/live-stt/getting-started
- https://docs.speechmatics.com/api-ref/batch/create-a-new-job
- https://docs.speechmatics.com/api-ref/batch/get-the-transcript-for-a-transcription-job
- https://docs.speechmatics.com/rt-api-ref
- https://docs.rev.ai/api/asynchronous/
- https://docs.rev.ai/_bundle/api/asynchronous/reference.yaml
- https://docs.rev.ai/api/streaming/
- https://console.groq.com/docs/speech-to-text
- https://docs.mistral.ai/studio/audio/speech_to_text/offline_transcription
- https://docs.mistral.ai/studio/audio/speech-to-text/transcribe-in-realtime
- https://elevenlabs.io/docs/api-reference/speech-to-text/convert
- https://elevenlabs.io/docs/research/capabilities/speech-to-text
- https://elevenlabs.io/pricing/api
- https://github.com/ggml-org/whisper.cpp
- https://github.com/SYSTRAN/faster-whisper
