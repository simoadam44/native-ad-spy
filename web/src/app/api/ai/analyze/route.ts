import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const { title, network, landing } = await req.json();

    const Groq = (await import("groq-sdk")).default;
    const groq = new Groq({ apiKey: process.env.GROQ_API_KEY! });

    const completion = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      temperature: 0.3,
      max_tokens: 600,
      response_format: { type: "json_object" },
      messages: [
        {
          role: "system",
          content: `You are a world-class native advertising analyst. Analyze the given ad and return ONLY a JSON object with these exact keys:
- hook: the psychological trigger used (string)
- angle: one of "fear | curiosity | gain | pain | social" (string)
- audience: who this ad targets (string)
- cta_type: type of call to action (string)
- score: performance rating 1-10 (integer)
- tip: one specific actionable improvement (string)`,
        },
        {
          role: "user",
          content: `Headline: ${title}\nNetwork: ${network || "unknown"}\nLanding: ${landing || "N/A"}`,
        },
      ],
    });

    const content = completion.choices[0]?.message?.content || "{}";
    const data = JSON.parse(content);

    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
