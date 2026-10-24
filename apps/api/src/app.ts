import { GoogleGenAI } from "@google/genai";
import cors from "cors";
import express, { type ErrorRequestHandler } from "express";
import { z } from "zod";

const cartesiaVersion = "2026-08-14";
const transcriptResponseSchema = z.object({ text: z.string() });
const geminiResponseSchema = z.object({ message: z.string().min(1) });
const checkinRequestSchema = z.object({
  transcript: z.string().trim().min(1).max(4000),
});
const extractedCheckinSchema = z
  .object({
    flow: z.enum([
      "None",
      "Spotting",
      "Light",
      "Moderate",
      "Heavy",
      "Very heavy",
      "Not stated",
    ]),
    mood: z.enum([
      "Low",
      "Okay",
      "Good",
      "Anxious",
      "Irritable",
      "Not stated",
    ]),
    energy: z.number().int().min(0).max(5),
    sleep_hours: z.number().min(-1).max(12),
    pain: z.number().int().min(-1).max(10),
    workout_done: z.enum(["yes", "no", "not stated"]),
    severe_pain: z.enum(["yes", "no", "not stated"]),
    persistently_irregular_cycles: z.enum(["yes", "no", "not stated"]),
    positive_pregnancy_test: z.enum(["yes", "no", "not stated"]),
  })
  .strict();
const geminiJsonSchema = {
  type: "object",
  properties: {
    message: { type: "string" },
  },
  required: ["message"],
  additionalProperties: false,
};
const checkinJsonSchema = {
  type: "object",
  properties: {
    flow: {
      type: "string",
      enum: [
        "None",
        "Spotting",
        "Light",
        "Moderate",
        "Heavy",
        "Very heavy",
        "Not stated",
      ],
    },
    mood: {
      type: "string",
      enum: ["Low", "Okay", "Good", "Anxious", "Irritable", "Not stated"],
    },
    energy: { type: "integer", minimum: 0, maximum: 5 },
    sleep_hours: { type: "number", minimum: -1, maximum: 12 },
    pain: { type: "integer", minimum: -1, maximum: 10 },
    workout_done: { type: "string", enum: ["yes", "no", "not stated"] },
    severe_pain: { type: "string", enum: ["yes", "no", "not stated"] },
    persistently_irregular_cycles: {
      type: "string",
      enum: ["yes", "no", "not stated"],
    },
    positive_pregnancy_test: {
      type: "string",
      enum: ["yes", "no", "not stated"],
    },
  },
  required: [
    "flow",
    "mood",
    "energy",
    "sleep_hours",
    "pain",
    "workout_done",
    "severe_pain",
    "persistently_irregular_cycles",
    "positive_pregnancy_test",
  ],
  additionalProperties: false,
};

function normalizeCheckinFields(
  extracted: z.infer<typeof extractedCheckinSchema>,
) {
  return {
    flow: extracted.flow === "Not stated" ? null : extracted.flow,
    mood: extracted.mood === "Not stated" ? null : extracted.mood,
    energy: extracted.energy === 0 ? null : extracted.energy,
    sleep_hours: extracted.sleep_hours < 0 ? null : extracted.sleep_hours,
    pain: extracted.pain < 0 ? null : extracted.pain,
    workout_done:
      extracted.workout_done === "not stated"
        ? null
        : extracted.workout_done === "yes",
    severe_pain:
      extracted.severe_pain === "not stated"
        ? null
        : extracted.severe_pain === "yes",
    persistently_irregular_cycles:
      extracted.persistently_irregular_cycles === "not stated"
        ? null
        : extracted.persistently_irregular_cycles === "yes",
    positive_pregnancy_test:
      extracted.positive_pregnancy_test === "not stated"
        ? null
        : extracted.positive_pregnancy_test === "yes",
  };
}

export interface AppConfig {
  geminiApiKey?: string;
  cartesiaApiKey?: string;
}

