import "dotenv/config";
import { createApp } from "./app.js";

const port = Number(process.env.PORT ?? 4000);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error("PORT must be an integer between 1 and 65535");
}

createApp({
  geminiApiKey: process.env.GEMINI_API_KEY,
  cartesiaApiKey: process.env.CARTESIA_API_KEY,
}).listen(port, "127.0.0.1", () => {
  process.stdout.write(`Phase API listening on port ${port}\n`);
});
