# Runtime address book + stale paused flag (TRIALS.EXE case, 2026-08-31)

Some mints are heavy client-side games with NO contract address in the HTML or
in the JS bundles. The address book is fetched at RUNTIME from a JSON file at
the site root. Two things bit us on trialsexe.com; both generalize.

## 1. Find the address book: fetch `<site>/deployed.json`

`www.trialsexe.com` loaded `chain.js`, which resolved its contracts like this:

```js
const bookFile = new URLSearchParams(location.search).get("net") === "testnet"
  ? "deployed.testnet.json" : "deployed.json";
const [book, ...abis] = await Promise.all([
  fetch(bookFile).then(r => r.json()),
  ...NAMES.map(n => fetch("abi/" + n + ".json").then(r => r.json())),
]);
ADDR = book.contracts;
```

So: `curl -A <UA> https://<site>/deployed.json` → `{"chainId":4663, "rpc":"...",
"contracts": {Name: address, ...}}`. The contract addresses were NOT in the
HTML and NOT in any `.js` chunk — only the zero address showed up in a grep.
When a site has 10+ named contracts (SigilSBT, TrialGate, TrialToken, Forge,
CryptResolver, OracleResolver, ArenaResolver, ...), expect a `contracts` map
in the runtime JSON, plus the ABI per contract at `abi/<Name>.json`.

The same URL search param tells you there is a TESTNET variant
(`deployed.testnet.json`) — check the param, then always pull mainnet's book.

## 2. `paused: true` in the config can be STALE — trust on-chain, not the flag

The deployed.json said `"paused": true` and listed a large `retired` set of
addresses (several contracts redeployed the same day). That would make you
conclude the whole machine is halted. It was NOT: the live gate returned
`TrialGate.isOpen() = true` and `available() = 2786`.

**Do not decide mintability off a config flag.** The `deployer`/`adminMint`
and `retired` maps show this project redeploys and re-points contracts; the
config snapshot lags. Query the live gate controller on-chain:

```python
# TrialGate (the mint gate) exposed: isOpen(), status(), available(),
# closed(). TrialToken exposed totalSupply(), taxState().
isOpen()  -> 0x...1   # TRUE = mint open
available() -> 0xae2   # 2786 mint slots left
closed()  -> 0x0       # FALSE = not closed
```

Decode with the selector helper in SKILL.md `Pitfalls` (keccak via
pycryptodome). `status()` returned a multi-word packed struct — decode word by
word, don't `int(...)` the whole hex.

## 3. Chain RPC rate-limits with 429, not just 403

`rpc.mainnet.chain.robinhood.com` returned `HTTPError 429 Too Many Requests`
on intermittent `eth_call`s — the same Robinhood RPC flakiness the Wallet
Radar daemon hit. It intermittently succeeded on retry. Pattern that worked:

```python
HDRS = {"User-Agent":"Mozilla/5.0", "Content-Type":"application/json",
        "Origin": "https://<site>"}   # browser-style headers
for i in range(tries):
    try: ...urlopen(req, timeout=20).... return json.load(r)["result"]
    except: time.sleep(2 + i)   # linear backoff, then fall through
return "ERR_RATE_LIMITED"
```

- Send `Origin` + browser `User-Agent` (the 403 fix from SKILL.md step 7 also
  applies to 429s).
- Never conclude a view is unavailable from a single 429 — retry ~6x.
- `closed()` was the only call that answered on the first try; `isOpen()`
  and `status()` needed retries. Probe several views and treat 429 per-call.

## 4. "Free mint" is about the mint price, not the automation cost

meta: "Free mint on Robinhood Chain. No allowlist, no snapshot, no price."
but the actual mint is gated behind passing THREE on-chain trials before you
can consume the gate. The token also carried a 2.5-5% transfer tax
(`taxState()` returned 250/250/500/250/250 bps + fee wallets). Always read the
full config and ABI before promising a "free" mint is one click — it may be
a multi-trial quest needing PoW mining, a riddle bank, and an arena opponent.
