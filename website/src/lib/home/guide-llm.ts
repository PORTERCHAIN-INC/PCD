/**
 * Capacity Guide LLM provider — Groq (default) or NVIDIA NIM OpenAI-compatible.
 * Marketing chat only; not on the booking money path.
 */
import { groq } from "@ai-sdk/groq";
import { createOpenAI } from "@ai-sdk/openai";
import type { LanguageModel } from "ai";

export type GuideLlmProvider = "groq" | "nvidia";

export function resolveGuideProvider(): GuideLlmProvider {
  const raw = (process.env.CAPACITY_GUIDE_PROVIDER || "groq").trim().toLowerCase();
  if (raw === "nvidia" || raw === "nim" || raw === "nvidia_nim") return "nvidia";
  return "groq";
}

export function guideChatModel(): {
  provider: GuideLlmProvider;
  model: LanguageModel;
  modelId: string;
} {
  const provider = resolveGuideProvider();
  if (provider === "nvidia") {
    const apiKey = process.env.NVIDIA_API_KEY?.trim() || process.env.NGC_API_KEY?.trim();
    if (!apiKey) {
      throw new Error("NVIDIA_API_KEY is required when CAPACITY_GUIDE_PROVIDER=nvidia");
    }
    const baseURL = (
      process.env.NVIDIA_API_BASE?.trim() || "https://integrate.api.nvidia.com/v1"
    ).replace(/\/$/, "");
    const modelId = process.env.NVIDIA_MODEL?.trim() || "openai/gpt-oss-20b";
    const client = createOpenAI({ apiKey, baseURL });
    return { provider, model: client(modelId), modelId };
  }

  const modelId = process.env.GROQ_MODEL?.trim() || "llama-3.3-70b-versatile";
  return { provider: "groq", model: groq(modelId), modelId };
}

export function guideRouterModel(): { provider: GuideLlmProvider; model: LanguageModel } | null {
  const provider = resolveGuideProvider();
  if (provider === "nvidia") {
    const apiKey = process.env.NVIDIA_API_KEY?.trim() || process.env.NGC_API_KEY?.trim();
    if (!apiKey) return null;
    const baseURL = (
      process.env.NVIDIA_API_BASE?.trim() || "https://integrate.api.nvidia.com/v1"
    ).replace(/\/$/, "");
    const modelId =
      process.env.NVIDIA_ROUTER_MODEL?.trim() ||
      process.env.NVIDIA_MODEL?.trim() ||
      "openai/gpt-oss-20b";
    const client = createOpenAI({ apiKey, baseURL });
    return { provider, model: client(modelId) };
  }
  if (!process.env.GROQ_API_KEY?.trim()) return null;
  const modelId = process.env.GROQ_ROUTER_MODEL?.trim() || "llama-3.1-8b-instant";
  return { provider: "groq", model: groq(modelId) };
}

export function guideProviderConfigured(): boolean {
  const provider = resolveGuideProvider();
  if (provider === "nvidia") {
    return Boolean(process.env.NVIDIA_API_KEY?.trim() || process.env.NGC_API_KEY?.trim());
  }
  return Boolean(process.env.GROQ_API_KEY?.trim());
}
