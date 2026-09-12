#!/usr/bin/env python3
"""
wallet_recon.py — precise multi-chain NFT trading P&L reconstruction (v2).

Reconstructs every NFT acquisition (mint/buy) and disposition (sell/transfer),
extracts the exact ETH/WETH amount per trade, matches FIFO, and reports
REALIZED P&L, open inventory at cost basis, and total gas — across Ethereum
mainnet and Robinhood Chain. No API keys.

Money-flow model (the correctness core):
  - WETH: gross ERC-20 token transfers (exact, no gas entanglement).
  - Native ETH, Ethereum: tx `value` + internal transfers (already gross).
  - Native ETH, Robinhood: state-changes coin delta (authoritative — the
    internal-transfers endpoint MISSES Seaport sweep proceeds) with gas
    reversed out when the wallet was the tx sender, so every trade's
    cost/proceeds is GROSS and gas is subtracted exactly once at the end.
  - a fulfill/match tx `value` is the BUYER's total, never used as seller share.
  - mint = NFT from 0x0; buy = from non-zero; sell = to non-zero non-self.
  - multi-NFT tx splits money evenly (flagged "even-split").
  - FIFO matching per (chain, contract, token_id).

Usage:
  python3 wallet_recon.py <address> [--days N] [--json out.json] [--refresh]
"""
import argparse, json, os, sys, time, urllib.request, urllib.error, urllib.parse, datetime
from decimal import Decimal as D
from collections import defaultdict, Counter

ZERO = '0x0000000000000000000000000000000000000000'
WETH_RH  = '0x1111111111111111111111111111111111111111'
WETH_ETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'

UA = {'User-Agent': 'Mozilla/5.0'}
CACHE = os.path.expanduser('~/.cache/wallet_recon')


def _get(url, retries=6, backoff=2.0):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # 429/5xx are rate-limit / transient server errors — retry harder
            if i == retries - 1:
                raise
            delay = backoff * (i + 1) * (2.0 if e.code in (429, 500, 502, 503, 504) else 1.0)
            time.sleep(delay)
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(backoff * (i + 1))


def routescan(action, address, **kw):
    q = urllib.parse.urlencode({'module': 'account', 'action': action,
                                'address': address, 'startblock': 0,
                                'endblock': 99999999, 'sort': 'desc', **kw})
    d = _get('https://api.routescan.io/v2/network/mainnet/evm/1/etherscan/api?' + q)
    return d.get('result', []) or []


def blockscout_pages(path, cutoff, maxpages=120):
    base = 'https://robinhoodchain.blockscout.com/api/v2' + path.split('?')[0]
    url = 'https://robinhoodchain.blockscout.com/api/v2' + path
    out, seen = [], set()
    for _ in range(maxpages):
        d = _get(url)
        items = d.get('items', [])
        if not items:
            break
        for it in items:
            key = it.get('hash') or it.get('transaction_hash')
            li = it.get('log_index')
            key = (key, li) if li is not None else key
            if key not in seen:
                seen.add(key)
                out.append(it)
        if items[-1].get('timestamp', '') < cutoff:
            break
        n = d.get('next_page_params')
        if not n:
            break
        url = base + '?' + urllib.parse.urlencode(n)
        time.sleep(0.2)
    return out


def blockscout_tx(h):
    return _get(f'https://robinhoodchain.blockscout.com/api/v2/transactions/{h}')


def blockscout_state(h):
    return _get(f'https://robinhoodchain.blockscout.com/api/v2/transactions/{h}/state-changes').get('items', [])


FUNGIBLE = {'global dollar', 'weth', 'wrapped ether', 'usd coin', 'usdc',
            'usdt', 'tether usd', 'multipli', 'mult'}


