# Realtime duplex voice

**Currency:** researched 2026-11-10 against official provider documentation
(URLs in Sources). This is the fastest-moving surface in the survey: OpenAI renamed its Realtime events at GA and
added a separate full-duplex product (GPT-Live, `/v1/live/sessions`); Gemini's Live API is still "preview" with
`gemini-3.8-live` models; Azure Voice Live wraps OpenAI's event protocol; Hume EVI could not be verified as available.
Items marked *unverified* could not be confirmed on an official page at read time. The archived
`docs/plans/archive/v1.4-realtime-duplex.md` plan (DuplexTransport port, RealtimeSession port, canonical event union,
middleware over sessions) is the intended shape; this page replaces its provider assumptions.

## 1. What is being modelled

A **session** over a bidirectional transport (WebSocket, WebRTC data channel + media tracks, HTTP/2 event stream, SIP)
in which the client streams audio (and optionally text, images, tool results) and the provider streams audio,
transcripts, tool calls, turn boundaries and usage. Two provider families:

- **Speech-to-speech models** that own the whole loop: OpenAI Realtime (`gpt-realtime-2.1`), OpenAI GPT-Live
  (`gpt-live-1`, full duplex), Gemini Live (`gemini-3.8-live`), Amazon Nova 2 Sonic, Hume EVI (status unverified).
- **Composed agents** that chain STT, an LLM and TTS behind one socket and expose the composition as data: Deepgram
  Voice Agent (`listen` / `think` / `speak` providers), ElevenLabs Agents, Azure Voice Live (cascade or native-audio
  models with Azure STT/TTS).

The orchestration frameworks (LiveKit Agents, Pipecat, Daily) are the third tier: they *consume* both families plus
standalone STT/TTS and own turn detection, interruption and telephony. They are what an ocai-based platform would use;
the kernel's job is the provider wire (§6).

## 2. Provider survey

### 2.1 OpenAI Realtime API (GA)

- Transports: WebSocket (`wss://api.openai.com/v1/realtime`, server side), WebRTC (`POST /v1/realtime/calls` with an
  SDP offer, `Content-Type: application/sdp`, bearer = ephemeral key from `POST /v1/realtime/client_secrets` with body
  `{"session": {"type": "realtime", "model": ..., "audio": {...}}}` returning `value`; data channel `oai-events`;
  audio on media tracks), SIP (guide page returned 404 at read time; call-control endpoint names *unverified*). GA
  removed the `OpenAI-Beta: realtime=v1` header.
- Session config (`session.update`): `type: "realtime" | "transcription"`, `model` (`gpt-realtime-2.1`: 128k context,
  32k max output, text/audio/image in, text/audio out; $32 / 1M audio input tokens, $64 / 1M audio output, $0.40
  cached), `instructions`, `output_modalities` (audio or text, not both), `audio.input{format{type: audio/pcm rate
  24000 | audio/pcmu | audio/pcma}, noise_reduction{type: near_field|far_field, strength}, transcription{model,
  prompt, language, languages, keywords, delay}, turn_detection: server_vad{threshold, prefix_padding_ms,
  silence_duration_ms, create_response, interrupt_response, idle_timeout_ms 5000-30000} | semantic_vad{eagerness:
  low|medium|high|auto, create_response, interrupt_response} | null}`, `audio.output{format, voice, speed 0.25-1.5}`,
  `tools`, `tool_choice`, `max_output_tokens` (1-4096 or `inf`), `truncation` (`auto|disabled`; `retention_ratio`
  *unverified*), `tracing`, `include`, `prompt`. Voice cannot change after the first audio output. Session max 60
  minutes.
- Client events: `session.update`, `input_audio_buffer.append{audio}` (15 MiB max), `input_audio_buffer.commit`,
  `input_audio_buffer.clear`, `conversation.item.create{item, previous_item_id}`,
  `conversation.item.retrieve{item_id}`, `conversation.item.truncate{item_id, content_index: 0, audio_end_ms}`,
  `conversation.item.delete{item_id}`, `response.create{response{conversation: auto|none, input[], instructions,
  metadata, output_modalities, tools, tool_choice, max_output_tokens, audio}}`, `response.cancel{response_id}`,
  `output_audio_buffer.clear` (WebRTC/SIP only).
