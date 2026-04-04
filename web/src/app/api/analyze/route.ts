import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
});

export async function POST(req: Request) {
  try {
    const { title, network } = await req.json();

    const response = await anthropic.messages.create({
      model: "claude-3-5-sonnet-20241022",
      max_tokens: 1000,
      temperature: 0,
      system: "You are a senior marketing analyst. Analyze the native ad based on its headline and network. Return only a JSON object with: hook, angle, score (1-10), and tip.",
      messages: [
        {
          role: "user",
          content: `Analyze this ad:\nHeadline: ${title}\nNetwork: ${network}`,
        },
      ],
    });

    // استخراج النص من رد كلود
    const content = (response.content[0] as any).text;
    const jsonMatch = content.match(/\{.*\}/s);
    const data = jsonMatch ? JSON.parse(jsonMatch[0]) : { error: "Failed to parse AI response" };

    return NextResponse.json(data);
  } catch (error: any) {
    console.error("AI Analysis Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
