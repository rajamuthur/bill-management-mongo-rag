import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = await req.json();

  if (body.userId !== "u1") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const response = await fetch("http://localhost:8000/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: body.userId,
      query: body.query
    })
  });

  const data = await response.json();
  return NextResponse.json(data);
}
