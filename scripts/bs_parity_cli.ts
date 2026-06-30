// scripts/bs_parity_cli.ts
// Uso: echo '{"s":100,"k":105,"t":0.5,"r":0.1065,"sigma":0.3,"type":"call"}' | npx tsx scripts/bs_parity_cli.ts
import fs from "fs";
import { callPrice, putPrice } from "../src/lib/black-scholes";

const input = JSON.parse(fs.readFileSync(0, "utf-8"));
const { s, k, t, r, sigma, type } = input;
const price = type === "call" ? callPrice(s, k, t, sigma, r, 0) : putPrice(s, k, t, sigma, r, 0);
console.log(JSON.stringify({ price }));