- Server events: `error`, `session.created`, `session.updated`, `conversation.created`,
  `conversation.item.created|added|done|retrieved| truncated|deleted`,
  `conversation.item.input_audio_transcription.delta| completed|failed|segment`,
  `input_audio_buffer.committed|cleared| speech_started{audio_start_ms, item_id}|speech_stopped{audio_end_ms}|
  timeout_triggered`, `response.created`, `response.output_item.added|done`, `response.content_part.added|done`,
  `response.output_text.delta|done`, `response.output_audio_transcript.delta|done`, `response.output_audio.delta|
  done`, `response.function_call_arguments.delta|done`, `response.done` (`response.status:
  completed|cancelled|failed|incomplete|in_progress`, `status_details`, `usage{input_tokens, output_tokens,
  total_tokens, input_token_details, output_token_details}`), `rate_limits.updated`,
  `mcp_list_tools.in_progress|completed|failed`, `output_audio_buffer. cleared` (WebRTC).
  `output_audio_buffer.started|stopped` and `response.mcp_call*` names *unverified* on the read pages.
- Interruption: on `input_audio_buffer.speech_started` the server cancels the active response (`response.done` with
  `status: cancelled`). WebRTC/SIP truncate unplayed audio server-side; WebSocket clients must stop playback and send
  `conversation.item.truncate` with the heard `audio_end_ms` (transcript truncation "is not precise"). Push-to-talk
  uses `response.cancel` + `output_audio_buffer.clear`.
- Tools: declared in `session.tools` / `response.tools`; the model emits a `function_call` output item (`name`,
  `arguments`, `call_id`) streamed via `response.function_call_arguments.delta|done` and completed in `response.done`;
  client answers with `conversation.item.create{item{type: "function_call_output", call_id, output}}` then
  `response.create`. Out-of-band responses (`conversation: "none"`, `metadata`, `input[]`) run side tasks without
  touching the default conversation.
- Transcript: user side from `conversation.item.input_audio_transcription.*` (only if `audio.input.transcription` is
  set; it runs a separate model and may complete out of order), assistant side from
  `response.output_audio_transcript.*` and `response.output_text.*`, truncated by `conversation.item.truncate`.

### 2.2 OpenAI GPT-Live (`gpt-live-1`, `/v1/live/sessions`)

A separate product: a full-duplex model that "can listen while speaking" and delegates reasoning and tools to a
backend (Responses delegation run by OpenAI, or client delegation to any agent). Session created server-side (`POST
/v1/live/sessions` with `session{model: "gpt-live-1"}` and `transport{type: "webrtc", sdp}` -> 201 with `session.id`,
`transport.sdp`); client waits for `session.started`, ends with `session.close` -> `session.closed`. Billed $0.05 per
minute of session (per second, 15 s charged at creation), backend usage separate; concurrency 50-500 sessions by tier.
Custom voices (`session.audio.output.voice = {"id": ...}`), prompt-to- voice only here. Event vocabulary beyond
`session.*` *unverified*. This is where OpenAI points both deprecated TTS and translation users.

### 2.3 Gemini Live API (preview)

- `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`
  (API key for server-to-server; ephemeral tokens for client-to-server). Models: `gemini-3.8-live`,
  `gemini-3.8-live-extended-thinking`, `gemini-3.1-flash-live-preview`,
  `gemini-2.5-flash-native-audio-preview-12-2025`. Audio in `audio/pcm;rate=16000` (16-bit LE mono), out 24 kHz PCM;
  video as JPEG/PNG frames at <= 1 fps; native audio models output `AUDIO` only.
- Client messages: `BidiGenerateContentSetup{model, generationConfig {responseModalities,
  speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName, temperature, thinkingConfig}, systemInstruction, tools,
  realtimeInputConfig {automaticActivityDetection{disabled, startOfSpeechSensitivity, endOfSpeechSensitivity,
  prefixPaddingMs, silenceDurationMs}, activityHandling, turnCoverage: TURN_INCLUDES_AUDIO_ACTIVITY_AND_ALL_VIDEO |
  TURN_INCLUDES_ONLY_ACTIVITY, interimTranscriptTimestampEnabled}, sessionResumption{handle},
  contextWindowCompression{slidingWindow {targetTokens}, triggerTokens}, inputAudioTranscription{customVocabulary},
  outputAudioTranscription, proactivity{proactiveAudio}, historyConfig, labels}` (first and only first message; wait
  for `setupComplete`), `BidiGenerateContentClientContent{turns, turnComplete}` (interrupts generation),
  `BidiGenerateContentRealtimeInput{audio{data, mimeType}, video, text, activityStart, activityEnd, audioStreamEnd}`,
  `BidiGenerateContentToolResponse{functionResponses[{id, name, response}]}`.
