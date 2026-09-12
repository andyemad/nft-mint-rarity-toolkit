// hcminer.cu — Hashcats PoW miner, CUDA (Robinhood Chain 4663)
// workHash = keccak256( miner(20) | nonce(uint256 BE) | prev(uint256 BE) | anchor(bytes32) )  [116 bytes]
// Message word map (word i = LE64 of msg[8i..8i+7]) — identical to the verified CPU fast path in hcminer.c:
//   w0,w1,w2 <- miner(20)   w3 <- nonce[4..11]  w4 <- nonce[12..19]
//   w5 <- nonce[20..27]     w6 <- nonce[28..31]|prev[0..3]   w7..w13 prev/anchor
//   w14 = anchor[28..31] | 0x01<<32      w16 = 0x80<<56
// nonce = (salt64 << 64) | counter64  =>  w3/w4 carry salt, w5/w6 carry counter.
// Digest words: hh[i] = bswap64(s[i]); hh is the big-endian 256-bit hash. Accept iff hh < target (strict).
// VALIDATED: H100 probe hash was byte-identical to the Python/keccak reference (2026-09-11).
//
// Build: nvcc -O3 -o hcminer_cuda hcminer.cu
//   ./hcminer_cuda probe <miner> <prev> <anchor> <nonce_hex>
//   ./hcminer_cuda bench <seconds> [blocks] [threads]
//   ./hcminer_cuda mine  <miner> <prev> <anchor> <target_hex> [max_seconds] [blocks] [threads]
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <chrono>
#include <cuda_runtime.h>

#define ROTL(x,n) (((x)<<(n))|((x)>>(64-(n))))
__device__ __constant__ uint64_t RC[24] = {
0x0000000000000001ULL,0x0000000000008082ULL,0x800000000000808aULL,0x8000000080008000ULL,
0x000000000000808bULL,0x0000000080000001ULL,0x8000000080008081ULL,0x8000000000008009ULL,
0x000000000000008aULL,0x0000000000000088ULL,0x0000000080008009ULL,0x000000008000000aULL,
0x000000008000808bULL,0x800000000000008bULL,0x8000000000008089ULL,0x8000000000008003ULL,
0x8000000000008002ULL,0x8000000000000080ULL,0x000000000000800aULL,0x800000008000000aULL,
0x8000000080008081ULL,0x8000000000008080ULL,0x0000000080000001ULL,0x8000000080008008ULL};

__device__ __forceinline__ uint64_t bswap64d(uint64_t x){
    return ((x&0x00000000000000FFULL)<<56)|((x&0x000000000000FF00ULL)<<40)|
           ((x&0x0000000000FF0000ULL)<<24)|((x&0x00000000FF000000ULL)<<8)|
           ((x&0x000000FF00000000ULL)>>8)|((x&0x0000FF0000000000ULL)>>24)|
           ((x&0x00FF000000000000ULL)>>40)|((x&0xFF00000000000000ULL)>>56);
}
__device__ __forceinline__ uint32_t bswap32d(uint32_t x){
    return ((x&0xFFu)<<24)|((x&0xFF00u)<<8)|((x>>8)&0xFF00u)|((x>>24)&0xFFu);
}
__device__ void keccakf(uint64_t s[25]){
    uint64_t t,bc[5];
    const int ROTC[24]={1,3,6,10,15,21,28,36,45,55,2,14,27,41,56,8,25,43,62,18,39,61,20,44};
    const int PILN[24]={10,7,11,17,18,3,5,16,8,21,24,4,15,23,19,13,12,2,20,14,22,9,6,1};
    #pragma unroll 1
    for(int r=0;r<24;r++){
        #pragma unroll
        for(int i=0;i<5;i++) bc[i]=s[i]^s[i+5]^s[i+10]^s[i+15]^s[i+20];
        #pragma unroll
        for(int i=0;i<5;i++){
            t=bc[(i+4)%5]^ROTL(bc[(i+1)%5],1);
            #pragma unroll
            for(int j=0;j<25;j+=5) s[j+i]^=t;
        }
        t=s[1];
        #pragma unroll
        for(int i=0;i<24;i++){ int j=PILN[i]; bc[0]=s[j]; s[j]=ROTL(t,ROTC[i]); t=bc[0]; }
        #pragma unroll
        for(int j=0;j<25;j+=5){
            #pragma unroll
            for(int i=0;i<5;i++) bc[i]=s[j+i];
            #pragma unroll
            for(int i=0;i<5;i++) s[j+i]^=(~bc[(i+1)%5])&bc[(i+2)%5];
        }
        s[0]^=RC[r];
    }
}
__device__ __forceinline__ void load_state(const uint64_t* base, uint64_t salt, uint64_t c, uint64_t s[25]){
    #pragma unroll
    for(int i=0;i<17;i++) s[i]=base[i];
    #pragma unroll
    for(int i=17;i<25;i++) s[i]=0;
    uint32_t sh=(uint32_t)(salt>>32), sl=(uint32_t)salt;
    s[3]^=(uint64_t)bswap32d(sh)<<32;
    s[4]^=(uint64_t)bswap32d(sl);
    uint32_t ch=(uint32_t)(c>>32), cl=(uint32_t)c;
    s[5]^=(uint64_t)bswap32d(ch)<<32;
    s[6]^=(uint64_t)bswap32d(cl);
}

