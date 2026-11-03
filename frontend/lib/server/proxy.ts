import { NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL || "http://127.0.0.1:8000";
const API_KEY = process.env.API_KEY || process.env.RECOMMENDER_API_KEY || "";
const DEFAULT_TIMEOUT_MS = 60000;

export interface ProxyOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
  timeoutMs?: number;
}

export async function proxyToBackend(backendPath: string, options: ProxyOptions = {}): Promise<NextResponse> {
  const url = `${API_BASE_URL}${backendPath.startsWith("/") ? "" : "/"}${backendPath}`;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  // Sanitize headers: strictly block forwarding of client credentials or auth
  const safeHeaders: Record<string, string> = {};
  if (options.headers) {
    for (const [key, val] of Object.entries(options.headers)) {
      const lower = key.toLowerCase();
      if (lower !== "x-api-key" && lower !== "authorization" && lower !== "cookie") {
        safeHeaders[key] = val;
      }
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...safeHeaders,
  };

  if (API_KEY) {
    headers["x-api-key"] = API_KEY;
  }

  try {
    const res = await fetch(url, {
      method: options.method || "GET",
      headers,
      body: options.body,
      signal: AbortSignal.timeout(timeoutMs),
      cache: "no-store",
    });

    const contentType = res.headers.get("content-type") || "";
    const retryAfter = res.headers.get("retry-after");
    const responseHeaders: Record<string, string> = {};
    if (retryAfter) {
      responseHeaders["Retry-After"] = retryAfter;
    }

    if (contentType.includes("application/json")) {
      const data = await res.json();
      return NextResponse.json(data, {
        status: res.status,
        headers: Object.keys(responseHeaders).length > 0 ? responseHeaders : undefined,
      });
    }

    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: {
        "Content-Type": contentType || "text/plain",
        ...responseHeaders,
      },
    });
  } catch (err: unknown) {
    console.error("[proxy]", backendPath, err);
    const isTimeout = err instanceof Error && (err.name === "TimeoutError" || err.name === "AbortError");
    const statusCode = isTimeout ? 504 : 502;
    const errorCode = isTimeout ? "GATEWAY_TIMEOUT" : "BAD_GATEWAY";
    const message = isTimeout
      ? "The recommender service took too long to respond."
      : "The recommender service is unavailable.";

    return NextResponse.json(
      {
        error: {
          code: errorCode,
          message,
        },
      },
      { status: statusCode },
    );
  }
}
