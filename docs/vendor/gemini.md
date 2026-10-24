# Gemini API notes for Phase

Official documentation consulted:

- [Getting started](https://ai.google.dev/gemini-api/docs/get-started?lang=node)
- [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output?lang=node)

The current JavaScript SDK package is `@google/genai`; the current documentation
demonstrates `GoogleGenAI` and the Interactions API. Its structured-output
example creates JSON output using a schema:

```ts
const interaction = await client.interactions.create({
  model: "gemini-3.8-flash",
  input: prompt,
  response_format: {
    type: "text",
    mime_type: "application/json",
    schema: responseJsonSchema
  }
});
```

The response text still must be parsed and validated by the application before
use. API keys stay on the server. Never pass a login code, account identifier,
or raw audio/transcript to Gemini. Requests should contain only the minimum
fields needed for the feature. Every system prompt must prohibit emojis.

The Stage 2 hello-world is an opt-in server endpoint requiring
`GEMINI_API_KEY`; it is not a verified product feature.

## Audio understanding (G1)

Official audio docs show inline audio on Interactions:

```ts
await client.interactions.create({
  model: "gemini-3.8-flash",
  input: [
    { type: "text", text: "..." },
    { type: "audio", data: base64Audio, mime_type: "audio/wav" },
  ],
});
```

Phase uses this for `/api/gemini/checkin-audio` with a JSON schema for
check-in fields. Do not send login codes or account IDs. Audio is held only
in memory until the user confirms or clears the check-in.