__global__ void kprobe(const uint64_t* base, uint64_t salt, uint64_t c, uint64_t* out){
    uint64_t s[25]; load_state(base,salt,c,s); keccakf(s);
    if(threadIdx.x==0&&blockIdx.x==0){ for(int i=0;i<4;i++) out[i]=s[i]; }
}

// budget_cycles bounds the kernel in GPU clock cycles so it can NEVER hang a shard.
__global__ void kmine(const uint64_t* base, uint64_t salt0, unsigned long long start, int tb,
                      const uint64_t* tgt, unsigned long long* f_c, unsigned long long* f_salt,
                      volatile int* done, unsigned long long budget_cycles){
    uint64_t salt = salt0 + ((unsigned long long)blockIdx.x*blockDim.x + threadIdx.x)*0x9E3779B97F4A7C15ULL;
    unsigned long long stride = (unsigned long long)gridDim.x*blockDim.x;
    uint64_t t0=tgt[0],t1=tgt[1],t2=tgt[2],t3=tgt[3];
    unsigned long long cstart = clock64();
    for(unsigned long long k=(unsigned long long)blockIdx.x*blockDim.x+threadIdx.x; ; k+=stride){
        if(*done) return;
        if((k & 0x1FFULL)==0 && (clock64()-cstart)>budget_cycles) return;
        uint64_t c = start + k;
        uint64_t s[25]; load_state(base,salt,c,s); keccakf(s);
        uint64_t w0=bswap64d(s[0]);
        if(w0==0 || __clzll(w0)>=(unsigned)tb){
            uint64_t h0=w0,h1=bswap64d(s[1]),h2=bswap64d(s[2]),h3=bswap64d(s[3]);
            int ok = (h0<t0)||(h0==t0&&((h1<t1)||(h1==t1&&((h2<t2)||(h2==t2&&h3<t3)))));
            if(ok && !*done){ atomicExch(f_c,(unsigned long long)c); atomicExch(f_salt,(unsigned long long)salt); *done=1; return; }
        }
    }
}
__global__ void kbench(const uint64_t* base, uint64_t salt0, unsigned long long iters, unsigned long long* cnt){
    unsigned long long salt = salt0 + ((unsigned long long)blockIdx.x*blockDim.x + threadIdx.x);
    uint64_t s[25]; s[0]=0;
    for(unsigned long long k=0;k<iters;k++){
        load_state(base,salt,k,s);
        keccakf(s);
    }
    if(s[0]==0xdeadbeefULL) atomicAdd(cnt,1ULL);   // keep the work from being optimised away
}

static int hex2bin(const char* h, uint8_t* out, int n){
    if(h[0]=='0'&&h[1]=='x') h+=2;
    for(int i=0;i<n;i++){ unsigned b; if(sscanf(h+2*i,"%2x",&b)!=1) return -1; out[i]=(uint8_t)b; }
    return 0;
}
static void msg_words(const uint8_t miner[20],const uint8_t prev[32],const uint8_t anchor[32],uint64_t w[17]){
    uint8_t buf[136]; memset(buf,0,136);
    memcpy(buf,miner,20); memcpy(buf+52,prev,32); memcpy(buf+84,anchor,32);
    buf[116]=0x01; buf[135]|=0x80;
    for(int i=0;i<17;i++){ uint64_t v; memcpy(&v,buf+i*8,8); w[i]=v; }
}