- Server messages (one of, plus `usageMetadata`, `voiceActivity`): `setupComplete`, `serverContent{modelTurn{parts},
  turnComplete, interrupted, generationComplete, groundingMetadata, inputTranscription {text},
  outputTranscription{text}, interimInputTranscription, waitingForInput, interactionStatus, urlContextMetadata}`,
  `toolCall{functionCalls[{id, name, args}]}`, `toolCallCancellation{ids}`, `goAway{timeLeft}`,
  `sessionResumptionUpdate{newHandle, resumable}`. `enableAffectiveDialog` is 2.5-only; `activityHandling` values are
  *unverified*.
- Interruption: VAD-triggered; `serverContent.interrupted = true` means stop and clear queued playback; pending
  function calls are cancelled and their ids reported. Manual activity with `automaticActivityDetection.disabled` +
  `activityStart`/`activityEnd`; `audioStreamEnd` flushes after >1 s pause.
- Tools: function declarations in setup; the client must answer every `toolCall` (no automatic handling); `behavior:
  NON_BLOCKING` on a declaration makes it asynchronous, and the response's `scheduling` (`INTERRUPT | WHEN_IDLE |
  SILENT`) says when the model may speak the result (required on `gemini-3.8-live-extended-thinking`, unsupported on
  3.1 flash live). Google Search built-in on all; code execution / URL context listed as unsupported.
- Session: 15 min audio-only, 2 min audio+video without compression, "unlimited" with `contextWindowCompression`;
  connection lifetime about 10 min, `goAway.timeLeft` precedes termination, resumption handles valid 2 h; context 128k
  (native audio) / 32k.

### 2.4 Amazon Nova Sonic (v1) and Nova 2 Sonic

- Bedrock `InvokeModelWithBidirectionalStream` (HTTP/2, SigV4). Input events in strict order:
  `sessionStart{inferenceConfiguration{maxTokens, topP, temperature},
  turnDetectionConfiguration{endpointingSensitivity: HIGH| MEDIUM|LOW}}` (Nova 2), `promptStart{promptName,
  textOutputConfiguration, audioOutputConfiguration{mediaType: audio/lpcm, sampleRateHertz 8000|16000| 24000,
  sampleSizeBits 16, channelCount 1, voiceId, encoding: base64, audioType: SPEECH}, toolUseOutputConfiguration,
  toolConfiguration{tools [{toolSpec{name, description, inputSchema{json}}}]}}`, then per block
  `contentStart{promptName, contentName, type: TEXT|AUDIO|TOOL, role: SYSTEM|USER|ASSISTANT|TOOL|SYSTEM_SPEECH,
  interactive, audioInputConfiguration | textInputConfiguration | toolResultInputConfiguration{toolUseId}}`,
  `textInput{content}` / `audioInput{content}` (about 32 ms frames, one open audio container for the whole
  conversation) / `toolResult{content}`, `contentEnd`, and finally `promptEnd`, `sessionEnd`.
- Output events: `usageEvent{details{delta|total{input|output{speechTokens, textTokens}}}, totalInputTokens,
  totalOutputTokens, totalTokens}`, `completionStart{sessionId, promptName, completionId}`, text blocks
  `contentStart{type: TEXT, role: USER|ASSISTANT, additionalModelFields: generationStage SPECULATIVE|FINAL}` +
  `textOutput{content}` + `contentEnd {stopReason: PARTIAL_TURN|END_TURN|INTERRUPTED}`, tool blocks `toolUse{toolName,
  toolUseId, content}` + `contentEnd{stopReason: TOOL_USE}`, audio blocks `audioOutput{content}` + `contentEnd`,
  `completionEnd{stopReason}`. ASR of the user arrives as a USER text block (FINAL); the assistant's SPECULATIVE text
  precedes audio and a FINAL text block after audio is "what was actually spoken" (post-barge-in truth).
- Nova 2 Sonic adds automatic language switching, 16 voices, cross-modal text input mid-session, async tool handling,
  8-minute connection limit with a renewal pattern. Model id *unverified* on the read pages.

### 2.5 Deepgram Voice Agent

- `wss://agent.deepgram.com/v1/agent/converse` (`Authorization` header). First client message after
  `Welcome{request_id}` is `Settings{audio{input {encoding, sample_rate}, output{encoding, sample_rate, bitrate,
  container}}, agent{greeting, context.messages, listen.provider{type: deepgram, version: v1|v2, model, language,
  keyterms, smart_format | eot_threshold, eager_eot_threshold, eot_timeout_ms (Flux)}, think{provider{type: open_ai|
  anthropic|google|groq|aws_bedrock|deepgram, model, temperature}, prompt, endpoint{url, headers}, functions[{name,
  description, parameters, endpoint{url, method, headers}}], context_length}, speak{provider{type, model | model_id,
  voice}, endpoint}}, tags, experimental, flags.history}` -> `SettingsApplied`. Then binary audio in; `UpdateListen`,
  `UpdateThink`, `UpdateSpeak`, `UpdatePrompt`, `InjectUserMessage{content}`, `InjectAgentMessage{message, behavior:
  default|queue|interrupt}`, `FunctionCallResponse{id, name, content}`, `ForceEndTurn`, `KeepAlive`.
