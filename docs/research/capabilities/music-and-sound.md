# Music and sound-effect generation — status summary (deferred)

> **Research snapshot, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

**Currency.** Researched 2026-11-10 against the official documentation
linked in Sources; third-party reporting is marked as such. Two of the five
named vendors have no public API at all, so this page records status and a
recommendation rather than a provider survey.

## 1. Status table

| Vendor | Product | Public API | Transport | Key request fields (as documented) | Output | Price signal |
|---|---|---|---|---|---|---|
| Suno | Suno v5 music | **No.** Invite-only partner program announced 2026-07-01 (intake form); as of 2026-10 no self-serve console, docs, or pricing (third-party reporting) | — | — | — | — |
| Udio | Udio music | **No.** Help center states no public API; 2026-07 reporting describes a "walled garden" strategy; some limited partner access reported (third-party) | — | — | — | — |
| ElevenLabs | Music | Yes | `POST https://api.elevenlabs.io/v1/music`, `xi-api-key`, JSON; regional hosts | `prompt` xor `composition_plan` (`MusicPrompt` for `music_v1`, `CompositionPlan` for `music_v2`/`music_v2_5`), `music_length_ms` 3000–600000, `model_id` `music_v1|music_v2|music_v2_5`, `force_instrumental`, `seed`, `finetune_id`, `store_for_inpainting`, `sign_with_c2pa`; query `output_format` (`mp3_44100_128` default for v1, `mp3_48000_192` for v2) | audio file body (sync) | not on the reference page |
| ElevenLabs | Sound effects | Yes | `POST /v1/sound-generation`, `xi-api-key` | `text`, `duration_seconds` 0.5–30 (guessed if omitted), `prompt_influence` 0–1 (default 0.3), `loop`, `model_id` `eleven_text_to_sound_v2|v3`; query `output_format` | audio file body (sync) | not on the reference page |
| Stability AI | Stable Audio 2 / 2.5 | Yes | `POST https://api.stability.ai/v2beta/audio/stable-audio-2/text-to-audio`, Bearer, multipart; `accept: audio/*` or `application/json` | `prompt` ≤10000, `duration` 1–190 s, `seed`, `steps` (2: 30–100; 2.5: 4–8), `cfg_scale` 1–25, `model` `stable-audio-2|stable-audio-2.5`, `output_format` `mp3|wav` | bytes or `{audio (base64), seed, finish_reason}` | 2.5: 8 credits ($0.08); 2.0: `17 + 0.06*steps` credits |
| Stability AI | Stable Audio 3.0 | Yes | async (returns `id`, poll `/v2beta/results/{id}`, 24 h retention) — endpoint path not reachable (`unverified`) | text-to-audio, audio-to-audio, inpaint; up to 6 minutes | — | 8 credits ($0.08) |
| Google | Lyria 3.5 / Lyria 3 Clip Preview | Yes | `POST https://generativelanguage.googleapis.com/v1beta/interactions`, `x-goog-api-key`, `Api-Revision: 2026-05-20` | `model` `lyria-3.5|lyria-3-clip-preview`, `input` (text, up to 10 images), `response_format{type:"audio"}` (WAV option for 3.5 mentioned, field `unverified`) | `output_audio` base64 (or `steps[]` with `audio` and `text` blocks); MP3 44.1 kHz stereo; SynthID | $0.08 per song, $0.04 per 30 s clip |
| Google | Lyria RealTime | Yes (experimental) | WebSocket `BidiGenerateMusic` session, model `models/lyria-realtime-exp` | `weighted_prompts[]{text, weight}` (normalized, not all zero), `music_generation_config{bpm 60–200, density 0–1, brightness 0–1, scale, temperature 0–3, top_k, seed, mute controls}`, control `play|pause|stop|reset_context` | streamed PCM audio chunks | not located |
| Runway | sound effects / music | Yes (listed) | tasks API endpoints under the same `X-Runway-Version` grammar | not surveyed | URL via task | credits |

## 2. What the survey shows

- **Reachable APIs are three** (ElevenLabs, Stability, Google) plus
  Runway's side endpoints; the two consumer leaders (Suno, Udio) are
  closed. A capability that cannot express the models most users ask
  for would misrepresent coverage.
- **Paradigms do not align.** ElevenLabs and Stability are one-shot
  prompt→file; Lyria 3.5 is one-shot through the Interactions API; Lyria
  RealTime is a duplex session with live steering (bpm, density,
  `reset_context`) — closer to the realtime/duplex family in §11 step 8
  ("duplex sessions fold a frame log") than to generation. Stable Audio
  3.0 is a job. Three execution styles for three providers.
- **Knob congruence is thin.** Duration (ElevenLabs ms, Stability seconds,
  Lyria prompt-controlled), instrumental flag (ElevenLabs only),
  structure plan (ElevenLabs `composition_plan` vs Lyria lyrics-in-prompt),
  and sampler knobs (Stability `steps`/`cfg_scale`) do not clear the
  three-lane law's ≥2–3-congruent-interfaces bar for any first-class field
  except `prompt`, `duration`, `seed` and `output format`.
- **Sound effects** are the simplest and most congruent slice
  (ElevenLabs `/v1/sound-generation`, Stable Audio short durations, Runway
  sound effects): text + duration + loop → short audio file.

## 3. Recommendation: defer

Defer `ocai.music`/`ocai.sound` entirely until (a) Suno or Udio ships a
documented public API, or (b) a second provider matches Lyria RealTime's
duplex steering, whichever comes first. Preconditions inside ocai: the
`Source` union already covers audio outputs; `ocai.jobs` (H6) covers Stable
Audio 3.0; the duplex session law (fold a frame log into a transcript)
should be settled by the realtime chat work before Lyria RealTime is
modeled. If pressure arrives earlier, the smallest honest slice is a
single-shape `("sound","generate.request")` for sound effects with
`prompt`, `duration_seconds`, `loop`, `seed`, `output: AudioOutputSpec`,
reusing core `Consumption` with unit `seconds` or `credits` — two to three
interfaces (ElevenLabs, Stability, Runway) and no job or duplex machinery.
Revisit at the H6 checkpoint.

## 4. Unverified items

- Suno/Udio status rests on third-party reporting; neither vendor
  publishes developer docs.
- Stable Audio 3.0 endpoint path and async fields.
- Lyria RealTime raw wire field names (`weightedPrompts`,
  `musicGenerationConfig`) — seen only through SDK method names and
  partial reference excerpts.
- Lyria 3.5 WAV `response_format` field; ElevenLabs music streaming and
  "detailed" variants; Runway sound/music request fields.

## Sources (read 2026-11-10)

- https://www.digitalmusicnews.com/2026/07/03/suno-is-opening-an-api-partner-program/ (third-party)
- https://musicbusinessworldwide.com/suno-explores-developer-api-seeking-apps-that-unlock-experiences-generative-music-makes-possible-for-the-first-time (third-party)
- https://www.digitalmusicnews.com/2026/07/17/udio-buydrm-deal-walled-garden/ (third-party)
- https://apiframe.ai/guides/udio-api-guide (third-party; quotes the Udio help center)
- https://elevenlabs.io/docs/api-reference/music/compose
- https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert
- https://docs.stability.ai/api-reference/stable-audio-2/text-to-audio.md
- https://docs.stability.ai/api-reference
- https://docs.stability.ai/pricing.md
- https://aistudio.google.com/docs/music-generation
- https://aistudio.google.com/docs/pricing
- https://ai.google.dev/gemini-api/docs/realtime-music-generation
- https://ai.google.dev/api/live_music
- https://docs.dev.runwayml.com/_llms-txt/core-api.txt
