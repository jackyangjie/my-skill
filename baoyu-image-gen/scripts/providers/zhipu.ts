import type { CliArgs } from "../types";

export function getDefaultModel(): string {
  return process.env.ZHIPU_IMAGE_MODEL || "glm-image";
}

// Map aspect ratio to Zhipu size
function getZhipuSize(ar: string | null): string {
  const sizeMap: Record<string, string> = {
    "1:1": "1280x1280",
    "16:9": "1728x960",
    "9:16": "960x1728",
    "4:3": "1472x1088",
    "3:4": "1088x1472",
    "2.35:1": "1728x960",
  };
  
  if (!ar) return "1280x1280";
  return sizeMap[ar] || "1280x1280";
}

interface AsyncImageResponse {
  id: string;
  request_id: string;
  task_status: string;
  model?: string;
}

interface AsyncResultResponse {
  id: string;
  request_id: string;
  model: string;
  task_status: string;
  image_result?: Array<{
    url: string;
  }>;
  error?: {
    code: string;
    message: string;
  };
}

export async function generateImage(
  prompt: string,
  model: string,
  args: CliArgs
): Promise<Uint8Array> {
  const apiKey = process.env.ZHIPU_API_KEY;
  if (!apiKey) {
    throw new Error("ZHIPU_API_KEY is required");
  }

  const baseURL = process.env.ZHIPU_BASE_URL || "https://open.bigmodel.cn/api/coding";
  const size = getZhipuSize(args.aspectRatio);

  // Step 1: Submit async image generation task
  const submitRes = await fetch(`${baseURL}/paas/v4/async/images/generations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: model || "glm-image",
      prompt,
      size,
      quality: args.quality === "2k" ? "hd" : undefined,
    }),
  });

  if (!submitRes.ok) {
    const err = await submitRes.text();
    throw new Error(`Zhipu API error: ${err}`);
  }

  const submitResult = (await submitRes.json()) as AsyncImageResponse;
  const taskId = submitResult.id;

  if (!taskId) {
    throw new Error("No task ID returned from Zhipu API");
  }

  // Step 2: Poll for task completion
  return await pollZhipuTask(baseURL, apiKey, taskId);
}

async function pollZhipuTask(
  baseURL: string,
  apiKey: string,
  taskId: string,
  maxAttempts = 60,
  intervalMs = 2000
): Promise<Uint8Array> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, intervalMs));

    const res = await fetch(`${baseURL}/paas/v4/async-result/${taskId}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Zhipu task query error: ${err}`);
    }

    const result = (await res.json()) as AsyncResultResponse;
    const status = result.task_status;

    if (status === "SUCCESS") {
      const imageUrl = result.image_result?.[0]?.url;
      if (!imageUrl) {
        throw new Error("Task succeeded but no image URL found");
      }

      const imgRes = await fetch(imageUrl);
      if (!imgRes.ok) {
        throw new Error("Failed to download generated image");
      }

      const buf = await imgRes.arrayBuffer();
      return new Uint8Array(buf);
    }

    if (status === "FAIL") {
      throw new Error(
        `Zhipu task failed: ${result.error?.message || JSON.stringify(result)}`
      );
    }

    // Continue polling for PROCESSING status
  }

  throw new Error(
    `Zhipu task polling timeout after ${maxAttempts} attempts`
  );
}
