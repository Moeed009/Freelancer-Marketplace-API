// supabase/functions/send-email/index.ts
//
// Accepts: { "to": "email@example.com", "subject": "Subject", "body": "Email body" }
// Sends the email through SendGrid (Single Sender Verification, no domain needed)
// and returns { success: true } or { success: false, error }.

import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

const SENDGRID_API_KEY = Deno.env.get("SENDGRID_API_KEY");
const FROM_EMAIL = Deno.env.get("FROM_EMAIL") ?? "";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return jsonResponse({ success: false, error: "Method not allowed" }, 405);
  }

  if (!SENDGRID_API_KEY) {
    return jsonResponse(
      { success: false, error: "SENDGRID_API_KEY is not configured on this function." },
      500,
    );
  }

  if (!FROM_EMAIL) {
    return jsonResponse(
      { success: false, error: "FROM_EMAIL is not configured on this function." },
      500,
    );
  }

  let payload: { to?: string; subject?: string; body?: string };
  try {
    payload = await req.json();
  } catch {
    return jsonResponse({ success: false, error: "Request body must be valid JSON." }, 400);
  }

  const { to, subject, body } = payload;

  if (!to || !subject || !body) {
    return jsonResponse(
      { success: false, error: "Fields 'to', 'subject' and 'body' are all required." },
      400,
    );
  }

  try {
    const sgResponse = await fetch("https://api.sendgrid.com/v3/mail/send", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${SENDGRID_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personalizations: [{ to: [{ email: to }] }],
        from: { email: FROM_EMAIL },
        subject: subject,
        content: [{ type: "text/plain", value: body }],
      }),
    });

    // SendGrid returns 202 with an EMPTY body on success - only errors have JSON.
    if (!sgResponse.ok) {
      let errorDetail: unknown;
      try {
        errorDetail = await sgResponse.json();
      } catch {
        errorDetail = await sgResponse.text();
      }
      // Forward SendGrid's status code so the FastAPI provider's
      // _classify_http_status() can correctly mark this Transient (5xx/429/408)
      // vs Permanent (e.g. 403, 400 bad sender) in the outbox.
      return jsonResponse({ success: false, error: errorDetail }, sgResponse.status);
    }

    const messageId = sgResponse.headers.get("x-message-id") ?? undefined;
    return jsonResponse({ success: true, message: "Email sent successfully", id: messageId }, 200);
  } catch (err) {
    console.error("send-email: unexpected error", err);
    return jsonResponse({ success: false, error: String(err) }, 500);
  }
});

function jsonResponse(data: unknown, status: number): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}