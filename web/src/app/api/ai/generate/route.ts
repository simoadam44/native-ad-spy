import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const { title } = await req.json();

    const Groq = (await import("groq-sdk")).default;
    const groq = new Groq({ apiKey: process.env.GROQ_API_KEY! });

    const completion = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      temperature: 0.8,
      max_tokens: 400,
      response_format: { type: "json_object" },
      messages: [
        {
          role: "system",
          content: `You are a top native ad copywriter. Generate 3 high-converting headline variations. Use different angles: 1) curiosity, 2) fear of loss, 3) direct benefit. Return ONLY a JSON object with key "variants" containing an array of 3 strings.`,
        },
        {
          role: "user",
          content: `Original headline: ${title}`,
        },
      ],
    });

    const content = completion.choices[0]?.message?.content || '{"variants":[]}';
    const data = JSON.parse(content);

    return NextResponse.json(Array.isArray(data.variants) ? data.variants : []);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
