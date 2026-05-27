'use client'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'

const exampleSignals = [
  {
    ticker: 'PETR4',
    tipo: 'CALL',
    score: 8,
    preco: 37.50,
    strike: 39.38,
    entrada: '0.40-0.50',
    alvo1: 0.56,
    alvo2: 1.13,
    rr: '0.8x',
    dte: 21,
  },
  {
    ticker: 'VALE3',
    tipo: 'PUT',
    score: 7,
    preco: 68.20,
    strike: 64.59,
    entrada: '0.34-0.42',
    alvo1: 0.47,
    alvo2: 0.95,
    rr: '0.68x',
    dte: 21,
  },
  {
    ticker: 'MGLU3',
    tipo: 'CALL',
    score: 9,
    preco: 9.85,
    strike: 10.95,
    entrada: '0.29-0.35',
    alvo1: 0.40,
    alvo2: 0.80,
    rr: '0.91x',
    dte: 21,
  },
]

export default function SignalsTable() {
  return (
    <div className="border border-gray-800 rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="border-gray-800 hover:bg-gray-800/30">
            <TableHead>Ativo</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead>Score</TableHead>
            <TableHead>Preço</TableHead>
            <TableHead>Strike</TableHead>
            <TableHead>Entrada</TableHead>
            <TableHead>Alvo 1</TableHead>
            <TableHead>Alvo 2</TableHead>
            <TableHead>R/R</TableHead>
            <TableHead>DTE</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {exampleSignals.map((signal) => (
            <TableRow key={signal.ticker} className="border-gray-800 hover:bg-gray-800/30">
              <TableCell className="font-bold">{signal.ticker}</TableCell>
              <TableCell>
                <Badge variant={signal.tipo === 'CALL' ? 'default' : 'destructive'}>
                  {signal.tipo === 'CALL' ? '🟢 CALL' : '🔴 PUT'}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant="outline">{signal.score}/10</Badge>
              </TableCell>
              <TableCell>R$ {signal.preco.toFixed(2)}</TableCell>
              <TableCell>R$ {signal.strike.toFixed(2)}</TableCell>
              <TableCell className="text-sm">{signal.entrada}</TableCell>
              <TableCell className="text-green-400 font-bold">R$ {signal.alvo1.toFixed(2)}</TableCell>
              <TableCell className="text-green-400 font-bold">R$ {signal.alvo2.toFixed(2)}</TableCell>
              <TableCell className={signal.rr === '0.68x' ? 'text-yellow-400' : 'text-green-400'}>
                {signal.rr}
              </TableCell>
              <TableCell>{signal.dte}d</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