- Server: `ConversationText{role: user|assistant, content, conversational_behavior}`, `UserStartedSpeaking` (stop
  playback), `AgentThinking{content}`, `FunctionCallRequest{functions[{id, name, arguments, client_side}]}`,
  `FunctionCallCancelled{functions[{id, name}]}`, `AgentStartedSpeaking{total_latency, tts_latency, ttt_latency}`,
  `AgentAudioDone`, `PromptUpdated`, `SpeakUpdated`, `InjectionRefused`, `FrustrationDetected`, `LatencyReport`,
  `History`, `Error{description, code}`, `Warning`, binary audio. Pricing $0.075/min standard.

### 2.6 ElevenLabs Agents (Conversational AI)

- `wss://api.elevenlabs.io/v1/convai/conversation?agent_id=` (regional hosts; auth via signed URL / `xi-api-key`
  *unverified* on the reference page). Client: `conversation_initiation_client_data{conversation_config_override,
  custom_llm_extra_body, dynamic_variables, user_id}`, `user_audio_chunk` (base64), `user_message`,
  `multimodal_message`, `user_activity`, `contextual_update`, `pong{event_id}`, `client_tool_result{tool_call_id,
  result, is_error}`, `mcp_tool_approval_result`, `feedback`. Server:
  `conversation_initiation_metadata{conversation_id, agent_output_audio_format, user_input_audio_format}`,
  `user_transcript{user_transcription_event {user_transcript}}`,
  `agent_response{agent_response_event{agent_response}}`, `agent_response_correction`, `agent_response_complete`,
  `audio{audio_event {audio_base_64, event_id, alignment, is_final}}`, `interruption {interruption_event{event_id}}`,
  `ping{ping_event{event_id, ping_ms}}`, `client_tool_call{tool_name, tool_call_id, parameters, expects_response}`,
  `vad_score`, `agent_tool_request|response`, `mcp_tool_call`, `guardrail_triggered`, `context_usage`, `client_error`.
  Formats `pcm_8000..pcm_48000`, `ulaw_8000`. The agent (prompt, LLM, voice, tools) is server-side configuration, not
  session data. $0.08/min plus LLM.

### 2.7 Azure Voice Live

WebSocket API "designed for compatibility with the Azure OpenAI Realtime API" events, adding `azure_semantic_vad`,
noise suppression, echo cancellation, Azure TTS voices (standard/custom), avatars, and a model menu spanning
`gpt-realtime-2.1(-mini|-datazone|-regional)`, cascades over `gpt-5.x` / `gpt-4.1` / `phi4-mm-realtime`, and
`azure-realtime`. Sessions <= 60 min, 100 new connections/min. Pricing tiers Pro/Standard/Lite by model; audio about
10 input / 20 output tokens per second. Exact event deltas vs OpenAI are in a how-to page not read (*unverified*).
Relevant because it is a second host of the OpenAI event vocabulary (a `DialectTraits` case, not a new interface).

### 2.8 Hume EVI — status unverified

