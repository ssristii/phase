# Sponsor documentation

Before using a sponsor SDK, paste the official documentation relied on into
this directory and read it. Do not infer or guess API signatures. In any code
that uses an SDK, quote the exact relied-on signature in a code comment.

Official starting references provided:

- **Cartesia:** [Documentation overview](https://docs.cartesia.ai/get-started/overview)
- **Gemini:** [Gemini API documentation](https://ai.google.dev/gemini-api/docs)

The relevant API notes, signatures, and official page references are recorded
in [cartesia.md](./cartesia.md) and [gemini.md](./gemini.md). Read the original
pages again if implementation reaches beyond those documented API surfaces.
In particular, verify the runtime-specific requirements for:

- **Cartesia:** streaming speech-to-text in the chosen client/runtime, live
  transcript events, and Sonic text-to-speech playback.
- **Gemini:** server-side text generation, structured JSON/schema-constrained
  output, and the current TypeScript/JavaScript SDK signatures.
- **Moss:** retrieval/search setup and query APIs for the proposed knowledge
  base, only if the cut-ladder timebox permits using it.

If a feature or runtime is not covered by the supplied documentation, pause
before integrating it and use the documented fallback instead.