export function createApp(config: AppConfig = {}): express.Express {
  const app = express();

  app.disable("x-powered-by");
  app.use(cors());
  app.use(express.json({ limit: "10kb" }));

  app.get("/health", (_request, response) => {
    response.json({ status: "ok" });
  });

  app.post("/api/gemini/hello", async (_request, response, next) => {
    if (!config.geminiApiKey) {
      response.status(503).json({ error: "GEMINI_API_KEY is not configured" });
      return;
    }

    try {
      const client = new GoogleGenAI({ apiKey: config.geminiApiKey });
      const prompt =
        "Do not use emojis. Return a short hello for the Phase integration check.";
      // Gemini docs: const interaction = await client.interactions.create({ model: "gemini-3.8-flash", input: prompt, response_format: { type: "text", mime_type: "application/json", schema: geminiJsonSchema } });
      const interaction = await client.interactions.create({
        model: "gemini-3.8-flash",
        input: prompt,
        response_format: {
          type: "text",
          mime_type: "application/json",
          schema: geminiJsonSchema,
        },
      });
      const output = interaction.output_text;
      if (!output) {
        throw new Error("Gemini returned no text output");
      }
      const parsed = geminiResponseSchema.parse(JSON.parse(output));
      response.json(parsed);
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/gemini/checkin", async (request, response, next) => {
    if (!config.geminiApiKey) {
      response.status(503).json({ error: "GEMINI_API_KEY is not configured" });
      return;
    }

    const requestResult = checkinRequestSchema.safeParse(request.body);
    if (!requestResult.success) {
      response.status(400).json({
        error: "Provide a transcript between 1 and 4000 characters",
      });
      return;
    }

    try {
      const client = new GoogleGenAI({ apiKey: config.geminiApiKey });
      const prompt = [
        "Extract only health check-in details explicitly stated in the transcript.",
        "Do not infer missing values. Use Not stated, 0, -1, or not stated as defined by the schema.",
        "Map sleep to hours, energy to 1 through 5, and pain to 0 through 10 only when the user states a value.",
        "Mark a yes/no item only when the transcript clearly states it; otherwise use not stated.",
        "Do not use emojis. Return JSON matching the schema exactly.",
        "",
        "Transcript to extract:",
        requestResult.data.transcript,
      ].join("\n");
      let extracted: z.infer<typeof extractedCheckinSchema> | undefined;
      let lastValidationError: Error | undefined;

      for (let attempt = 0; attempt < 2 && !extracted; attempt += 1) {
        // Gemini docs signature: client.interactions.create({ model, input, response_format: { type: "text", mime_type: "application/json", schema } }).
        const interaction = await client.interactions.create({
          model: "gemini-3.8-flash",
          input: prompt,
          store: false,
          response_format: {
            type: "text",
            mime_type: "application/json",
            schema: checkinJsonSchema,
          },
        });
        const output = interaction.output_text;
        if (!output) {
          lastValidationError = new Error("Gemini returned no text output");
          continue;
        }
        try {
          extracted = extractedCheckinSchema.parse(JSON.parse(output));
        } catch (error) {
          lastValidationError =
            error instanceof Error
              ? error
              : new Error("Gemini returned invalid check-in fields");
        }
      }

      if (!extracted) {
        throw lastValidationError ?? new Error("Gemini returned invalid fields");
      }
      response.json({ fields: normalizeCheckinFields(extracted) });
    } catch (error) {
      next(error);
    }
  });

  app.post(
    "/api/cartesia/transcribe",
    express.raw({
      type: [
        "audio/mp4",
        "audio/wav",
        "audio/x-wav",
        "audio/x-m4a",
        "audio/mpeg",
        "audio/mp3",
        "audio/webm",
        "audio/ogg",
        "video/mp4",
      ],
      limit: "10mb",
    }),
    async (request, response, next) => {
      const audioContentType = request.headers["content-type"]
        ?.split(";")[0]
        .toLowerCase();
      const audioFile = {
        "audio/mp4": { extension: "m4a", mimeType: "audio/mp4" },
        "audio/x-m4a": { extension: "m4a", mimeType: "audio/mp4" },
        "video/mp4": { extension: "mp4", mimeType: "video/mp4" },
        "audio/wav": { extension: "wav", mimeType: "audio/wav" },
        "audio/x-wav": { extension: "wav", mimeType: "audio/x-wav" },
        "audio/mpeg": { extension: "mp3", mimeType: "audio/mpeg" },
        "audio/mp3": { extension: "mp3", mimeType: "audio/mpeg" },
        "audio/webm": { extension: "webm", mimeType: "audio/webm" },
        "audio/ogg": { extension: "ogg", mimeType: "audio/ogg" },
      }[audioContentType ?? ""];
      if (!audioFile) {
        response.status(415).json({
          error: "Upload a WAV, MP3, M4A, MP4, WebM, or Ogg recording",
        });
        return;
      }
      if (!Buffer.isBuffer(request.body) || request.body.length === 0) {
        response.status(400).json({ error: "A recorded audio file is required" });
        return;
      }
      if (!config.cartesiaApiKey) {
        response
          .status(503)
          .json({ error: "CARTESIA_API_KEY is not configured" });
        return;
      }

      try {
        const form = new FormData();
        // Cartesia API: POST /stt multipart fields file, model, and language; send Cartesia-Version.
        form.append(
          "file",
          new Blob([new Uint8Array(request.body)], {
            type: audioFile.mimeType,
          }),
          `phase-check-in.${audioFile.extension}`,
        );
        form.append("model", "ink-whisper");
        form.append("language", "en");

        const providerResponse = await fetch("https://api.cartesia.ai/stt", {
          method: "POST",
          headers: {
            Authorization: "Bearer " + config.cartesiaApiKey,
            "Cartesia-Version": cartesiaVersion,
          },
          body: form,
          signal: AbortSignal.timeout(30000),
        });
        if (!providerResponse.ok) {
          response.status(502).json({
            error: `Cartesia transcription failed (${providerResponse.status})`,
          });
          return;
        }
        response.json(
          transcriptResponseSchema.parse(await providerResponse.json()),
        );
      } catch (error) {
        next(error);
      }
    },
  );

  app.post("/api/cartesia/readback", async (_request, response, next) => {
    if (!config.cartesiaApiKey) {
      response.status(503).json({ error: "CARTESIA_API_KEY is not configured" });
      return;
    }

    try {
      // Cartesia API signature: POST /tts/bytes with { model_id, transcript, voice, output_format }.
      const providerResponse = await fetch("https://api.cartesia.ai/tts/bytes", {
        method: "POST",
        headers: {
          Authorization: "Bearer " + config.cartesiaApiKey,
          "Cartesia-Version": cartesiaVersion,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model_id: "sonic-3.6",
          transcript: "Hello. This is the Phase voice playback check.",
          voice: "694f9389-aac1-45b6-b726-9d9369183238",
          output_format: {
            container: "mp3",
            sample_rate: 44100,
            bit_rate: 128000,
          },
        }),
        signal: AbortSignal.timeout(30000),
      });
      if (!providerResponse.ok) {
        response.status(502).json({
          error: `Cartesia readback failed (${providerResponse.status})`,
        });
        return;
      }

      response
        .type("audio/mpeg")
        .send(Buffer.from(await providerResponse.arrayBuffer()));
    } catch (error) {
      next(error);
    }
  });

  const errorHandler: ErrorRequestHandler = (
    error,
    _request,
    response,
    _next,
  ) => {
    if (
      error instanceof Error &&
      "type" in error &&
      error.type === "entity.too.large"
    ) {
      response.status(413).json({ error: "Audio file exceeds the 10 MB limit" });
      return;
    }
    response.status(502).json({ error: "The requested provider operation failed" });
  };
  app.use(errorHandler);

  return app;
}
