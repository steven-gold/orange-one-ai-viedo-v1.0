import { createHash } from "node:crypto";
import { resolveProviderConfigs, type ProviderConfig } from "./llmClient";

export interface SpeechTakeResult {
  takeId: string;
  bytes: number;
  sha256: string;
  provider: string;
  model: string;
}

const TTS_VOICE = "alloy";
const TTS_FORMAT = "mp3";

// Synthesize a voice take through the configured text-to-speech profile.
// The take lands as an exact VTK reference anchored by the audio checksum;
// no binding fields are touched here, so a failed generation can never
// block the render gate.
export async function generateSpeechTake(
  input: string,
  signal?: AbortSignal,
): Promise<SpeechTakeResult> {
  const configs = await resolveProviderConfigs("text-to-speech");
  const config: ProviderConfig | undefined = configs[0];
  if (!config) {
    throw new (class TtsUnavailable extends Error {
      readonly code = "TTS_PROVIDER_NOT_CONFIGURED";
    })("No enabled text-to-speech provider with a stored credential");
  }
  const text = input.trim();
  if (!text) {
    throw new (class TtsEmpty extends Error {
      readonly code = "TTS_SCRIPT_EMPTY";
    })("No script text available for synthesis");
  }
  let response: Response;
  try {
    response = await fetch(config.url, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${config.credential}`,
      },
      body: JSON.stringify({
        model: config.model,
        input: text,
        voice: TTS_VOICE,
        response_format: TTS_FORMAT,
      }),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new (class TtsUnreachable extends Error {
      readonly code = "TTS_PROVIDER_UNREACHABLE";
    })(`TTS provider request failed: ${String(error)}`);
  }
  if (!response.ok) {
    const detail = (await response.text().catch(() => "")).slice(0, 160);
    throw new (class TtsRejected extends Error {
      readonly code = "TTS_PROVIDER_CALL_FAILED";
    })(`TTS provider returned ${response.status}: ${detail}`);
  }
  const audio = new Uint8Array(await response.arrayBuffer());
  if (!audio.byteLength) {
    throw new (class TtsEmptyAudio extends Error {
      readonly code = "TTS_PROVIDER_EMPTY_AUDIO";
    })("TTS provider returned an empty audio body");
  }
  const sha256 = createHash("sha256").update(audio).digest("hex");
  const takeId = `VTK-${sha256.slice(0, 8)}`;
  return { takeId, bytes: audio.byteLength, sha256, provider: config.provider, model: config.model };
}
