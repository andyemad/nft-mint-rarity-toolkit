#!/usr/bin/env python3
"""
seadrop_fire.py — Rapid RH-chain SeaDrop public-mint fire tool (Dunlap config).

Flow for a live drop:
  1) recon <collection>        -> is it open? price/cap/window/fee recipient
  2) wallet <collection> N     -> prints N FRESH wallet addresses + exact fund amount
                                  (user funds; script never holds prior keys)
  3) check-funded <collection> --wallets a,b -> polls ETH balances until funded
  4) fire <collection> --keyfile K --quantity Q   -> eth_call dry-run, then broadcast
  5) verify <collection> <address>

Defaults (Dunlap postmortem / RH SeaDrop):
  SeaDrop singleton: 0x00005ea00ac477b1030ce78506496e8c2de24bf5
  mintPublic(address nftContract, address feeRecipient, address minterIfNotPayer, uint256 quantity)
  selector 0x161ac21f | gas 180000 | maxFeePerGas 0.5 gwei | maxPriorityFee 0
  One prepared tx per fresh wallet, broadcast in parallel.

RPC: https://rpc.mainnet.chain.robinhood.com (rate-limits: every call retried w/ backoff).
Only eth_account needed (no web3). Key files: raw hex private keys chmod 600 in
~/.hermes/secrets/ (see ethereum-wallet-operations conventions).
"""
import json, os, sys, time, datetime, urllib.request, secrets

RPC = 'https://rpc.mainnet.chain.robinhood.com'
SEADROP = '0x00005ea00ac477b1030ce78506496e8c2de24bf5'
GAS_LIMIT = 180000
MAX_FEE_GWEI = 0.5
MAX_PRIORITY_GWEI = 0.0
GAS_BUFFER_ETH = 0.00014          # covers ~120k gas at 0.5 gwei + slack
EXTRA_MARGIN_ETH = 0.0001         # safety on top of price*qty+gas
KEYS_DIR = os.path.expanduser('~/.hermes/secrets')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0'

# --- json-rpc ---------------------------------------------------------------
def rpc(method, params, tries=6, wait=2.0):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(RPC, data=body,
                                         headers={'Content-Type': 'application/json', 'User-Agent': UA})
            d = json.loads(urllib.request.urlopen(req, timeout=20).read())
            if 'error' in d:
                last = d['error']
                if '429' in str(d['error']) or 'limit' in str(d['error']).lower():
                    time.sleep(wait * (i + 1)); continue
                return {'error': d['error']}
            return d.get('result')
        except Exception as e:
            last = str(e)
            time.sleep(wait * (i + 1))
    return {'error': last}

def call(to, data):
    r = rpc('eth_call', [{'to': to, 'data': data}, 'latest'])
    return r

def bal_eth(addr):
    r = rpc('eth_getBalance', [addr, 'latest'])
    return int(r, 16) / 1e18 if isinstance(r, str) else 0.0

def send_raw(raw_hex):
    return rpc('eth_sendRawTransaction', [raw_hex])

def get_receipt(txhash, tries=20, wait=2.0):
    for i in range(tries):
        r = rpc('eth_getTransactionReceipt', [txhash])
        if isinstance(r, dict) and r.get('blockHash'):
            return r
        time.sleep(wait)
    return None

# --- selectors / decoding ----------------------------------------------------
def sel(sig):  # 4-byte selector
    from eth_hash.auto import keccak
    return '0x' + keccak(sig.encode()).hex()[:8]

SEL_TOTAL = '0x18160ddd'
SEL_MAX = '0xd5abeb01'
SEL_NAME = '0x06fdde03'
SEL_SYMBOL = '0x95d89b41'
SEL_BAL = '0x70a08231'  # balanceOf(address)
SEL_GETPUBLICDROP = sel('getPublicDrop(address)')
SEL_ALLOWED_FEES = sel('getAllowedFeeRecipients(address)')
SEL_MINT = sel('mintPublic(address,address,address,uint256)')

def u256(hexstr):
    return int(hexstr, 16)

def pad(addr):
    return addr.lower().replace('0x', '').rjust(64, '0')

def decode_public_drop(h):
    h = h[2:]
    w = [int(h[i:i + 64], 16) for i in range(0, len(h), 64)] if h else []
    return w

def decode_addresses(h):
    """ABI-decode a dynamic address[] return: offset, length, then N padded words."""
    h = h[2:] if h.startswith('0x') else h
    if len(h) < 128 or int(h[0:64], 16) == 0:
        return []
    length = int(h[64:128], 16)
    out = []
    for i in range(length):
        chunk = h[128 + i * 64:128 + (i + 1) * 64]
        if len(chunk) == 64 and int(chunk, 16) != 0:
            out.append('0x' + chunk[-40:].lower())
    return out

