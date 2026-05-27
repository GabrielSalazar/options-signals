import { NextResponse } from 'next/server';
import { BACKEND_URL } from '@/lib/config';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/signals/strategies`, {
      signal: AbortSignal.timeout(15000),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch strategies from backend' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching strategies:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
