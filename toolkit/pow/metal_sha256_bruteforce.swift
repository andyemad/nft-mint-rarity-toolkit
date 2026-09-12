// Metal SHA-256 brute-forcer — VERIFIED CORRECT (hashes "abc" to ba7816bf...).
// Copy and modify: change the two target prefixes (t1/t2) and the wordlist path.
//
// Usage:
//   swiftc -O metal_sha256_bruteforce.swift -o huntmetal
//   ./huntmetal corpus/v3/public/wordlist.json
//
// What it does: brute-forces a 3-word SHA-256 "hunt" (words from a wordlist, space-separated,
// may repeat) by dispatching one GPU thread per (i,j) pair, each looping the third word.
// It checks TWO target prefixes at once and reports any match.
//
// Gotchas already solved here:
//   - Metal uses [[thread_position_in_grid]], NOT get_global_id() (that's OpenCL).
//   - Thread-local arrays passed to an inline fn need the `thread` address space.
//   - setbuf(stdout, nil) — otherwise buffered stdout makes long GPU runs look hung.
//   - It self-tests "abc" before the real run and aborts on mismatch.

import Metal
import Foundation

let shaderSource = """
#include <metal_stdlib>
using namespace metal;

constant uint K[64] = {
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};

inline uint rotr(uint x, uint n){ return (x >> n) | (x << (32-n)); }

inline void sha256_block_words(const thread uchar* blk, thread uint& H0, thread uint& H1){
    uint w[64];
    for(uint t=0;t<16;t++){
        uint b=t*4;
        w[t] = ((uint)blk[b]<<24)|((uint)blk[b+1]<<16)|((uint)blk[b+2]<<8)|(uint)blk[b+3];
    }
    for(uint t=16;t<64;t++){
        uint s0 = rotr(w[t-15],7)^rotr(w[t-15],18)^(w[t-15]>>3);
        uint s1 = rotr(w[t-2],17)^rotr(w[t-2],19)^(w[t-2]>>10);
        w[t] = w[t-16]+s0+w[t-7]+s1;
    }
    uint a=0x6a09e667,b=0xbb67ae85,c=0x3c6ef372,d=0xa54ff53a,
         e=0x510e527f,f=0x9b05688c,g=0x1f83d9ab,h=0x5be0cd19;
    for(uint t=0;t<64;t++){
        uint S1 = rotr(e,6)^rotr(e,11)^rotr(e,25);
        uint ch = (e&f)^((~e)&g);
        uint t1 = h+S1+ch+K[t]+w[t];
        uint S0 = rotr(a,2)^rotr(a,13)^rotr(a,22);
        uint maj = (a&b)^(a&c)^(b&c);
        uint t2 = S0+maj;
        h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    }
    H0 = 0x6a09e667+a;
    H1 = 0xbb67ae85+b;
}

kernel void hunt3(
    uint gid [[thread_position_in_grid]],
    device const uchar* wb,
    device const uint*  woff,
    device const uint*  wlen,
    device atomic_uint* count,
    device uint* result,
    constant uint& nw,
    constant uint& t1_hi, constant uint& t1_lo,
    constant uint& t2_hi, constant uint& t2_lo
){
    uint total = nw*nw;
    if(gid >= total) return;
    uint i = gid/nw;
    uint j = gid%nw;

    uchar pre[64];
    uint prelen=0;
    uint li=wlen[i], lj=wlen[j];
    for(uint x=0;x<li;x++) pre[prelen++] = wb[woff[i]+x];
    pre[prelen++] = (uchar)' ';
    for(uint x=0;x<lj;x++) pre[prelen++] = wb[woff[j]+x];
    pre[prelen++] = (uchar)' ';

    for(uint k=0;k<nw;k++){
        uint lk=wlen[k];
        uint len=prelen+lk;
        uchar blk[64];
        for(uint x=0;x<64;x++) blk[x]=0;
        for(uint x=0;x<prelen;x++) blk[x]=pre[x];
        for(uint x=0;x<lk;x++) blk[prelen+x]=wb[woff[k]+x];
        blk[len]=0x80;
        ulong bits=(ulong)len*8;
        for(uint x=0;x<8;x++) blk[63-x]=(uchar)((bits>>(x*8))&0xff);
        uint H0,H1;
        sha256_block_words(blk,H0,H1);
        uint b0=(H0>>24)&0xff, b1=(H0>>16)&0xff, b2=(H0>>8)&0xff, b3=H0&0xff;
        uint b4=(H1>>24)&0xff, b5=(H1>>16)&0xff, b6=(H1>>8)&0xff;
        bool m1 = (b0==((t1_hi>>24)&0xff)) && (b1==((t1_hi>>16)&0xff)) && (b2==((t1_hi>>8)&0xff)) && (b3==(t1_hi&0xff)) && (b4==((t1_lo>>16)&0xff)) && (b5==((t1_lo>>8)&0xff)) && (b6==(t1_lo&0xff));
        bool m2 = (b0==((t2_hi>>24)&0xff)) && (b1==((t2_hi>>16)&0xff)) && (b2==((t2_hi>>8)&0xff)) && (b3==(t2_hi&0xff)) && (b4==((t2_lo>>16)&0xff)) && (b5==((t2_lo>>8)&0xff)) && (b6==(t2_lo&0xff));
        if(m1 || m2){
            uint r = atomic_fetch_add_explicit(count, 1, memory_order_relaxed);
            if(r < 64){ result[r*4]=i; result[r*4+1]=j; result[r*4+2]=k; result[r*4+3]= m1?1u:2u; }
        }
    }
}

kernel void test_hash(device const uchar* input, constant uint& len, device uint* out){
    uchar blk[64];
    for(uint x=0;x<64;x++) blk[x]=0;
    for(uint x=0;x<len;x++) blk[x]=input[x];
    blk[len]=0x80;
    ulong bits=(ulong)len*8;
    for(uint x=0;x<8;x++) blk[63-x]=(uchar)((bits>>(x*8))&0xff);
    uint w[64];
    for(uint t=0;t<16;t++){ uint b=t*4; w[t]=((uint)blk[b]<<24)|((uint)blk[b+1]<<16)|((uint)blk[b+2]<<8)|(uint)blk[b+3]; }
    for(uint t=16;t<64;t++){ uint s0=rotr(w[t-15],7)^rotr(w[t-15],18)^(w[t-15]>>3); uint s1=rotr(w[t-2],17)^rotr(w[t-2],19)^(w[t-2]>>10); w[t]=w[t-16]+s0+w[t-7]+s1; }
    uint a=0x6a09e667,b=0xbb67ae85,c=0x3c6ef372,d=0xa54ff53a,e=0x510e527f,f=0x9b05688c,g=0x1f83d9ab,h=0x5be0cd19;
    for(uint t=0;t<64;t++){ uint S1=rotr(e,6)^rotr(e,11)^rotr(e,25); uint ch=(e&f)^((~e)&g); uint t1=h+S1+ch+K[t]+w[t]; uint S0=rotr(a,2)^rotr(a,13)^rotr(a,22); uint maj=(a&b)^(a&c)^(b&c); uint t2=S0+maj; h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2; }
    out[0]=0x6a09e667+a; out[1]=0xbb67ae85+b; out[2]=0x3c6ef372+c; out[3]=0xa54ff53a+d;
    out[4]=0x510e527f+e; out[5]=0x9b05688c+f; out[6]=0x1f83d9ab+g; out[7]=0x5be0cd19+h;
}
"""

