import assert from "node:assert/strict";
import { after, before, describe, it } from "node:test";
import { createServer, type Server } from "node:http";
import { createApp } from "./app.js";

describe("Phase API smoke checks", () => {
  let server: Server;
  let baseUrl: string;

  before(async () => {
    server = createServer(createApp());
    await new Promise<void>((resolve) => {
      server.listen(0, "127.0.0.1", resolve);
    });
    const address = server.address();
    assert.ok(address && typeof address !== "string");
    baseUrl = `http://127.0.0.1:${address.port}`;
  });

  after(async () => {
    await new Promise<void>((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
  });

  it("reports health without requiring provider credentials", async () => {
    const response = await fetch(`${baseUrl}/health`);
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { status: "ok" });
  });

  it("surfaces missing Gemini credentials instead of returning sample success", async () => {
    const response = await fetch(`${baseUrl}/api/gemini/hello`, {
      method: "POST",
    });
    assert.equal(response.status, 503);
    assert.deepEqual(await response.json(), {
      error: "GEMINI_API_KEY is not configured",
    });
  });

  it("surfaces missing Cartesia credentials instead of returning sample success", async () => {
    const response = await fetch(`${baseUrl}/api/cartesia/readback`, {
      method: "POST",
    });
    assert.equal(response.status, 503);
    assert.deepEqual(await response.json(), {
      error: "CARTESIA_API_KEY is not configured",
    });
  });

  it("surfaces missing Cartesia credentials on transcription", async () => {
    const response = await fetch(`${baseUrl}/api/cartesia/transcribe`, {
      method: "POST",
      headers: { "Content-Type": "audio/mp4" },
      body: new Uint8Array([1, 2, 3]),
    });
    assert.equal(response.status, 503);
    assert.deepEqual(await response.json(), {
      error: "CARTESIA_API_KEY is not configured",
    });
  });
});
