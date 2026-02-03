import { NextResponse } from "next/server";
import { type NextRequest } from 'next/server';

export async function GET(req: NextRequest) {
  const searchParams = req.nextUrl.searchParams;
  const page = searchParams.get('page') || '1';
  const pageSize = searchParams.get('page_size') || '10';
  const sortBy = searchParams.get('sort_by') || 'bill_date';
  const sortOrder = searchParams.get('sort_order') || 'desc';
  const search = searchParams.get('search') || '';

  const userId = "u1"; // hardcoded for now, ideal: get from session

  const backendUrl = new URL("http://localhost:8000/bills");
  backendUrl.searchParams.append("user_id", userId);
  backendUrl.searchParams.append("page", page);
  backendUrl.searchParams.append("page_size", pageSize);
  backendUrl.searchParams.append("sort_by", sortBy);
  backendUrl.searchParams.append("sort_order", sortOrder);
  if (search) backendUrl.searchParams.append("search", search);

  try {
    const response = await fetch(backendUrl.toString());
    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`);
    }
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching bills:", error);
    return NextResponse.json({ error: "Failed to fetch bills" }, { status: 500 });
  }
}
