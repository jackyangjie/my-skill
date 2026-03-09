import path from "node:path";
import { readFile } from "node:fs/promises";
import type { CliArgs } from "../types";

export function getDefaultModel(): string {
  return process.env.OPENAI_IMAGE_MODEL || "gpt-image-1.5";
}

type OpenAIImageResponse = { data: Array<{ url?: string; b64_json?: string }> };

function parseAspectRatio(ar: string): { width: number; height: number } | null {
  const match = ar.match(/^(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)$/);
  if (!match) return null;
  const w = parseFloat(match[1]!);
  const h = parseFloat(match[2]!);
  if (w <= 0 || h <= 0) return null;
  return { width: w, height: h };
}

type SizeMapping = {
  square: string;
  landscape: string;
  portrait: string;
};

function getOpenAISize(
  model: string,
  ar: string | null,
  quality: CliArgs["quality"]
): string {
  const isDalle3 = model.includes("dall-e-3");
  const isDalle2 = model.includes("dall-e-2");

  if (isDalle2) {
    return "1024x1024";
  }

  const sizes: SizeMapping = isDalle3
    ? {
        square: "1024x1024",
        landscape: "1792x1024",
        portrait: "1024x1792",
      }
    : {
        square: "1024x1024",
        landscape: "1536x1024",
        portrait: "1024x1536",
      };

  if (!ar) return sizes.square;

  const parsed = parseAspectRatio(ar);
  if (!parsed) return sizes.square;

  const ratio = parsed.width / parsed.height;

  if (Math.abs(ratio - 1) < 0.1) return sizes.square;
  if (ratio > 1.5) return sizes.landscape;
  if (ratio < 0.67) return sizes.portrait;
  return sizes.square;
}

export async function generateImage(
  prompt: string,
  model: string,
  args: CliArgs
): Promise<Uint8Array> {
  const baseURL = process.env.OPENAI_BASE_URL || "https://api.openai.com/v1";
  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) throw new Error("OPENAI_API_KEY is required");

  const size = args.size || getOpenAISize(model, args.aspectRatio, args.quality);

  if (args.referenceImages.length > 0) {
    if (model.includes("dall-e-2") || model.includes("dall-e-3")) {
      throw new Error(
        "Reference images with OpenAI in this skill require GPT Image models. Use --model gpt-image-1.5 (or another gpt-image model)."
      );
    }
    return generateWithOpenAIEdits(baseURL, apiKey, prompt, model, size, args.referenceImages, args.quality);
  }

  return generateWithOpenAIGenerations(baseURL, apiKey, prompt, model, size, args.quality);
}

async function generateWithOpenAIGenerations(
  baseURL: string,
  apiKey: string,
  prompt: string,
  model: string,
  size: string,
  quality: CliArgs["quality"]
): Promise<Uint8Array> {
  const body: Record<string, any> = { model, prompt, size };

  if (model.includes("dall-e-3")) {
    body.quality = quality === "2k" ? "hd" : "standard";
  }

  // Check if using ModelScope (async mode required)
  const isModelScope = baseURL.includes("modelscope.cn");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${apiKey}`,
  };
  
  if (isModelScope) {
    headers["X-ModelScope-Async-Mode"] = "true";
  }

  const res = await fetch(`${baseURL}/images/generations`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`OpenAI API error: ${err}`);
  }

  // Handle ModelScope async response
  if (isModelScope) {
    const asyncResult = await res.json() as { task_id?: string; id?: string };
    const taskId = asyncResult.task_id || asyncResult.id;
    if (!taskId) {
      throw new Error("No task_id in ModelScope async response");
    }
    return await pollModelScopeTask(baseURL, apiKey, taskId);
  }

  const result = (await res.json()) as OpenAIImageResponse;
  return extractImageFromResponse(result);
}

// Poll ModelScope async task until completion
async function pollModelScopeTask(
  baseURL: string,
  apiKey: string,
  taskId: string,
  maxAttempts = 60,
  intervalMs = 2000
): Promise<Uint8Array> {
  const taskUrl = `${baseURL.replace(/\/$/, "")}/tasks/${taskId}`;
  
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
    
    const res = await fetch(taskUrl, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`ModelScope task query error: ${err}`);
    }

    const result = await res.json() as { 
      status?: string; 
      state?: string;
      output?: { url?: string; image_url?: string; images?: Array<{ url?: string }> };
      results?: { url?: string; image_url?: string };
    };
    
    const status = result.status || result.state;
    
    if (status === "SUCCEEDED" || status === "COMPLETED") {
      // Extract image URL from various possible locations
      const imageUrl = result.output?.url || 
                       result.output?.image_url || 
                       result.results?.url || 
                       result.results?.image_url ||
                       result.output?.images?.[0]?.url;
      
      if (imageUrl) {
        const imgRes = await fetch(imageUrl);
        if (!imgRes.ok) throw new Error("Failed to download generated image");
        const buf = await imgRes.arrayBuffer();
        return new Uint8Array(buf);
      }
      throw new Error("Task completed but no image URL found");
    }
    
    if (status === "FAILED" || status === "ERROR") {
      throw new Error(`ModelScope task failed: ${JSON.stringify(result)}`);
    }
    
    // Continue polling for PENDING, RUNNING, etc.
  }
  
  throw new Error(`ModelScope task polling timeout after ${maxAttempts} attempts`);
}

async function generateWithOpenAIEdits(
  baseURL: string,
  apiKey: string,
  prompt: string,
  model: string,
  size: string,
  referenceImages: string[],
  quality: CliArgs["quality"]
): Promise<Uint8Array> {
  const form = new FormData();
  form.append("model", model);
  form.append("prompt", prompt);
  form.append("size", size);

  if (model.includes("gpt-image")) {
    form.append("quality", quality === "2k" ? "high" : "medium");
  }

  for (const refPath of referenceImages) {
    const bytes = await readFile(refPath);
    const filename = path.basename(refPath);
    const mimeType = getMimeType(filename);
    const blob = new Blob([bytes], { type: mimeType });
    form.append("image[]", blob, filename);
  }

  const res = await fetch(`${baseURL}/images/edits`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
    },
    body: form,
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`OpenAI edits API error: ${err}`);
  }

  const result = (await res.json()) as OpenAIImageResponse;
  return extractImageFromResponse(result);
}

function getMimeType(filename: string): string {
  const ext = path.extname(filename).toLowerCase();
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".webp") return "image/webp";
  if (ext === ".gif") return "image/gif";
  return "image/png";
}

async function extractImageFromResponse(result: OpenAIImageResponse): Promise<Uint8Array> {
  const img = result.data[0];

  if (img?.b64_json) {
    return Uint8Array.from(Buffer.from(img.b64_json, "base64"));
  }

  if (img?.url) {
    const imgRes = await fetch(img.url);
    if (!imgRes.ok) throw new Error("Failed to download image");
    const buf = await imgRes.arrayBuffer();
    return new Uint8Array(buf);
  }

  throw new Error("No image in response");
}