The EVI reference (`wss://api.hume.ai/v0/evi/chat`, `audio_input`, `session_settings`, `user_message{interim}`,
`assistant_message`, `audio_output`, `assistant_end`, `user_interruption`, `tool_call`) is known from search snippets
only; every `dev.hume.ai` URL fetched on 2026-11-10 served the new Audio Decisions product, and one snippet claimed
TTS/EVI access ends 2026-11-13. Not a candidate until confirmed.

### 2.9 Orchestration layer: LiveKit Agents, Pipecat, Daily

- LiveKit Agents: agents join rooms over WebRTC; `AgentSession` composes STT/LLM/TTS plugins or a realtime model;
  `turn_detection` modes (turn detector model, `"vad"`, `"stt"` for Flux/AssemblyAI endpointing, `"realtime_llm"`,
  `"manual"`); interruption options (`enabled`, `mode: adaptive|vad`, `min_duration`, `min_words`,
  `discard_audio_if_uninterruptible`, `resume_false_interruption`); on interruption the agent truncates its chat
  history to what the user heard; manual control via `session.interrupt()`, `commit_user_turn()`, `clear_user_turn()`;
  SIP telephony. Plugin interface shapes (`SpeechEvent` types) *unverified*.
- Pipecat (BSD-2): frame-processor pipelines ("data packages" carrying audio, transcripts, LLM text, synthesized
  audio), transports (Daily WebRTC, LiveKit, WebSocket, Twilio), service wrappers for STT/TTS/LLM and for OpenAI
  Realtime / Gemini Live as speech-to-speech services, Silero VAD and Smart Turn detection, interruption handling;
  exact frame class names *unverified* (reference pages exist but were not read).
- What the platform uses vs what the kernel models: the platform (an application built *on* ocai) owns rooms, media
  transport to end users, VAD/turn policy and telephony; the kernel models the provider session wire (one neutral
  event union, a frame log, a fold to transcript) so that a Pipecat/LiveKit adapter can swap OpenAI for Gemini behind
  one port.

## 3. Event vocabulary side by side

| Concept | OpenAI Realtime | Gemini Live | Nova Sonic | Deepgram Agent | ElevenLabs Agents |
|---|---|---|---|---|---|
| Configure | `session.update` | `BidiGenerateContentSetup` (first only) | `sessionStart` + `promptStart` | `Settings` (first after `Welcome`) | `conversation_initiation_client_data` |
| Config ack | `session.created` / `session.updated` | `setupComplete` | none | `SettingsApplied` | `conversation_initiation_metadata` |
| Audio in | `input_audio_buffer.append` | `realtimeInput.audio` | `audioInput` (in a `contentStart` AUDIO block) | binary frame | `user_audio_chunk` |
| Text in | `conversation.item.create` (message) | `clientContent.turns` / `realtimeInput.text` | `textInput` (USER, `interactive: true`) | `InjectUserMessage` | `user_message` |
| End of user turn | `input_audio_buffer.commit` / VAD `speech_stopped` | `activityEnd` / VAD; `audioStreamEnd` | model endpointing (`endpointingSensitivity`) | `ForceEndTurn` / model | VAD |
| User speech started | `input_audio_buffer.speech_started` | `voiceActivity` | implicit | `UserStartedSpeaking` | `vad_score` |
| User transcript | `conversation.item.input_audio_transcription.delta|completed` | `serverContent.inputTranscription` | `textOutput` role USER (FINAL) | `ConversationText` role user | `user_transcript` |
| Assistant audio | `response.output_audio.delta` | `serverContent.modelTurn.parts[inlineData]` | `audioOutput` | binary frame | `audio.audio_event` |
| Assistant transcript | `response.output_audio_transcript.delta` | `serverContent.outputTranscription` | `textOutput` role ASSISTANT (SPECULATIVE then FINAL) | `ConversationText` role assistant | `agent_response` (+ `agent_response_correction`) |
| Turn complete | `response.done` | `serverContent.turnComplete` (+ `generationComplete`) | `contentEnd` END_TURN, `completionEnd` | `AgentAudioDone` | `agent_response_complete` |
| Interrupted | `response.done` status `cancelled` + client `conversation.item.truncate` | `serverContent.interrupted` | `contentEnd` stopReason INTERRUPTED | `UserStartedSpeaking` | `interruption` |
| Tool call | `response.function_call_arguments.delta|done` + item | `toolCall.functionCalls` | `toolUse` block | `FunctionCallRequest` | `client_tool_call` |
| Tool result | `conversation.item.create` `function_call_output` + `response.create` | `toolResponse.functionResponses` (+ `scheduling`) | `toolResult` block | `FunctionCallResponse` | `client_tool_result` |
| Tool cancel | none explicit | `toolCallCancellation.ids` | none | `FunctionCallCancelled` | none |
| Usage | `response.done.usage`, `rate_limits.updated` | `usageMetadata` | `usageEvent` | `LatencyReport` (no tokens) | `context_usage` |
| Session end / resume | 60 min; none | `goAway`, `sessionResumptionUpdate` | `promptEnd`, `sessionEnd`; 8 min reconnect | `Close` | close code 4300 |
| Audio formats | pcm 24k, pcmu, pcma | pcm 16k in, 24k out | lpcm 8/16/24k | configurable | pcm 8k-48k, ulaw 8k |

