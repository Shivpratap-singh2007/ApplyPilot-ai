import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

async function proxyToBackend(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const { path } = await context.params;
  const backendBase = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
  const query = request.nextUrl.search;
  const targetUrl = `${backendBase}/api/v1/${path.join("/")}${query}`;

  const forwardHeaders = new Headers();
  for (const name of ["authorization", "cookie", "content-type", "x-csrf-token", "accept"]) {
    const val = request.headers.get(name);
    if (val) forwardHeaders.set(name, val);
  }

  const method = request.method.toUpperCase();
  const body = method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer();

  const upstream = await fetch(targetUrl, {
    method,
    headers: forwardHeaders,
    body,
    redirect: "manual",
  });

  const respHeaders = new Headers();
  for (const [k, v] of upstream.headers.entries()) {
    const lower = k.toLowerCase();
    if (lower === "set-cookie" || lower === "transfer-encoding" || lower === "content-encoding") {
      continue;
    }
    respHeaders.set(k, v);
  }

  const setCookies =
    typeof upstream.headers.getSetCookie === "function" ? upstream.headers.getSetCookie() : [];
  for (const cookie of setCookies) {
    respHeaders.append("set-cookie", cookie);
  }

  const respBody = await upstream.arrayBuffer();
  return new Response(respBody, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: respHeaders,
  });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToBackend(req, ctx);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToBackend(req, ctx);
}

export async function PUT(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToBackend(req, ctx);
}

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToBackend(req, ctx);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToBackend(req, ctx);
}