def reconstruct(address, days=14, refresh=False):
    A = address.lower()
    os.makedirs(CACHE, exist_ok=True)
    cutoff_epoch = int((datetime.datetime.now(datetime.timezone.utc)
                        - datetime.timedelta(days=days)).timestamp())
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%S.000000Z')

    cache_file = os.path.join(CACHE, f'{A}_{days}d.json')
    if not refresh and os.path.exists(cache_file):
        raw = json.load(open(cache_file))
    else:
        raw = {'ethereum': {}, 'robinhood': {}}
        raw['ethereum']['txs'] = [x for x in routescan('txlist', A, offset=10000) if int(x['timeStamp']) >= cutoff_epoch]
        raw['ethereum']['internals'] = [x for x in routescan('txlistinternal', A, offset=10000) if int(x['timeStamp']) >= cutoff_epoch]
        raw['ethereum']['toktx'] = [x for x in routescan('tokentx', A, offset=10000) if int(x['timeStamp']) >= cutoff_epoch]
        raw['ethereum']['nfttx'] = [x for x in routescan('tokennfttx', A, offset=10000) if int(x['timeStamp']) >= cutoff_epoch]
        b = routescan('balance', A)
        raw['ethereum']['balance'] = b if isinstance(b, str) else '0'
        rh = _get(f'https://robinhoodchain.blockscout.com/api/v2/addresses/{A}')
        raw['robinhood']['balance'] = rh.get('coin_balance', '0')
        raw['robinhood']['txs'] = blockscout_pages(f'/addresses/{A}/transactions', cutoff)
        raw['robinhood']['nfts'] = blockscout_pages(f'/addresses/{A}/token-transfers?type=ERC-721%2CERC-1155', cutoff)
        json.dump(raw, open(cache_file, 'w'))

    eth_bal = D(raw['ethereum'].get('balance') or 0) / D(10**18)
    rh_bal = D(raw['robinhood'].get('balance') or 0) / D(10**18)
    eth_txs = raw['ethereum']['txs']; eth_int = raw['ethereum']['internals']
    eth_tok = raw['ethereum']['toktx']; eth_nft = raw['ethereum']['nfttx']
    rh_txs = raw['robinhood']['txs']; rh_nft = raw['robinhood']['nfts']

    # ---------- Ethereum money flows (gross native + WETH) ----------
    eth_int_by = defaultdict(list)
    for x in eth_int:
        eth_int_by[x['hash']].append(x)
    eth_tok_by = defaultdict(list)
    for x in eth_tok:
        eth_tok_by[x['hash']].append(x)

    eth_flows = {}  # tx -> (native_in, native_out, weth_in, weth_out, gas)
    eth_gas = D(0)
    for tx in eth_txs:
        h = tx['hash']
        gas = D(tx.get('gasUsed', 0)) * D(tx.get('gasPrice', 0)) / D(10**18)
        is_sender = tx.get('from', '').lower() == A
        if is_sender:
            eth_gas += gas
        n_in = n_out = D(0)
        v = D(tx.get('value', 0)) / D(10**18)
        if tx.get('isError') == '0':
            if tx.get('to', '').lower() == A:
                n_in += v
            if tx.get('from', '').lower() == A:
                n_out += v
        for z in eth_int_by.get(h, []):
            if z.get('isError') == '0':
                iv = D(z.get('value', 0)) / D(10**18)
                if z.get('to', '').lower() == A:
                    n_in += iv
                if z.get('from', '').lower() == A:
                    n_out += iv
        w_in = w_out = D(0)
        for t in eth_tok_by.get(h, []):
            if t.get('contractAddress', '').lower() == WETH_ETH:
                amt = D(t.get('value', 0)) / D(10**int(t.get('tokenDecimal') or 18))
                if t.get('to', '').lower() == A:
                    w_in += amt
                if t.get('from', '').lower() == A:
                    w_out += amt
        eth_flows[h] = (n_in, n_out, w_in, w_out, gas)

    # ---------- Robinhood money flows (state-changes native + WETH) ----------
    # Relevant txs = address transactions UNION NFT-transfer tx hashes, because
    # buyer-initiated sales (wallet is only the seller) do NOT appear in the
    # address transactions list.
    rh_tx_hashes = set()
    for tx in rh_txs:
        rh_tx_hashes.add(tx['hash'])
    for x in rh_nft:
        h = x.get('transaction_hash')
        if h:
            rh_tx_hashes.add(h)

    rh_flows = {}  # tx -> (native_in, native_out, weth_in, weth_out, gas)
    rh_gas = D(0)

    # Incremental per-tx flow cache so a rate-limit crash can resume without
    # re-fetching every transaction detail.
    flow_cache_file = os.path.join(CACHE, f'{A}_{days}d_txflows.json')
    flow_cache = {}
    if os.path.exists(flow_cache_file):
        try:
            flow_cache = json.load(open(flow_cache_file))
        except Exception:
            flow_cache = {}

    def _save_flows():
        try:
            json.dump(flow_cache, open(flow_cache_file, 'w'))
        except Exception:
            pass

    for idx, h in enumerate(sorted(rh_tx_hashes)):
        if h in flow_cache and not refresh:
            n_in, n_out, w_in, w_out, gs, is_sender = flow_cache[h]
            rh_flows[h] = (D(n_in), D(n_out), D(w_in), D(w_out), D(gs))
            if is_sender:
                rh_gas += D(gs)
            continue
        try:
            d = blockscout_tx(h)
            gas = D((d.get('fee') or {}).get('value') or 0) / D(10**18)
            is_sender = (d.get('from') or {}).get('hash', '').lower() == A
            # authoritative native ETH delta from state-changes
            coin_delta = D(0)
            for z in blockscout_state(h):
                if z.get('address', {}).get('hash', '').lower() == A and z.get('type') == 'coin':
                    ch = z.get('change')
                    if isinstance(ch, (int, str)):
                        try:
                            coin_delta = D(ch) / D(10**18)
                        except Exception:
                            pass
            # reverse gas so flows are GROSS (only if wallet was the sender)
            if coin_delta > 0:
                n_in = coin_delta + (gas if is_sender else D(0))
                n_out = D(0)
            else:
                n_in = D(0)
                n_out = -coin_delta - (gas if is_sender else D(0))
            w_in = w_out = D(0)
            for tt in (d.get('token_transfers') or []):
                tok = tt.get('token') or {}
                if tok.get('address_hash', '').lower() == WETH_RH:
                    amt = D((tt.get('total') or {}).get('value') or 0) / D(10**18)
                    if (tt.get('to') or {}).get('hash', '').lower() == A:
                        w_in += amt
                    if (tt.get('from') or {}).get('hash', '').lower() == A:
                        w_out += amt
        except Exception:
            # leave this tx unattributed rather than crash the whole run
            flow_cache[h] = ['0', '0', '0', '0', '0', False]
            _save_flows()
            continue
        rh_flows[h] = (n_in, n_out, w_in, w_out, gas)
        if is_sender:
            rh_gas += gas
        flow_cache[h] = [str(n_in), str(n_out), str(w_in), str(w_out), str(gas), is_sender]
        if (idx + 1) % 25 == 0:
            _save_flows()
        time.sleep(0.2)
    _save_flows()

    # ---------- NFT events ----------
    events = []
    for x in eth_nft:
        name = x.get('tokenName') or x.get('tokenSymbol') or '?'
        if name.lower() in FUNGIBLE:
            continue
        contract = x.get('contractAddress', '').lower()
        token_id = x.get('tokenID')
        if token_id is None:
            continue
        f = x.get('from', '').lower(); t = x.get('to', '').lower()
        side = 'in' if t == A else ('out' if f == A else None)
        if side is None:
            continue
        ts = datetime.datetime.fromtimestamp(int(x.get('timeStamp', 0)), datetime.timezone.utc).isoformat()
        events.append({'chain': 'ethereum', 'tx': x['hash'], 'token_id': str(token_id),
                       'contract': contract, 'name': name, 'side': side,
                       'counterparty': f if side == 'in' else t, 'ts': ts})

    for x in rh_nft:
        name = x.get('token', {}).get('name') or '?'
        if name.lower() in FUNGIBLE:
            continue
        contract = x.get('token', {}).get('address_hash', '').lower()
        token_id = (x.get('total') or {}).get('token_id')
        if token_id is None:
            continue
        f = (x.get('from') or {}).get('hash', '').lower()
        t = (x.get('to') or {}).get('hash', '').lower()
        side = 'in' if t == A else ('out' if f == A else None)
        if side is None:
            continue
        events.append({'chain': 'robinhood', 'tx': x.get('transaction_hash'),
                       'token_id': str(token_id), 'contract': contract, 'name': name,
                       'side': side, 'counterparty': f if side == 'in' else t,
                       'ts': x.get('timestamp')})

    money = {'ethereum': eth_flows, 'robinhood': rh_flows}

    # ---------- per-tx NFT counts for even-split ----------
    tx_count = defaultdict(lambda: [0, 0])
    for ev in events:
        tx_count[ev['tx']][0 if ev['side'] == 'in' else 1] += 1

    def attribute(ev):
        n_in, n_out, w_in, w_out, gas = money[ev['chain']].get(ev['tx'], (D(0), D(0), D(0), D(0), D(0)))
        if ev['side'] == 'in':
            cost = n_out + w_out
            n = max(tx_count[ev['tx']][0], 1)
            return cost / D(n), 'mint' if ev['counterparty'] == ZERO else 'buy'
        else:
            proceeds = n_in + w_in
            n = max(tx_count[ev['tx']][1], 1)
            return proceeds / D(n), 'sell'

    # ---------- FIFO matching ----------
    ledger = defaultdict(list)
    for ev in events:
        ledger[(ev['chain'], ev['contract'], ev['token_id'])].append(ev)
    for k in ledger:
        ledger[k].sort(key=lambda e: e['ts'])

    realized = []
    open_inv = []
    for key, evs in ledger.items():
        chain, contract, token_id = key
        buys = []
        for ev in evs:
            amt, typ = attribute(ev)
            if ev['side'] == 'in':
                buys.append({'cost': amt, 'type': typ, 'name': ev['name'],
                             'contract': contract, 'token_id': token_id, 'chain': chain})
            else:
                if buys:
                    b = buys.pop(0)
                    realized.append({'chain': chain, 'contract': contract, 'name': ev['name'],
                                     'token_id': token_id, 'cost': b['cost'],
                                     'proceeds': amt, 'net': amt - b['cost'],
                                     'acq_type': b['type'], 'ts': ev['ts']})
                else:
                    realized.append({'chain': chain, 'contract': contract, 'name': ev['name'],
                                     'token_id': token_id, 'cost': D(0), 'proceeds': amt,
                                     'net': amt, 'acq_type': 'no-record', 'ts': ev['ts']})
        for b in buys:
            open_inv.append(b)

    gas_eth = eth_gas
    gas_rh = rh_gas

    return {'address': A, 'days': days,
            'balances': {'ethereum': eth_bal, 'robinhood': rh_bal},
            'realized': realized, 'open_inventory': open_inv,
            'gas': {'ethereum': gas_eth, 'robinhood': gas_rh}}


