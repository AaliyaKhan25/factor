import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Redirect signed-out visitors to /login once sessions are wired up.
export function middleware(_req: NextRequest) {
  return NextResponse.next();
}

export const config = { matcher: ["/dashboard/:path*"] };