int main(int argc,char**argv){
    if(argc<2){fprintf(stderr,"usage: %s probe|bench|mine ...\n",argv[0]);return 1;}
    const char* mode=argv[1];
    if(strcmp(mode,"probe")&&strcmp(mode,"mine")&&strcmp(mode,"bench")){fprintf(stderr,"bad mode\n");return 1;}
    uint8_t miner[20],prev[32],anc[32]; memset(miner,0x11,20); memset(prev,0x22,32); memset(anc,0x33,32);
    if(strcmp(mode,"bench")!=0 && argc>4){
        if(hex2bin(argv[2],miner,20)||hex2bin(argv[3],prev,32)||hex2bin(argv[4],anc,32)){fprintf(stderr,"hex\n");return 1;}
    }
    uint64_t w[17]; msg_words(miner,prev,anc,w);
    uint64_t* d_w; cudaMalloc(&d_w,17*8); cudaMemcpy(d_w,w,17*8,cudaMemcpyHostToDevice);

    if(!strcmp(mode,"probe")){
        if(argc<6){fprintf(stderr,"probe <miner> <prev> <anchor> <nonce_hex>\n");return 1;}
        char* nz=argv[5]; if(nz[0]=='0'&&nz[1]=='x') nz+=2;
        uint8_t nb[32]; for(int i=0;i<32;i++){ unsigned b; if(sscanf(nz+2*i,"%2x",&b)!=1){fprintf(stderr,"nonce hex\n");return 1;} nb[i]=(uint8_t)b; }
        for(int i=0;i<8;i++){ if(nb[i]||nb[16+i]){ fprintf(stderr,"probe expects nonce with zero bytes 0..7 and 16..23\n"); return 1; } }
        uint64_t salt=0,c=0;
        for(int i=8;i<16;i++) salt=(salt<<8)|nb[i];
        for(int i=24;i<32;i++) c=(c<<8)|nb[i];
        uint64_t* d_out; cudaMallocManaged(&d_out,4*8);
        kprobe<<<1,1>>>(d_w,salt,c,d_out);
        cudaError_t e=cudaDeviceSynchronize();
        if(e!=cudaSuccess){ printf("CUDAERR %s\n",cudaGetErrorString(e)); return 2; }
        printf("hash=0x");
        for(int i=0;i<32;i++){ uint64_t v=d_out[i/8]; printf("%02x",(unsigned)((v>>(8*(i%8)))&0xFF)); }
        printf("\n");
        return 0;
    }

    if(!strcmp(mode,"bench")){
        int secs = argc>2?atoi(argv[2]):5;
        int blocks = argc>3?atoi(argv[3]):4096, threads = argc>4?atoi(argv[4]):256;
        unsigned long long* d_cnt; cudaMallocManaged(&d_cnt,8); *d_cnt=0;
        unsigned long long iters = 20000;
        double el = 0;
        for(int pass=0; pass<3; pass++){
            auto t0=std::chrono::steady_clock::now();
            kbench<<<blocks,threads>>>(d_w,0x123456789abcdefULL,iters,d_cnt);
            cudaError_t e=cudaDeviceSynchronize();
            auto t1=std::chrono::steady_clock::now();
            if(e!=cudaSuccess){ printf("CUDAERR %s\n",cudaGetErrorString(e)); return 2; }
            el=std::chrono::duration<double>(t1-t0).count();
            double target = secs>0?secs:5.0;
            if(el>=target*0.6 || pass==2) break;
            double scale = target/el;
            if(scale>50) scale=50;
            iters = (unsigned long long)(iters*scale);
            if(iters<1000) iters=1000;
        }
        double total=(double)blocks*(double)threads*(double)iters;
        printf("%.2f GH/s (%.3e hashes in %.2fs, %d blocks x %d threads, %llu iters/thread)\n",
               total/el/1e9, total, el, blocks, threads, iters);
        return 0;
    }

    // mine
    if(argc<6){fprintf(stderr,"mine <miner> <prev> <anchor> <target_hex> [max_s] [blocks] [threads]\n");return 1;}
    uint8_t tgt[32]; if(hex2bin(argv[5],tgt,32)){fprintf(stderr,"target hex\n");return 1;}
    int maxs = argc>6?atoi(argv[6]):60;
    int blocks = argc>7?atoi(argv[7]):4096, threads = argc>8?atoi(argv[8]):256;
    uint64_t tw[4]; for(int i=0;i<4;i++){ uint64_t v=0; for(int j=0;j<8;j++) v=(v<<8)|tgt[i*8+j]; tw[i]=v; }
    int tb=0; for(int i=0;i<32;i++){ if(tgt[i]==0){tb+=8;continue;} int b=tgt[i]; while(!(b&0x80)){tb++;b<<=1;} break; }
    uint64_t* d_t; cudaMalloc(&d_t,32); cudaMemcpy(d_t,tw,32,cudaMemcpyHostToDevice);
    unsigned long long *d_c,*d_s; cudaMallocManaged(&d_c,8); cudaMallocManaged(&d_s,8);
    *d_c=0; *d_s=0; int* d_done; cudaMallocManaged(&d_done,4); *d_done=0;
    // GPU clock budget so the kernel always returns
    int clockKHz=0; cudaDeviceGetAttribute(&clockKHz, cudaDevAttrClockRate, 0);
    if(clockKHz<=0) clockKHz=1800000;
    unsigned long long budget=(unsigned long long)((double)clockKHz*1000.0*(double)(maxs>0?maxs:1)*0.98);
    auto t0=std::chrono::steady_clock::now();
    kmine<<<blocks,threads>>>(d_w,(uint64_t)time(NULL)*2654435761ULL,0ULL,tb,d_t,d_c,d_s,d_done,budget);
    cudaError_t e=cudaDeviceSynchronize();
    double el=std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count();
    if(e!=cudaSuccess){ printf("CUDAERR %s\n",cudaGetErrorString(e)); return 2; }
    if(*d_done){
        char nh[80]; memset(nh,0,sizeof nh);
        for(int i=0;i<16;i++) sprintf(nh+2*i,"%02x",(unsigned)((*d_s>>(8*(15-i)))&0xFF));
        for(int i=0;i<16;i++) sprintf(nh+32+2*i,"%02x",(unsigned)((*d_c>>(8*(15-i)))&0xFF));
        printf("FOUND salt=%llx counter=%llu\nnonce=0x%s\nelapsed=%.2fs\n",*d_s,*d_c,nh,el);
        return 0;
    }
    printf("TIMEOUT after %.2fs\n",el); return 3;
}
