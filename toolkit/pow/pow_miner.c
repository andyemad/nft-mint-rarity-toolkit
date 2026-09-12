// pow_miner.c — FAB-4200-style PoW nonce hunter (VERIFIED 2026-08-21)
//
// workHash = keccak256( chainid_u32_be || contract_20 || minter_20 || nonce_u256_be )
// Finds nonce with >= target leading zero bits. OpenMP multithreaded.
//
// Build:   gcc -O3 -fopenmp -o fabminer fabminer.c
//          (NOT -march=native on Modal: image-build host != exec host -> SIGILL, rc=-4)
// Usage:   ./fabminer <minter_hex> <start_nonce> <target_bits> [threads]
// Output:  FOUND nonce=N bits=B hash=0x… / calldata=0xa0712d68%016x
//
// SELF-CHECK BEFORE LONG RUNS (mandatory):
//   1. Run at target=24 (finds in seconds).
//   2. Recompute in Python with exact contract byte layout:
//        from Crypto.Hash import keccak
//        pre = (4663).to_bytes(32,'big') + contract_20 + minter_20 + nonce.to_bytes(32,'big')
//        keccak.new(digest_bits=256, data=pre).hexdigest()  -- must equal C hash
//   Empty-string keccak sanity: c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470
//
// BUGS THIS CODE PREVIOUSLY HAD (do not reintroduce):
//   - nonce written at bytes 88..95 instead of 96..103 (uint256 BE low word).
//     Bytes 72..95 of the preimage must stay ZERO for nonce < 2^64.
//   - RC round constants hand-retyped with shuffled entries -> plausible-but-wrong hashes.
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <omp.h>

#define ROTL(x,n) (((x)<<(n))|((x)>>(64-(n))))
static const uint64_t RC[24]={
0x0000000000000001ULL,0x0000000000008082ULL,0x800000000000808aULL,0x8000000080008000ULL,
0x000000000000808bULL,0x0000000080000001ULL,0x8000000080008081ULL,0x8000000000008009ULL,
0x000000000000008aULL,0x0000000000000088ULL,0x0000000080008009ULL,0x000000008000000aULL,
0x000000008000808bULL,0x800000000000008bULL,0x8000000000008089ULL,0x8000000000008003ULL,
0x8000000000008002ULL,0x8000000000000080ULL,0x000000000000800aULL,0x800000008000000aULL,
0x8000000080008081ULL,0x8000000000008080ULL,0x0000000080000001ULL,0x8000000080008008ULL};
static const int ROTC[24]={1,3,6,10,15,21,28,36,45,55,2,14,27,41,56,8,25,43,62,18,39,61,20,44};
static const int PILN[24]={10,7,11,17,18,3,5,16,8,21,24,4,15,23,19,13,12,2,20,14,22,9,6,1};

static void keccakf(uint64_t s[25]){
    uint64_t t,bc[5];
    for(int r=0;r<24;r++){
        for(int i=0;i<5;i++) bc[i]=s[i]^s[i+5]^s[i+10]^s[i+15]^s[i+20];
        for(int i=0;i<5;i++){
            t=bc[(i+4)%5]^ROTL(bc[(i+1)%5],1);
            for(int j=0;j<25;j+=5) s[j+i]^=t;
        }
        t=s[1];
        for(int i=0;i<24;i++){
            int j=PILN[i]; bc[0]=s[j]; s[j]=ROTL(t,ROTC[i]); t=bc[0];
        }
        for(int j=0;j<25;j+=5){
            for(int i=0;i<5;i++) bc[i]=s[j+i];
            for(int i=0;i<5;i++) s[j+i]^=(~bc[(i+1)%5])&bc[(i+2)%5];
        }
        s[0]^=RC[r];
    }
}

static inline void keccak104(const uint8_t in[104], uint8_t out[32], uint64_t s_scratch[25]){
    memset(s_scratch,0,25*8);
    uint8_t buf[136];
    memcpy(buf,in,104);
    memset(buf+104,0,32);
    buf[104]=0x01;           // keccak padding (NOT sha3's 0x06)
    buf[135]|=0x80;
    for(int i=0;i<17;i++){ uint64_t v; memcpy(&v,buf+i*8,8); s_scratch[i]^=v; }
    keccakf(s_scratch);
    memcpy(out,s_scratch,32);
}

static uint8_t PRE_BASE[104];
static volatile int done=0;

int main(int argc,char**argv){
    if(argc<4){fprintf(stderr,"usage: %s minter_hex start_nonce target_bits [threads]\n",argv[0]);return 1;}
    memset(PRE_BASE,0,104);
    uint32_t chainid=4663;   // Robinhood Chain
    PRE_BASE[28]=chainid>>24;PRE_BASE[29]=chainid>>16;PRE_BASE[30]=chainid>>8;PRE_BASE[31]=(uint8_t)chainid;
    const char*ch="EF08089e4E082071AA39Ce99C460c0250744d758"; // FAB4200 contract
    for(int i=0;i<20;i++){unsigned b;sscanf(ch+2*i,"%2x",&b);PRE_BASE[32+i]=(uint8_t)b;}
    ch=argv[1]; if(ch[0]=='0'&&ch[1]=='x')ch+=2;
    for(int i=0;i<20;i++){unsigned b;sscanf(ch+2*i,"%2x",&b);PRE_BASE[52+i]=(uint8_t)b;}

    uint64_t start=strtoull(argv[2],0,0);
    int target=atoi(argv[3]);
    int nthreads=argc>4?atoi(argv[4]):omp_get_max_threads();
    omp_set_num_threads(nthreads);

    fprintf(stderr,"mining minter=%s start=%llu target=%d bits threads=%d\n",argv[1],(unsigned long long)start,target,nthreads);

    #pragma omp parallel
    {
        uint8_t pre[104]; memcpy(pre,PRE_BASE,104);
        uint8_t h[32]; uint64_t s_scr[25];
        int tid=omp_get_thread_num();
        for(uint64_t k=0;!done;k++){
            uint64_t n=start+(uint64_t)tid+k*nthreads;
            pre[96]=(uint8_t)(n>>56);pre[97]=(uint8_t)(n>>48);pre[98]=(uint8_t)(n>>40);pre[99]=(uint8_t)(n>>32);
            pre[100]=(uint8_t)(n>>24);pre[101]=(uint8_t)(n>>16);pre[102]=(uint8_t)(n>>8);pre[103]=(uint8_t)n;
            keccak104(pre,h,s_scr);
            int lz=0,i=0;
            while(i<32&&h[i]==0){lz+=8;i++;}
            if(i<32){uint8_t b=h[i];while(!(b&0x80)){lz++;b<<=1;}}
            if(lz>=target){
                #pragma omp critical
                {
                    printf("FOUND nonce=%llu bits=%d hash=",(unsigned long long)n,lz);
                    for(int x=0;x<32;x++)printf("%02x",h[x]);
                    printf("\ncalldata=0xa0712d68%016llx\n",(unsigned long long)n);
                    fflush(stdout); done=1;
                }
            }
        }
    }
    return 0;
}
