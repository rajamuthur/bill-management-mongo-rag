import { writeFile, mkdir } from "fs/promises";
import path from "path";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const formData = await req.formData();
  const file = formData.get("file") as File;
  let filePath: string | null;

  let data: any = {
    user_id: "u1",
    file_path: file ? "" : null,
    metadata: {
      category: formData.get("category"),
      total_amount: Number(formData.get("total_amount")),
    },
  }
  if (file) {
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // ✅ Ensure uploads directory exists
    const uploadDir = path.join(process.cwd(), "uploads");
    await mkdir(uploadDir, { recursive: true });

    filePath = path.join(uploadDir, file.name);
    data["file_path"] = filePath;
    console.log('[UPLOAD PATH]', filePath);
    // ✅ Write file
    await writeFile(filePath, buffer);
    // return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
  } else {
    // Manual entry mode
    filePath = null;
    data["bill"] = {
      vendor: formData.get("vendor"),
      bill_date: formData.get("bill_date"),
      category: formData.get("category"),
      total_amount: Number(formData.get("total_amount")),
      payment_method: formData.get("payment_method"),
      items: formData.get("items") ? JSON.parse(formData.get("items") as string) : [],
    };
  }

  console.log(data)


  // Send metadata + file path to Python
  const res = await fetch("http://localhost:8000/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  const backendData = await res.json();
  return NextResponse.json(backendData);
}
