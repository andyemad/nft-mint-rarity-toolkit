// hcminer.c — Hashcats (hashcats.fun) keccak PoW nonce hunter. Robinhood Chain 4663.
//
// Collection: 0xCA75DF55Cc9C476DB27a7375D1fc8E794cf80721
// workHash(miner,nonce,prev,anchor) = keccak256( abi.encodePacked(
//        address miner(20) | uint256 nonce(32 BE) | uint256 prev(32 BE) | bytes32 anchor(32) ) )
//   -> 116 bytes = ONE keccak-256 block (rate 136), padding 0x01 @116, 0x80 @135.
//   Accept iff work < target (target = targetFor(msg.sender) / currentTarget()).
//   prev = work value of the previous cat (workOf[tokenId-1]).  tx: mine(nonce, anchorBlock) payable.
//
// Message word map (word i = LE64 of msg[8i..8i+7]):
//   w0,w1,w2 <- miner(20B) at msg[0..19]   (w2 = miner[16..19] | nonce[0..3])
//   w3 <- nonce[4..11]   w4 <- nonce[12..19]   w5 <- nonce[20..27]   w6 <- nonce[28..31]|prev[0..3]
//   w7..w13 <- prev/anchor   w14 = anchor[28..31] | 0x01<<32   w16 = 0x80<<56
// Search space: nonce = (salt64 << 64) | counter64  =>  nonce[0..15]=0 except salt at [8..15],
//   nonce[16..23]=0, nonce[24..31]=counter BE.  Therefore only w3,w4 (salt) and w5,w6 (counter) move.
//
// Build:  gcc -O3 -fopenmp -o hcminer hcminer.c
// Modes:
//   ./hcminer selfcheck <miner_hex> <prev_hex> <anchor_hex>   # fast path vs reference, 200k nonces
//   ./hcminer verify <records.txt>     # lines: miner prev nonce anchor target work   (audit vs chain)
//   ./hcminer bench [seconds]
//   ./hcminer mine <miner_hex> <prev_hex> <anchor_hex> <target_hex> [threads] [max_s]
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#ifdef _OPENMP
#include <omp.h>
#else
// Apple clang ships no OpenMP: real fallbacks so the same file builds everywhere.
static int omp_get_thread_num(void){ return 0; }
static int omp_get_max_threads(void){ return 1; }
static void omp_set_num_threads(int n){ (void)n; }
#endif

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