def decode_string(h):
    """ABI-decode a dynamic string return: offset word, length word, then UTF-8 bytes."""
    h = h[2:] if h.startswith('0x') else h
    try:
        if len(h) < 128:
            return '?'
        length = int(h[64:128], 16)
        if length > 0 and length * 2 <= len(h) - 128:
            raw = bytes.fromhex(h[128:128 + length * 2])
            return raw.decode('utf-8', 'replace')
    except Exception:
        pass
    return '?'

# --- contract reads ------------------------------------------------------------
def token_meta(ca):
    name_h = call(ca, SEL_NAME)
    sym_h = call(ca, SEL_SYMBOL)
    def clean(h):
        s = decode_string(h) if isinstance(h, str) else '?'
        return s
    return clean(name_h), clean(sym_h)

def recon(ca, seadrop=SEADROP):
    ts = call(ca, SEL_TOTAL); ms = call(ca, SEL_MAX)
    total = u256(ts) if isinstance(ts, str) else None
    maxs = u256(ms) if isinstance(ms, str) else None
    nm, sym = token_meta(ca)
    info = {'collection': ca, 'name': nm, 'symbol': sym, 'totalSupply': total, 'maxSupply': maxs}
    if total is not None and maxs is not None:
        info['soldOut'] = total >= maxs
    pd = call(seadrop, SEL_GETPUBLICDROP + pad(ca))
    if isinstance(pd, str) and len(pd) > 2:
        w = decode_public_drop(pd)
        if len(w) >= 6:
            price = w[0] / 1e18
            info.update({
                'mintPriceEth': price,
                'startTime': w[1], 'endTime': w[2],
                'capPerWallet': w[3],
                'feeBps': w[4],
                'restrictFeeRecipients': bool(w[5]),
                'nowUtc': int(time.time()),
                'open': w[1] <= int(time.time()) < w[2] and (total is None or total < maxs),
            })
    fees = call(seadrop, SEL_ALLOWED_FEES + pad(ca))
    if isinstance(fees, str):
        info['allowedFeeRecipients'] = decode_addresses(fees)
    return info

