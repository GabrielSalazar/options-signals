import { NextResponse } from 'next/server';
import { ScanResponse } from '@/types/signals';
import { BACKEND_URL } from '@/lib/config';

export async function POST(request: Request) {
  try {
    const { ticker, filters } = await request.json();

    if (!ticker) {
      return NextResponse.json({ error: 'Ticker is required' }, { status: 400 });
    }

    const queryParams = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        queryParams.append(key, String(value));
      });
    }

    const qs = queryParams.toString();
    const url = `${BACKEND_URL}/signals/scan/${ticker}${qs ? '?' + qs : ''}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(15000),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to scan signals from backend' },
        { status: response.status }
      );
    }

    const data: ScanResponse = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error scanning signals:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const ticker = searchParams.get('ticker');

    if (!ticker) {
      return NextResponse.json({ error: 'Ticker is required' }, { status: 400 });
    }

    const qs = new URLSearchParams(
      Array.from(searchParams.entries()).filter(([k]) => k !== 'ticker')
    ).toString();

    const response = await fetch(
      `${BACKEND_URL}/signals/scan/${ticker}${qs ? '?' + qs : ''}`,
      {
        method: 'GET',
        signal: AbortSignal.timeout(15000),
      }
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to scan signals from backend' },
        { status: response.status }
      );
    }

    const data: ScanResponse = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error scanning signals:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
