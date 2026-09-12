#!/usr/bin/env node
// Live RPC smoke probe for mint-field-guide engines (wave-3 process lesson:
// every RPC-touching engine gets a live probe BEFORE ship — mocks passing is
// not evidence the provider accepts the call shape).
//
// Usage: node live-rpc-smoke.mjs [RPC_URL] [BLOCKS]
//   RPC_URL defaults to Robinhood mainnet; BLOCKS defaults to 1000.
// Exit 0 = sweep answered within the block-range cap; exit 1 = provider error.
//
// For other engines, copy the pattern: one real request of the exact shape the
// engine sends, print volume + distinct keys + latency, fail loudly on error.

const RPC = process.argv[2] || "https://rpc.mainnet.chain.robinhood.com";
const BLOCKS = parseInt(process.argv[3] || "1000", 10);
const ERC721_TRANSFER =
  "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";

const t0 = Date.now();
const post = async (body) => {
  const res = await fetch(RPC, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
};

const head = parseInt((await post({ jsonrpc: "2.0", id: 1, method: "eth_blockNumber", params: [] })).result, 16);
const from = head - BLOCKS + 1;
console.log(`rpc=${RPC} head=${head} scanning ${from}..${head} (${BLOCKS} blocks)`);

const j = await post({
  jsonrpc: "2.0",
  id: 2,
  method: "eth_getLogs",
  params: [{
    fromBlock: "0x" + from.toString(16),
    toBlock: "0x" + head.toString(16),
    topics: [ERC721_TRANSFER],
  }],
});
const ms = Date.now() - t0;
if (j.error) {
  console.log(`ERROR after ${ms}ms:`, JSON.stringify(j.error));
  process.exit(1);
}
const logs = j.result;
const addrs = new Set(logs.map((l) => l.address.toLowerCase()));
console.log(`logs=${logs.length} distinctContracts=${addrs.size} in ${ms}ms`);
console.log([...addrs].slice(0, 10).join("\n"));
