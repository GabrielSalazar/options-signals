import { NextResponse } from 'next/server';
import { BACKEND_URL } from '@/lib/config';

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ ticker: string }> },
) {
  try {
    const { ticker } = await params;
    const response = await fetch(
      `${BACKEND_URL}/market/indicators/${ticker.toUpperCase()}`,
      { signal: AbortSignal.timeout(30000) },
    );

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      return NextResponse.json(body, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching market indicators:', error);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