## 4. Canonical IR proposal (`ocai.realtime`, revision `2026-11` draft)

One capability, `Capability("realtime")`, with a **duplex port shape**: shapes `("realtime","session.config")`,
`("realtime","frame.in")`, `("realtime","frame.out")`, `("realtime","transcript")`. There is no request/response pair;
the unit of conversion is a **frame**, and the unit of certification is a **frame log**.

```
SessionConfig(IRObject)            # bound at open; provider-specific knobs via provider_options
  instructions, tools (chat Tool), tool_choice
  audio_in:  AudioFormat; audio_out: AudioFormat; voice: ProviderRef(kind="voice")
  turn_detection: TurnDetection(mode: server_vad | semantic_vad | manual, silence_ms, prefix_ms, threshold, interrupt: bool, create_response: bool)
  transcribe_input / transcribe_output: bool
  resume: ProviderRef(kind="session") | None

Frame(IRObject)                     # one entry of the frame log
  seq: int; direction: in | out; t_ms: int | None; kind: FrameKind; payload; raw_event; anchor: ProviderRef | None

FrameKind (open codes; in = client -> provider, out = provider -> client):
  in:  audio (DeltaBlob) | text (PartText) | commit | clear | tool_result (PartToolResult) | truncate(item, audio_end_ms) | cancel | config (SessionConfig delta) | close
  out: session_ready | speech_started | speech_stopped | transcript_in (DeltaText | Segment, final: bool, item) |
       audio_out (DeltaBlob, item) | transcript_out (DeltaText, item) | text_out | tool_call (PartToolCall delta/done, item) |
       tool_cancel(ids) | turn_end (item, finish: FinishInfo) | interrupted (item, audio_end_ms | None) |
       usage (Usage) | resume_handle (ProviderRef) | go_away(time_left) | error (wire error shape) | end (StreamEnd)
```

Decisions:

- **Reuse the chat IR for everything that is content.** Tool calls are `PartToolCall` (string-fragment `args_json`,
  `call_id`), tool results are `PartToolResult`, text is `PartText`, audio is `PartAudio`/`DeltaBlob`. Turns fold into
  chat `Message`s (§5), so a realtime transcript is a valid `ChatRequest.messages` for replay through the chat port.
- **Items are provider refs.** OpenAI `item_id`, Nova `contentId`, Deepgram function `id`, ElevenLabs `event_id`
  anchor frames; Gemini has no item ids (turns are implicit), which the Gemini codec synthesizes per `turnComplete`
  and declares as a `SemanticShift("item.synthesized")`.
- **Transport is not IR.** WebSocket, WebRTC, HTTP/2 event stream and SIP are `DuplexTransport` implementations;
  `DialectTraits` carry framing (JSON text frames vs binary audio frames vs event-stream envelopes). Azure Voice Live
  is a host of the OpenAI interface, not an interface.
- **Composed agents are partially modelled.** Deepgram's `think`/`speak` providers and ElevenLabs' server-side agent
  config are destination passthrough (`provider_options`), reported UNSUPPORTED when a session is moved to a
  speech-to-speech provider. Their frames still map (table in §3), so the transcript fold is portable even where the
  config is not.

## 5. Frame log and fold law

