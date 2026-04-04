import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const { keyword, ads } = await req.json();

    const Groq = (await import("groq-sdk")).default;
    const groq = new Groq({ apiKey: process.env.GROQ_API_KEY! });

    const adTitles = (ads as any[])
      .slice(0, 15)
      .map((a: any, i: number) => `${i + 1}. ${a.title}`)
      .join("\n");

    const completion = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      temperature: 0.2,
      max_tokens: 800,
      response_format: { type: "json_object" },
      messages: [
        {
          role: "system",
          content: `You are a strategic marketing analyst specializing in native advertising. Analyze the provided ads for a niche and return ONLY a JSON object with:
- top_hooks: array of the 3 most common psychological hooks (strings)
- dominant_angle: the primary winning strategy (string)
- pattern: observed textual or visual patterns (string)
- recommendation: one actionable strategic advice for competing in this niche (string)`,
        },
        {
          role: "user",
          content: `Niche/Keyword: ${keyword}\n\nAds:\n${adTitles}`,
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
