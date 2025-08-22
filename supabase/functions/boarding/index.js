// supabase/functions/boarding/index.ts
import { serve } from "https://deno.land/std@0.177.0/http/server.ts"

serve(async (req) => {
  try {
    const { qr_code } = await req.json()
    // Example: validate QR code
    if (!qr_code) {
      return new Response(JSON.stringify({ error: "Missing QR code" }), {
        headers: { "Content-Type": "application/json" },
        status: 400,
      })
    }

    // TODO: check participant in your DB
    return new Response(JSON.stringify({ message: "Boarded ✅", qr_code }), {
      headers: { "Content-Type": "application/json" },
      status: 200,
    })
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      headers: { "Content-Type": "application/json" },
      status: 500,
    })
  }
})
