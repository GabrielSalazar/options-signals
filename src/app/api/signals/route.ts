import { NextResponse } from 'next/server';
import { BACKEND_URL } from '@/lib/config';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = Math.max(1, parseInt(searchParams.get('limit') || '50') || 50);
    const offset = Math.max(0, parseInt(searchParams.get('offset') || '0') || 0);

    const response = await fetch(
      `${BACKEND_URL}/signals/history?limit=${limit}&offset=${offset}`,
      { signal: AbortSignal.timeout(15000) }
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch signals from backend' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching signals:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
