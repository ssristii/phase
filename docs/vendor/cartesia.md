# Cartesia API notes for Phase

Official documentation consulted:

- [Realtime STT quickstart](https://docs.cartesia.ai/get-started/realtime-speech-to-text-quickstart.md)
- [Realtime TTS quickstart](https://docs.cartesia.ai/get-started/realtime-text-to-speech-quickstart.md)
- [Client application authentication](https://docs.cartesia.ai/get-started/authenticate-your-client-applications.md)
- [Batch STT endpoint](https://docs.cartesia.ai/api-reference/stt/transcribe.md)
- [Access token endpoint](https://docs.cartesia.ai/api-reference/auth/access-token.md)
- [TTS bytes endpoint](https://docs.cartesia.ai/api-reference/tts/bytes.md)

The realtime Ink 2 quickstart sends raw PCM (`pcm_s16le`, 16 kHz) in chunks to
`client.stt.autoFinalize.websocket({ model: "ink-2", encoding: "pcm_s16le",
sample_rate: 16000 })`, then consumes `turn.update` and `turn.end` events.
That is the provider's streaming path.

Expo Go's documented `expo-audio` recording API records audio files. It does
not document a raw PCM frame callback for microphone streaming. Therefore the
Stage 2 phone probe must not label record-then-upload as live transcription.
The default fallback is to record a temporary file, upload the completed file
to Batch STT, show the full editable transcript, and delete the local file after
the request finishes. The Batch STT API accepts containerized `m4a`, `mp3`,
`wav`, `webm`, and other listed formats with `model: "ink-whisper"`.

For native clients, Cartesia says to mint short-lived access tokens on the
server rather than expose the API key. The official JavaScript example is:

```ts
await client.accessToken.create({
  grants: { tts: true, stt: true },
  expires_in: 60
});
```

Use only the grants needed and keep tokens short-lived. Do not persist or log
tokens, recordings, or transcripts.

Sonic realtime TTS uses `client.tts.websocket()`, then `ws.context({...})`,
`ctx.push({ transcript })`, `ctx.no_more_inputs()`, and `ctx.receive()` for
audio chunks. The SDK quickstart's sample output is raw PCM, which requires a
compatible native playback path. The Stage 2 playback smoke check instead
requests an MP3 from `POST /tts/bytes` and plays that file in Expo Audio. Verify
actual playback on the phone before claiming Cartesia readback works.

## Stage 2 findings

- Streaming mic audio is unverified and is not supported by the documented
  `expo-audio` recording interface. Use record-then-upload unless a phone test
  demonstrates a supported PCM capture path.
- Do not claim Cartesia integration until a real-device test succeeds.