def fmt_dt(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime('%H:%M:%S UTC') if ts else '?'

# --- fresh wallet ---------------------------------------------------------------
def fresh_wallet(tag='mint'):
    from eth_account import Account
    acct = Account.create(os.urandom(32))
    n = 0
    while True:
        n += 1
        keypath = f'{KEYS_DIR}/seadrop_{tag}_{n}_key'
        if not os.path.exists(keypath):
            break
    with open(keypath, 'w') as f:
        f.write(acct.key.hex() + '\n')
    os.chmod(keypath, 0o600)
    return {'address': acct.address, 'keyfile': keypath}

# --- main -----------------------------------------------------------------------
def cmd_recon(argv):
    ca = argv[0].lower()
    info = recon(ca, argv[1].lower() if len(argv) > 1 else SEADROP)
    print(json.dumps(info, indent=2))
    if info.get('open'):
        print('\nOPEN — ready to mint.')
    else:
        why = []
        if info.get('soldOut'): why.append('SOLD OUT')
        if info.get('startTime') and info.get('nowUtc') and info['nowUtc'] < info['startTime']:
            why.append(f'starts {fmt_dt(info["startTime"])}')
        if info.get('endTime') and info.get('nowUtc') and info['nowUtc'] >= info['endTime']:
            why.append(f'ended {fmt_dt(info["endTime"])}')
        print('\nNOT mintable:', '; '.join(why) if why else 'unknown reason')

def cmd_wallet(argv):
    ca = argv[0].lower()
    count = int(argv[1]) if len(argv) > 1 else 1
    seadrop = argv[2].lower() if len(argv) > 2 else SEADROP
    info = recon(ca, seadrop)
    price = info.get('mintPriceEth') or 0.0
    cap = info.get('capPerWallet') or 1
    # funding per wallet: price*cap + gas + margin
    per = price * cap + GAS_BUFFER_ETH + EXTRA_MARGIN_ETH
    print(f'{info.get("name")} ({info.get("symbol")}) | price {price} | cap {cap}/wallet')
    print(f'fund per wallet: {per:.6f} ETH (price*qty {price*cap:.6f} + gas/margin {GAS_BUFFER_ETH+EXTRA_MARGIN_ETH:.5f})')
    out = []
    for i in range(count):
        w = fresh_wallet(info.get('symbol') or 'mint')
        out.append({'address': w['address'], 'keyfile': w['keyfile'], 'fundEth': round(per, 6)})
        print(f'  FRESH WALLET #{i+1}: {w["address"]}  key={w["keyfile"]}  fund {per:.6f} ETH')
    with open(f'{KEYS_DIR}/seadrop_last.json', 'w') as f:
        json.dump({'collection': ca, 'seadrop': seadrop, 'priceEth': price, 'cap': cap,
                   'fundPerWalletEth': round(per, 6), 'wallets': out}, f, indent=2)
    print(f'\nFund the address(es), then run: check-funded {ca} --wallets <addr1,addr2>')

def cmd_check(argv):
    ca = argv[0].lower()
    addrs = [a.lower() for a in argv[1].split(',')]
    missing = []
    for a in addrs:
        b = bal_eth(a)
        print(f'{a[:14]} ETH balance: {b:.6f}')
        # need price*qty + gas; compare to stored or just > 0.004
        need = 0.004
        try:
            d = json.load(open(f'{KEYS_DIR}/seadrop_last.json'))
            for w in d.get('wallets', []):
                if w['address'].lower() == a:
                    need = w['fundEth']
        except Exception:
            pass
        if b < need:
            missing.append((a, need))
    if missing:
        print('\nNOT FUNDED YET — awaiting:', ', '.join(a[:10] for a, _ in missing))
    else:
        print('\nFUNDED — ready to fire.')

def cmd_fire(argv):
    from eth_account import Account
    ca = argv[0].lower()
    keyfile = argv[1]
    qty = int(argv[2]) if len(argv) > 2 else None
    seadrop = argv[3].lower() if len(argv) > 3 else SEADROP
    info = recon(ca, seadrop)
    if not info.get('open'):
        print('REFUSING: collection not open —', json.dumps(info)); return 1
    price = info['mintPriceEth']; cap = info['capPerWallet']
    if qty is None or qty < 1: qty = cap
    if qty > cap:
        print(f'qty {qty} > cap {cap}/wallet — refusing (use more wallets)'); return 1
    fees = info.get('allowedFeeRecipients') or []
    fee_rec = fees[0] if fees else '0x0000000000000000000000000000000000000000'
    key = open(keyfile).read().strip()
    try:
        key = json.loads(key).get('key') or json.loads(key).get('private_key') or key
    except Exception:
        pass
    acct = Account.from_key(key)
    sender = acct.address
    # dry run
    data = SEL_MINT + pad(ca) + pad(fee_rec) + pad(sender) + hex(qty)[2:].rjust(64, '0')
    dr = call(seadrop, data)
    if not isinstance(dr, str):
        print('DRY-RUN FAILED (would revert):', dr); return 1
    # nonce, gas, fees
    nonce_r = rpc('eth_getTransactionCount', [sender, 'latest'])
    nonce = int(nonce_r, 16) if isinstance(nonce_r, str) else 0
    fee = int(MAX_FEE_GWEI * 1e9)
    tip = int(MAX_PRIORITY_GWEI * 1e9)
    value = int(price * qty * 1e18)
    tx = {'from': sender, 'to': seadrop, 'data': data, 'nonce': nonce,
          'gas': GAS_LIMIT, 'maxFeePerGas': fee, 'maxPriorityFeePerGas': tip, 'value': value}
    signed = acct.sign_transaction(tx)
    print(f'DRY-RUN OK | sender {sender} | qty {qty} | value {price*qty:.6f} ETH | feeRecipient {fee_rec}')
    print('SENDING...')
    res = send_raw(signed.raw_transaction.hex())
    if isinstance(res, str):
        print('TX:', res)
        rc = get_receipt(res)
        if rc:
            ok = rc.get('status') == '0x1'
            print('RECEIPT status', rc.get('status'), 'gasUsed', int(rc.get('gasUsed', '0x0'), 16))
            b = call(ca, SEL_BAL + pad(sender))
            print('wallet balanceOf:', int(b, 16) if isinstance(b, str) else 'ERR')
            return 0 if ok else 2
        print('receipt pending...'); return 0
    print('SEND FAILED:', res); return 1

def cmd_verify(argv):
    ca = argv[0].lower()
    addr = argv[1].lower()
    b = call(ca, SEL_BAL + pad(addr))
    print('balanceOf:', int(b, 16) if isinstance(b, str) else b)

def main():
    if len(sys.argv) < 3:
        print(__doc__); return 1
    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == 'recon': return cmd_recon(args)
    if cmd == 'wallet': return cmd_wallet(args)
    if cmd == 'check-funded': return cmd_check(args)
    if cmd == 'fire': return cmd_fire(args)
    if cmd == 'verify': return cmd_verify(args)
    print(__doc__); return 1

if __name__ == '__main__':
    sys.exit(main())