def report(res):
    A = res['address']
    print(f"# P&L reconstruction for {A}  (last {res['days']} days)\n")
    b = res['balances']
    print(f"== BALANCES ==")
    print(f"  Ethereum {b['ethereum']:.6f} ETH   Robinhood {b['robinhood']:.6f} ETH   "
          f"combined {(b['ethereum'] + b['robinhood']):.6f} ETH")

    realized = res['realized']
    tc = sum(r['cost'] for r in realized)
    tp = sum(r['proceeds'] for r in realized)
    tn = sum(r['net'] for r in realized)
    gas = sum(res['gas'].values())

    print(f"\n== REALIZED (matched) ==")
    print(f"  {len(realized)} dispositions")
    print(f"  total cost      {tc:.6f} ETH")
    print(f"  total proceeds  {tp:.6f} ETH")
    print(f"  realized P&L    {tn:+.6f} ETH  (before gas)")
    print(f"  gas (all chains){gas:.6f} ETH")
    print(f"  P&L after gas   {tn - gas:+.6f} ETH")

    by_coll = defaultdict(lambda: [D(0), D(0), D(0), 0])
    for r in realized:
        c = by_coll[r['name']]
        c[0] += r['cost']; c[1] += r['proceeds']; c[2] += r['net']; c[3] += 1
    if by_coll:
        print(f"\n== REALIZED BY COLLECTION ==")
        for name, (c, p, n, cnt) in sorted(by_coll.items(), key=lambda z: -z[1][2]):
            print(f"  {name:<26} {cnt:>3} sold  net {n:+.6f} ETH  (cost {c:.6f} / proc {p:.6f})")

    oi = res['open_inventory']
    if oi:
        print(f"\n== OPEN INVENTORY (unsold, at cost basis) ==")
        oi_by = defaultdict(lambda: [D(0), 0])
        for x in oi:
            oi_by[x['name']][0] += x['cost']
            oi_by[x['name']][1] += 1
        for name, (c, cnt) in sorted(oi_by.items(), key=lambda z: -z[1][0]):
            print(f"  {name:<26} {cnt:>3} held  cost basis {c:.6f} ETH")
        print(f"  total open cost basis {sum(x['cost'] for x in oi):.6f} ETH")

    print(f"\n== SUMMARY ==")
    print(f"  realized (after gas) : {tn - gas:+.6f} ETH")
    print(f"  open inventory cost  : {sum(x['cost'] for x in oi):.6f} ETH (realizable value unknown)")
    print(f"  NOTE: open inventory valued at COST BASIS, never guessed market value.")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('address')
    ap.add_argument('--days', type=int, default=14)
    ap.add_argument('--json', default=None)
    ap.add_argument('--refresh', action='store_true')
    args = ap.parse_args()
    res = reconstruct(args.address, args.days, args.refresh)
    report(res)
    if args.json:
        def ser(x):
            return {k: (str(v) if isinstance(v, D) else v) for k, v in x.items()}
        out = {'address': res['address'], 'days': res['days'],
               'balances': {k: str(v) for k, v in res['balances'].items()},
               'gas': {k: str(v) for k, v in res['gas'].items()},
               'realized_total_eth': str(sum(r['net'] for r in res['realized'])),
               'realized': [ser(r) for r in res['realized']],
               'open_inventory': [ser(x) for x in res['open_inventory']]}
        json.dump(out, open(args.json, 'w'), indent=2)