static inline void keccakf(uint64_t s[25]){
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
static inline uint64_t bswap64(uint64_t x){
    return ((x&0x00000000000000FFULL)<<56)|((x&0x000000000000FF00ULL)<<40)|
           ((x&0x0000000000FF0000ULL)<<24)|((x&0x00000000FF000000ULL)<<8)|
           ((x&0x000000FF00000000ULL)>>8)|((x&0x0000FF0000000000ULL)>>24)|
           ((x&0x00FF000000000000ULL)>>40)|((x&0xFF00000000000000ULL)>>56);
}
static inline uint32_t bswap32(uint32_t x){
    return ((x&0xFFu)<<24)|((x&0xFF00u)<<8)|((x>>8)&0xFF00u)|((x>>24)&0xFFu);
}

// ---------- reference: hash the 116-byte preimage (single block) ----------
static void hc_hash_ref(const uint8_t in[116], uint8_t out[32]){
    uint8_t buf[136]; memset(buf,0,136);
    memcpy(buf,in,116);
    buf[116]=0x01; buf[135]|=0x80;
    uint64_t s[25]; memset(s,0,25*8);
    for(int i=0;i<17;i++){ uint64_t v; memcpy(&v,buf+i*8,8); s[i]^=v; }
    keccakf(s);
    memcpy(out,s,32);
}
static void hc_build_msg(const uint8_t miner[20],uint64_t salt,uint64_t c,
                         const uint8_t prev[32],const uint8_t anchor[32],uint8_t pre[116]){
    memset(pre,0,116);
    memcpy(pre,miner,20);
    // nonce = salt<<64 | c
    for(int i=0;i<8;i++) pre[28+i]=(uint8_t)(salt>>(8*(7-i)));
    for(int i=0;i<8;i++) pre[44+i]=(uint8_t)(c>>(8*(7-i)));
    memcpy(pre+52,prev,32);
    memcpy(pre+84,anchor,32);
}

// ---------- fast path ----------
typedef struct { uint64_t w[17]; } base_t;
static void hc_base(const uint8_t miner[20],const uint8_t prev[32],const uint8_t anchor[32],base_t *b){
    uint8_t buf[136]; memset(buf,0,136);
    memcpy(buf,miner,20); memcpy(buf+52,prev,32); memcpy(buf+84,anchor,32);
    buf[116]=0x01; buf[135]|=0x80;
    for(int i=0;i<17;i++){ uint64_t v; memcpy(&v,buf+i*8,8); b->w[i]=v; }
}
#define SALT_W3(s) ((uint64_t)bswap32((uint32_t)((s)>>32))<<32)   // msg[28..31]
#define SALT_W4(s) ((uint64_t)bswap32((uint32_t)(s)))             // msg[32..35]
#define CNT_W5(c)  ((uint64_t)bswap32((uint32_t)((c)>>32))<<32)   // msg[44..47]
#define CNT_W6(c)  ((uint64_t)bswap32((uint32_t)(c)))             // msg[48..51]
#define DEPTH(s0)  ((bswap64(s0)==0)?64:__builtin_clzll(bswap64(s0)))

// digest numeric words (BE) -> hh[0] most significant
#define DIGEST_WORDS(s,hh) { hh[0]=bswap64(s[0]); hh[1]=bswap64(s[1]); hh[2]=bswap64(s[2]); hh[3]=bswap64(s[3]); }
static int below(const uint64_t hh[4], const uint64_t tw[4]){
    for(int i=0;i<4;i++){ if(hh[i]<tw[i]) return 1; if(hh[i]>tw[i]) return 0; }
    return 0;   // equal is NOT below
}

static int hex2bin(const char *h, uint8_t *out, int n){
    if(h[0]=='0'&&h[1]=='x') h+=2;
    for(int i=0;i<n;i++){ unsigned b; if(sscanf(h+2*i,"%2x",&b)!=1) return -1; out[i]=(uint8_t)b; }
    return 0;
}
static void target_words(const uint8_t t[32], uint64_t tw[4]){
    for(int i=0;i<4;i++){ uint64_t v=0; for(int j=0;j<8;j++) v=(v<<8)|t[i*8+j]; tw[i]=v; }
}

int main(int argc,char**argv){
    if(argc<2){fprintf(stderr,"usage: %s selfcheck|verify|bench|mine ...\n",argv[0]);return 1;}

    if(!strcmp(argv[1],"selfcheck")){
        if(argc<5){fprintf(stderr,"need miner prev anchor hex\n");return 1;}
        uint8_t miner[20],prev[32],anc[32];
        if(hex2bin(argv[2],miner,20)||hex2bin(argv[3],prev,32)||hex2bin(argv[4],anc,32)){fprintf(stderr,"hex\n");return 1;}
        base_t b; hc_base(miner,prev,anc,&b);
        srand(1234); int bad=0; long long n=200000;
        for(long long k=0;k<n;k++){
            uint64_t salt=((uint64_t)rand()<<40)^((uint64_t)rand()<<20)^(uint64_t)rand();
            uint64_t c=((uint64_t)rand()<<40)^((uint64_t)rand()<<20)^(uint64_t)rand();
            uint8_t pre[116],href[32]; hc_build_msg(miner,salt,c,prev,anc,pre);
            hc_hash_ref(pre,href);
            uint64_t s[25]; memcpy(s,b.w,sizeof(b.w)); memset(s+17,0,8*8);
            s[3]^=SALT_W3(salt); s[4]^=SALT_W4(salt);
            s[5]^=CNT_W5(c);     s[6]^=CNT_W6(c);
            keccakf(s);
            uint8_t hf[32];
            for(int i=0;i<4;i++){ uint64_t v=bswap64(s[i]); for(int j=0;j<8;j++) hf[i*8+j]=(uint8_t)(v>>(8*(7-j))); }
            if(memcmp(hf,href,32)!=0){
                bad++;
                if(bad<4){ printf("MISMATCH k=%lld salt=%llx c=%llx\n ref=",k,(unsigned long long)salt,(unsigned long long)c);
                    for(int i=0;i<32;i++)printf("%02x",href[i]); printf("\n fast=");
                    for(int i=0;i<32;i++)printf("%02x",hf[i]); printf("\n"); }
            }
        }
        printf("selfcheck: %lld nonces, %d mismatches -> %s\n",n,bad,bad?"FAIL":"PASS");
        return bad?1:0;
    }

    if(!strcmp(argv[1],"verify")){
        if(argc<3){fprintf(stderr,"need records file\n");return 1;}
        FILE *f=fopen(argv[2],"r"); if(!f){perror("open");return 1;}
        char line[512]; int n=0,bad=0;
        while(fgets(line,sizeof line,f)){
            char miner[64],prev[80],nonce[80],anc[80],tgt[80],work[80];
            if(sscanf(line,"%63s %79s %79s %79s %79s %79s",miner,prev,nonce,anc,tgt,work)!=6) continue;
            uint8_t m[20],pv[32],an[32],tg[32],wk[32],pre[116],h[32];
            if(hex2bin(miner,m,20)||hex2bin(prev,pv,32)||hex2bin(anc,an,32)||hex2bin(tgt,tg,32)||hex2bin(work,wk,32)) continue;
            memset(pre,0,116); memcpy(pre,m,20);
            char *nz=nonce; if(nz[0]=='0'&&nz[1]=='x') nz+=2;
            for(int i=0;i<32;i++){ unsigned b; sscanf(nz+2*i,"%2x",&b); pre[20+i]=(uint8_t)b; }
            memcpy(pre+52,pv,32); memcpy(pre+84,an,32);
            hc_hash_ref(pre,h);
            int eq=memcmp(h,wk,32)==0;
            uint64_t hh[4],tw[4]; target_words(h,hh); target_words(tg,tw);
            n++;
            if(!eq){ bad++; printf("MISMATCH work=%s got=",work); for(int i=0;i<32;i++)printf("%02x",h[i]); printf("\n"); }
            else {
                int depth=0; for(int i=0;i<32;i++){ if(h[i]==0){depth+=8;continue;} int bb=h[i]; while(!(bb&0x80)){depth++;bb<<=1;} break; }
                printf("ok depth=%d below_target=%s\n",depth,below(hh,tw)?"yes":"NO");
            }
        }
        fclose(f);
        printf("verified %d records, %d mismatches -> %s\n",n,bad,bad?"FAIL":"PASS");
        return bad?1:0;
    }

    if(!strcmp(argv[1],"bench")){
        int secs = argc>2?atoi(argv[2]):5;
        uint8_t miner[20]; memset(miner,0x11,20);
        uint8_t prev[32];  memset(prev,0x22,32);
        uint8_t anc[32];   memset(anc,0x33,32);
        base_t b; hc_base(miner,prev,anc,&b);
        volatile long long total=0; double t0=(double)clock()/CLOCKS_PER_SEC;
        #pragma omp parallel
        {
            uint64_t st[17]; memcpy(st,b.w,sizeof(st));
            uint64_t salt=((uint64_t)time(NULL)<<20)^(uint64_t)(omp_get_thread_num()+1);
            st[3]^=SALT_W3(salt); st[4]^=SALT_W4(salt);
            long long local=0;
            for(uint64_t c=((uint64_t)omp_get_thread_num())<<40;;c+=1){
                uint64_t s[25]; memcpy(s,st,17*8); memset(s+17,0,8*8);
                s[5]^=CNT_W5(c); s[6]^=CNT_W6(c);
                keccakf(s);
                local++;
                if((local&0xFFFF)==0){
                    double el=(double)clock()/CLOCKS_PER_SEC-t0;
                    #pragma omp atomic
                    total+=local&0xFFFF; local&=~0xFFFFLL;
                    if(el>secs) break;
                }
            }
            #pragma omp atomic
            total+=local;
        }
        double el=(double)clock()/CLOCKS_PER_SEC-t0;
        printf("%.1f MH/s  (%lld hashes in %.2fs, %d threads)\n",(double)total/el/1e6,total,el,omp_get_max_threads());
        return 0;
    }

    if(!strcmp(argv[1],"mine")){
        if(argc<6){fprintf(stderr,"usage: mine <miner_hex> <prev_hex> <anchor_hex> <target_hex> [threads] [max_s]\n");return 1;}
        uint8_t miner[20],prev[32],anc[32],tgt[32];
        if(hex2bin(argv[2],miner,20)||hex2bin(argv[3],prev,32)||hex2bin(argv[4],anc,32)||hex2bin(argv[5],tgt,32)){
            fprintf(stderr,"hex parse\n");return 1; }
        int nthreads = argc>6?atoi(argv[6]):4;
        int maxs = argc>7?atoi(argv[7]):60;
        if(nthreads<1) nthreads=1;
        base_t b; hc_base(miner,prev,anc,&b);
        uint64_t tw[4]; target_words(tgt,tw);
        int tb=0; for(int i=0;i<32;i++){ if(tgt[i]==0){tb+=8;continue;} int bb=tgt[i]; while(!(bb&0x80)){tb++;bb<<=1;} break; }
        fprintf(stderr,"mining target=%d bits threads=%d max=%ds\n",tb,nthreads,maxs);
        volatile int state=0;            // 0 running, 1 found, -1 timeout
        volatile unsigned long long fsalt=0,fc=0;
        double t0=(double)clock()/CLOCKS_PER_SEC;
        #pragma omp parallel num_threads(nthreads)
        {
            uint64_t st[17]; memcpy(st,b.w,sizeof(st));
            uint64_t salt=((uint64_t)time(NULL)<<24)^((uint64_t)(omp_get_thread_num()+1)<<8)^0x9E37;
            st[3]^=SALT_W3(salt); st[4]^=SALT_W4(salt);
            for(uint64_t c=((uint64_t)omp_get_thread_num())<<40;;c+=(uint64_t)nthreads){
                if(state) break;
                uint64_t s[25]; memcpy(s,st,17*8); memset(s+17,0,8*8);
                s[5]^=CNT_W5(c); s[6]^=CNT_W6(c);
                keccakf(s);
                if(DEPTH(s[0])>=tb){
                    uint64_t hh[4]; DIGEST_WORDS(s,hh);
                    if(below(hh,tw)&&!state){
                        #pragma omp critical
                        { if(!state){ state=1; fsalt=salt; fc=c; } }
                    }
                }
                if((c&0xFFFFF)<(uint64_t)nthreads){
                    double el=(double)clock()/CLOCKS_PER_SEC-t0;
                    if(el>maxs&&!state) state=-1;
                }
            }
        }
        if(state==1){
            char nh[80]; memset(nh,0,sizeof nh);
            for(int i=0;i<16;i++) sprintf(nh+2*i,"%02x",(unsigned)((fsalt>>(8*(15-i)))&0xFF));
            for(int i=0;i<16;i++) sprintf(nh+32+2*i,"%02x",(unsigned)((fc>>(8*(15-i)))&0xFF));
            printf("FOUND salt=%llx counter=%llu\nnonce=0x%s\n",(unsigned long long)fsalt,(unsigned long long)fc,nh);
            return 0;
        }
        printf("TIMEOUT\n"); return 3;
    }
    fprintf(stderr,"unknown mode\n"); return 1;
}