The frame log is the ordered sequence of `Frame`s for one session (both directions, with `seq` assigned by the driver
and `t_ms` from the provider where given). Recorded frame logs are the fixture format (the archived plan's "captured
session transcript"); credentials are applied at the transport leaf and never appear in a log.

**Fold law (normative):** `fold(frame_log) -> SessionTranscript(messages: list[Message], usage: Usage, finish:
FinishInfo, report: FidelityReport)` is a pure function with these rules:

1. **User turns.** For each committed input item (`commit`, VAD `speech_stopped`, or provider turn boundary), one
   `Message(role="user")` whose text is the *final* `transcript_in` for that item (interim/delta frames are discarded,
   last-wins by item) and whose audio part references the concatenated `audio` frames between the previous commit and
   this one. Text-in frames become user messages verbatim.
2. **Assistant turns.** For each response item, one `Message(role="model")` whose text part is the concatenation of
   `transcript_out`/`text_out` deltas for that item and whose audio part is the concatenation of `audio_out` deltas;
   tool calls in the same response are `PartToolCall`s with `args_json` accumulated from fragments (PART_STOP rule:
   the done frame's arguments must equal the accumulation).
3. **Interruption truncates.** An `interrupted` frame (or a client `truncate`) with `audio_end_ms` cuts the assistant
   audio part at that offset and marks the message `finish.reason = "interrupted"`; the text part keeps the full
   transcript but records `truncated_at_ms` in a censused extension, because no provider except Nova (FINAL text block
   after barge-in) states what was actually heard. Without an offset the whole response is kept and flagged.
4. **Tool results** become `Message(role="tool")` with `PartToolResult` correlated by `call_id`; cancelled calls
   (`tool_cancel`) seal the call with `status = "output_error"` and no result message.
5. **Usage** is the last cumulative `usage` frame if the provider reports totals (Nova `total`, Gemini
   `usageMetadata.totalTokenCount`), else the sum of per-response `usage` frames (OpenAI `response.done.usage`);
   `finish` is `complete` on a clean `end`, `incomplete` on `go_away` / transport drop, `error` on a terminal `error`.
6. **Determinism.** Two folds of the same log are canonically equal (`canonjson.semantic_equal`); the fixture triple
   per edge is (frame log, folded transcript, provider's own history view where one exists: Deepgram `History`, OpenAI
   `conversation.item.retrieve`, Gemini none).

Streaming parity with chat holds per assistant turn: the assistant `Message` folded from a realtime response equals
what `StreamAccumulator` would fold from an equivalent `ChatChunk` sequence, which is how realtime reuses the chat
fold-triple harness instead of a new one.

## 6. UNSUPPORTED or report-only across providers

- Session resumption and context compression (Gemini `sessionResumption`, `contextWindowCompression`; Amazon
  `SessionResumeWindow` on Transcribe only): `ProviderRef(kind="session")`, UNSUPPORTED elsewhere.
- Out-of-band responses (`conversation: "none"`), `conversation.item.create` history injection with
  `previous_item_id`: OpenAI only.
- Async tool scheduling (`NON_BLOCKING`, `INTERRUPT|WHEN_IDLE|SILENT`): Gemini; Nova 2 async tools; others block.
  Reported as `SemanticShift`.
- Speculative vs final assistant text (Nova): extension; the fold uses FINAL.
- Video frames in (Gemini), images in (OpenAI 2.1): `PartImage` frames, UNSUPPORTED on audio-only providers.
- Affective dialog, proactive audio, thinking levels (Gemini), noise reduction / echo cancellation (OpenAI, Azure),
  avatar/viseme output (Azure), prosody scores (Hume), frustration detection (Deepgram): censused extensions.
- Composed-agent configuration (Deepgram `think`/`speak`, ElevenLabs agent overrides, Azure voice menus):
  `provider_options`.
- Full-duplex listening-while-speaking (GPT-Live) has no turn boundary semantics shared with half-duplex providers;
  its frames fold, but `turn_detection` is UNSUPPORTED in both directions.
- Transport-level features (WebRTC media tracks, SIP call control, telephony codecs): never in the IR.

## 7. Priority and effort

**Priority P3 for the capability, P2 for its transport primitive.** The argument for P3: the surface is unstable (GA
renames at OpenAI within a year, a parallel GPT-Live product with a different session API, Gemini still preview with
model churn, Hume possibly gone, Azure re-hosting OpenAI's vocabulary), the enterprise demand ocai targets is served
first by batch STT/TTS and streaming STT, and every realtime event maps onto chat parts that already exist, so nothing
in the kernel blocks on it. The argument against P2: a P2 commitment would freeze a `FrameKind` vocabulary before two
providers have been exercised through it, which the stability rules forbid. What *is* P2 is `DuplexTransport` (sans-io
frame log, recorded sessions, credentials at the leaf), because streaming STT needs it now and realtime inherits it
unchanged; that matches the archived plan's "9.1 gates everything".

**Effort:** 6 WUs once STT streaming has landed the transport. (1) `SessionConfig` + `Frame` IR, schemas, frame-log
fixture format. (2) Fold law implementation + determinism tests on synthetic logs. (3) OpenAI Realtime codec over
WebSocket with recorded session fixtures (VAD, tool call, interruption, out-of-order transcripts). (4) Gemini Live
codec with the synthesized-item shift and tool cancellation. (5) Cross-provider conformance: the same application log
replayed through both codecs, loss certified against each `EdgeContract`. (6) Middleware over sessions (cost accrual
from usage frames, tracing spans, reconnect policy).

**First provider when started: OpenAI Realtime over WebSocket** — the most completely documented event protocol, item
ids that make the fold exact, and a transcription-only session mode that is literally the STT streaming edge (so the
codec is shared). **Second: Gemini Live** as the cross-provider proof (no item ids, different interruption and tool
semantics). Nova Sonic third (event-stream transport, FINAL-after-barge-in truth that validates rule 3). Composed
agents (Deepgram, ElevenLabs) only after the speech-to-speech pair, since their value is in config portability that
ocai cannot offer.

## 8. Open questions and unverified items

- OpenAI SIP endpoints, `output_audio_buffer.started|stopped`, MCP call event names, `truncation.retention_ratio`;
  GPT-Live event vocabulary and delegation events.
- Gemini `activityHandling` values; Nova 2 Sonic model id and async tool event shapes; Hume EVI availability;
  ElevenLabs Agents auth flow; Azure Voice Live event deltas vs OpenAI; LiveKit/Pipecat type names.

## Sources

Read 2026-11-10.

- https://developers.openai.com/api/docs/guides/realtime
- https://developers.openai.com/api/docs/guides/realtime-conversations
- https://developers.openai.com/api/docs/guides/realtime-vad
- https://developers.openai.com/api/docs/guides/realtime-transcription
- https://developers.openai.com/api/docs/guides/voice-webrtc.md
- https://developers.openai.com/api/docs/guides/live
- https://developers.openai.com/api/docs/guides/custom-voices
- https://developers.openai.com/api/docs/api-reference/realtime-client-events
- https://developers.openai.com/api/docs/api-reference/realtime-server-events
- https://developers.openai.com/api/docs/models/gpt-realtime-2.1
- https://developers.openai.com/api/docs/models/gpt-live-1
- https://developers.openai.com/api/docs/pricing
- https://aistudio.google.com/docs/live-api
- https://aistudio.google.com/docs/live-api/capabilities
- https://aistudio.google.com/docs/live-api/tools
- https://aistudio.google.com/docs/live-api/session-management
- https://aistudio.google.com/api-reference/live
- https://docs.aws.amazon.com/nova/latest/userguide/speech.html
- https://docs.aws.amazon.com/nova/latest/userguide/input-events.html
- https://docs.aws.amazon.com/nova/latest/userguide/output-events.html
- https://docs.aws.amazon.com/nova/latest/nova2-userguide/using-conversational-speech.html
- https://docs.aws.amazon.com/nova/latest/nova2-userguide/sonic-input-events.html
- https://docs.aws.amazon.com/nova/latest/nova2-userguide/sonic-output-events.html
- https://developers.deepgram.com/reference/voice-agent/voice-agent
- https://developers.deepgram.com/docs/voice-agent-message-flow
- https://developers.deepgram.com/docs/voice-agent
- https://deepgram.com/pricing
- https://elevenlabs.io/docs/agents-platform/api-reference/agents-platform/websocket
- https://elevenlabs.io/pricing/api
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits
- https://dev.hume.ai/changelog and https://dev.hume.ai/reference/speech-to-speech-evi/chat (served Audio Decisions
  content only)
- https://docs.livekit.io/agents/
- https://docs.livekit.io/agents/build/turns/
- https://docs.pipecat.ai/ and https://docs.pipecat.ai/pipecat/learn/overview
- https://docs.pipecat.ai/llms.txt (index of frame and service reference pages, not read)
