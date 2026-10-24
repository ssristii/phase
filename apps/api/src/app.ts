import { GoogleGenAI } from "@google/genai";
import cors from "cors";
import express, { type ErrorRequestHandler } from "express";
import { z } from "zod";

const cartesiaVersion = "2026-08-14";
const transcriptResponseSchema = z.object({ text: z.string() });
const geminiResponseSchema = z.object({ message: z.string().min(1) });
const geminiJsonSchema = {
  type: "object",
  properties: {
    message: { type: "string" },
  },
  required: ["message"],
  additionalProperties: false,
};

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
      const parsed = geminiResponseSchema.parse(
        JSON.parse(interaction.output_text),
      );
      response.json(parsed);
    } catch (error) {
      next(error);
    }
  });

  app.post(
    "/api/cartesia/transcribe",
    express.raw({
      type: ["audio/mp4", "audio/wav", "audio/x-wav"],
      limit: "10mb",
    }),
    async (request, response, next) => {
      const audioContentType = request.headers["content-type"]
        ?.split(";")[0]
        .toLowerCase();
      const audioFile = {
        "audio/mp4": { extension: "m4a", mimeType: "audio/mp4" },
        "audio/wav": { extension: "wav", mimeType: "audio/wav" },
        "audio/x-wav": { extension: "wav", mimeType: "audio/x-wav" },
      }[audioContentType ?? ""];
      if (!audioFile) {
        response.status(415).json({
          error: "Audio must be an MP4 or WAV recording",
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
