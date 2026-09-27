interface Env {
  BACKEND_URL: string;
  EDGE_SHARED_SECRET: string;
}

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "Content-Type, X-Actor-Id, X-Actor-Roles",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      ...corsHeaders,
    },
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const incoming = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders,
      });
    }

    if (incoming.pathname === "/edge/health") {
      return json({
        status: "ok",
        service: "guardian-edge",
      });
    }

    if (!incoming.pathname.startsWith("/api/")) {
      return json({ detail: "not found" }, 404);
    }

    const target = new URL(env.BACKEND_URL);
    target.pathname = incoming.pathname.replace(/^\/api/, "");
    target.search = incoming.search;

    const headers = new Headers(request.headers);
    headers.set(
      "X-Guardian-Edge-Secret",
      env.EDGE_SHARED_SECRET,
    );
    headers.delete("Host");

    const response = await fetch(
      new Request(target.toString(), {
        method: request.method,
        headers,
        body:
          request.method === "GET" || request.method === "HEAD"
            ? undefined
            : request.body,
        redirect: "manual",
      }),
    );

    const outgoingHeaders = new Headers(response.headers);
    Object.entries(corsHeaders).forEach(([key, value]) => {
      outgoingHeaders.set(key, value);
    });

    return new Response(response.body, {
      status: response.status,
      headers: outgoingHeaders,
    });
  },
};