func main() {
    setbuf(stdout, nil)
    let device = MTLCreateSystemDefaultDevice()!
    let lib = try! device.makeLibrary(source: shaderSource, options: nil)

    // correctness test: "abc" -> ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
    do {
        let fn = lib.makeFunction(name: "test_hash")!
        let pipe = try! device.makeComputePipelineState(function: fn)
        let q = device.makeCommandQueue()!
        let abc = Array("abc".utf8)
        let inBuf = device.makeBuffer(bytes: abc, length: abc.count, options: .storageModeShared)!
        let lenBuf = device.makeBuffer(bytes: [UInt32(abc.count)], length: 4, options: .storageModeShared)!
        let outBuf = device.makeBuffer(length: 32, options: .storageModeShared)!
        let cmd = q.makeCommandBuffer()!
        let enc = cmd.makeComputeCommandEncoder()!
        enc.setComputePipelineState(pipe)
        enc.setBuffer(inBuf, offset: 0, index: 0)
        enc.setBuffer(lenBuf, offset: 0, index: 1)
        enc.setBuffer(outBuf, offset: 0, index: 2)
        enc.dispatchThreads(MTLSize(width: 1, height: 1, depth: 1), threadsPerThreadgroup: MTLSize(width: 1, height: 1, depth: 1))
        enc.endEncoding()
        cmd.commit(); cmd.waitUntilCompleted()
        let words = outBuf.contents().assumingMemoryBound(to: UInt32.self)
        var hex = ""
        for i in 0..<8 { hex += String(format: "%08x", words[i]) }
        let expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        print("test abc: \(hex)")
        print(hex == expected ? "✓ SHA256 CORRECT" : "✗ MISMATCH — aborting")
        if hex != expected { exit(1) }
    }

    let path = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "corpus/v3/public/wordlist.json"
    let text = try! String(contentsOfFile: path, encoding: .utf8)
    var words: [String] = []
    let re = try! NSRegularExpression(pattern: #""([a-z]+)""#)
    let range = NSRange(text.startIndex..<text.endIndex, in: text)
    for m in re.matches(in: text, range: range) {
        if let r = Range(m.range(at: 1), in: text) { words.append(String(text[r])) }
    }
    print("loaded \(words.count) words")

    var wordBytes: [UInt8] = []
    var woff: [UInt32] = []
    var wlen: [UInt32] = []
    for w in words {
        woff.append(UInt32(wordBytes.count))
        wlen.append(UInt32(w.utf8.count))
        wordBytes.append(contentsOf: w.utf8)
    }
    let nw = UInt32(words.count)

    // TARGETS — change these to your hunt prefixes. First 4 bytes = t_hi, next 3 bytes top-aligned = t_lo.
    let t1_hi: UInt32 = 0xab042744   // prefix ab042744bd2c7b
    let t1_lo: UInt32 = 0xbd2c7b00
    let t2_hi: UInt32 = 0x59cac89c   // prefix 59cac89c1f4f88
    let t2_lo: UInt32 = 0x1f4f8800

    let fn = lib.makeFunction(name: "hunt3")!
    let pipe = try! device.makeComputePipelineState(function: fn)
    let q = device.makeCommandQueue()!

    let wbBuf = device.makeBuffer(bytes: wordBytes, length: wordBytes.count, options: .storageModeShared)!
    let woffBuf = device.makeBuffer(bytes: woff, length: woff.count*4, options: .storageModeShared)!
    let wlenBuf = device.makeBuffer(bytes: wlen, length: wlen.count*4, options: .storageModeShared)!
    let countBuf = device.makeBuffer(length: 4, options: .storageModeShared)!
    let resBuf = device.makeBuffer(length: 64*4*4, options: .storageModeShared)!

    var nwVal = nw
    let nwBuf = device.makeBuffer(bytes: &nwVal, length: 4, options: .storageModeShared)!
    var t1h = t1_hi, t1l = t1_lo, t2h = t2_hi, t2l = t2_lo
    let t1hBuf = device.makeBuffer(bytes: &t1h, length: 4, options: .storageModeShared)!
    let t1lBuf = device.makeBuffer(bytes: &t1l, length: 4, options: .storageModeShared)!
    let t2hBuf = device.makeBuffer(bytes: &t2h, length: 4, options: .storageModeShared)!
    let t2lBuf = device.makeBuffer(bytes: &t2l, length: 4, options: .storageModeShared)!

    let total = Int(nw)*Int(nw)
    let start = Date()
    let cmd = q.makeCommandBuffer()!
    let enc = cmd.makeComputeCommandEncoder()!
    enc.setComputePipelineState(pipe)
    enc.setBuffer(wbBuf, offset: 0, index: 0)
    enc.setBuffer(woffBuf, offset: 0, index: 1)
    enc.setBuffer(wlenBuf, offset: 0, index: 2)
    enc.setBuffer(countBuf, offset: 0, index: 3)
    enc.setBuffer(resBuf, offset: 0, index: 4)
    enc.setBuffer(nwBuf, offset: 0, index: 5)
    enc.setBuffer(t1hBuf, offset: 0, index: 6)
    enc.setBuffer(t1lBuf, offset: 0, index: 7)
    enc.setBuffer(t2hBuf, offset: 0, index: 8)
    enc.setBuffer(t2lBuf, offset: 0, index: 9)
    enc.dispatchThreads(MTLSize(width: total, height: 1, depth: 1), threadsPerThreadgroup: MTLSize(width: 256, height: 1, depth: 1))
    enc.endEncoding()
    cmd.commit(); cmd.waitUntilCompleted()
    let elapsed = Date().timeIntervalSince(start)

    let cnt = countBuf.contents().load(as: UInt32.self)
    let res = resBuf.contents().assumingMemoryBound(to: UInt32.self)
    let space = Double(total) * Double(nw)
    print(String(format: "done in %.1fs; matches=%d; rate=%.1f M/s", elapsed, cnt, space/elapsed/1e6))
    if cnt > 0 {
        for r in 0..<min(Int(cnt), 64) {
            let i = Int(res[r*4]), j = Int(res[r*4+1]), k = Int(res[r*4+2]), which = res[r*4+3]
            print("MATCH \(which==1 ? "T1" : "T2"): \(words[i]) \(words[j]) \(words[k])")
        }
    }
}

main()
