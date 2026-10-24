# Sponsor documentation

Before using a sponsor SDK, paste the official documentation relied on into
this directory and read it. Do not infer or guess API signatures. In any code
that uses an SDK, quote the exact relied-on signature in a code comment.

Please provide documentation for:

- **Cartesia:** streaming speech-to-text in the chosen client/runtime, live
  transcript events, and Sonic text-to-speech playback.
- **Gemini:** server-side text generation, structured JSON/schema-constrained
  output, and the current TypeScript/JavaScript SDK signatures.
- **Moss:** retrieval/search setup and query APIs for the proposed knowledge
  base.

If a feature or runtime is not covered by the supplied documentation, pause
before integrating it and use the documented fallback instead.
