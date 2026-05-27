import { NextResponse } from 'next/server';
import { BACKEND_URL } from '@/lib/config';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { ticker, strategy_name, days, initial_capital } = body;

    if (!ticker || !strategy_name || !days || !initial_capital) {
      return NextResponse.json(
        { error: 'Missing required fields: ticker, strategy_name, days, initial_capital' },
        { status: 400 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/backtest/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticker, strategy_name, days, initial_capital }),
      signal: AbortSignal.timeout(60000),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to run backtest from backend' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error running backtest:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
