// fabminer_gpu.cu — FAB 4200-style keccak PoW miner, CUDA. VERIFIED against pycryptodome 2026-08-22.
// preimage: chainid(4663, 32B BE) | contract(20B) | minter(20B) | nonce(uint256 32B BE)
// Both classic GPU-port bugs fixed here (see SKILL.md "GPU pitfalls"):
//   1. nonce XORed into s[12] as BIG-endian bytes (bswap before XOR)
//   2. leading-zero check on byte-swapped word0 (digest byte order)
// Benchmark on Modal H100: ~7 GH/s; 40-bit expected hit ≈ 4 min.
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cuda_runtime.h>

#define ROTL(x,n) (((x)<<(n))|((x)>>(64-(n))))

__device__ __constant__ uint64_t RC[24] = {
0x0000000000000001ULL,0x0000000000008082ULL,0x800000000000808aULL,0x8000000080008000ULL,
0x000000000000808bULL,0x0000000080000001ULL,0x8000000080008081ULL,0x8000000000008009ULL,
0x000000000000008aULL,0x0000000000000088ULL,0x0000000080008009ULL,0x000000008000000aULL,
0x000000008000808bULL,0x800000000000008bULL,0x8000000000008089ULL,0x8000000000008003ULL,
0x8000000000008002ULL,0x8000000000000080ULL,0x000000000000800aULL,0x800000008000000aULL,
0x8000000080008081ULL,0x8000000000008080ULL,0x0000000080000001ULL,0x8000000080008008ULL};

__device__ void keccakf(uint64_t s[25]){
    uint64_t t,bc[5];
    const int ROTC[24]={1,3,6,10,15,21,28,36,45,55,2,14,27,41,56,8,25,43,62,18,39,61,20,44};
    const int PILN[24]={10,7,11,17,18,3,5,16,8,21,24,4,15,23,19,13,12,2,20,14,22,9,6,1};
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

__global__ void mine(const uint64_t* base_words, unsigned long long start_nonce, int target_bits,
                     unsigned long long* found_nonce, volatile int* done){
    uint64_t st[25];
    #pragma unroll
    for(int i=0;i<25;i++) st[i]=0;
    #pragma unroll
    for(int i=0;i<17;i++) st[i]=base_words[i];

    for(unsigned long long k=threadIdx.x + blockIdx.x*(unsigned long long)blockDim.x; !*done;
        k += (unsigned long long)gridDim.x*blockDim.x){
        uint64_t s[25];
        #pragma unroll
        for(int i=0;i<25;i++) s[i]=st[i];
        unsigned long long n = start_nonce + k;
        // nonce occupies preimage bytes 96..103 BIG-endian → bswap into LE word 12
        uint64_t nb = ((n & 0x00000000000000FFULL) << 56) | ((n & 0x000000000000FF00ULL) << 40) |
                      ((n & 0x0000000000FF0000ULL) << 24) | ((n & 0x00000000FF000000ULL) << 8) |
                      ((n & 0x000000FF00000000ULL) >> 8) | ((n & 0x0000FF0000000000ULL) >> 24) |
                      ((n & 0x00FF000000000000ULL) >> 40) | ((n & 0xFF00000000000000ULL) >> 56);
        s[12] ^= nb;
        keccakf(s);
        // digest bytes are the state words' bytes big-endian per byte position; word0 read LE puts
        // digest byte 7 at the MSB — swap so clzll counts leading zeros of the TRUE digest.
        uint64_t w0 = s[0];
        uint64_t w0bs = ((w0 & 0x00000000000000FFULL) << 56) | ((w0 & 0x000000000000FF00ULL) << 40) |
                        ((w0 & 0x0000000000FF0000ULL) << 24) | ((w0 & 0x00000000FF000000ULL) << 8) |
                        ((w0 & 0x000000FF00000000ULL) >> 8) | ((w0 & 0x0000FF0000000000ULL) >> 24) |
                        ((w0 & 0x00FF000000000000ULL) >> 40) | ((w0 & 0xFF00000000000000ULL) >> 56);
        if(w0bs==0){ atomicExch(found_nonce,n); *done=1; return; } // >=64 bits
        int lz=__clzll(w0bs);
        if(lz>=target_bits && *done==0){
            atomicExch(found_nonce,n); *done=1; return;
        }
    }
}

int main(int argc,char**argv){
    const char* minter = argc>1?argv[1]:"6D37DAc0525119ef3516E498120c3542cE60126B";
    unsigned long long start = argc>2?strtoull(argv[2],0,0):0;
    int target = argc>3?atoi(argv[3]):40;
    if(minter[0]=='0'&&minter[1]=='x')minter+=2;

    uint8_t block[136]; memset(block,0,136);
    uint32_t chainid=4663;
    block[28]=chainid>>24;block[29]=chainid>>16;block[30]=chainid>>8;block[31]=(uint8_t)chainid;
    const char*ch="EF08089e4E082071AA39Ce99C460c0250744d758";
    for(int i=0;i<20;i++){unsigned b;sscanf(ch+2*i,"%2x",&b);block[32+i]=(uint8_t)b;}
    for(int i=0;i<20;i++){unsigned b;sscanf(minter+2*i,"%2x",&b);block[52+i]=(uint8_t)b;}
    block[104]=0x01;
    block[135]|=0x80;

    uint64_t words[17];
    memcpy(words,block,136);

    uint64_t* d_words;
    cudaMalloc(&d_words,17*8);
    cudaMemcpy(d_words,words,17*8,cudaMemcpyHostToDevice);

    unsigned long long* d_found = nullptr;
    cudaMallocManaged((void**)&d_found,8);
    *d_found=0;
    int* d_done = nullptr;
    cudaMallocManaged((void**)&d_done,4);
    *d_done=0;

    int blocks=2048, threads=256;
    mine<<<blocks,threads>>>(d_words,start,target,d_found,d_done);
    cudaError_t err=cudaDeviceSynchronize();
    if(err!=cudaSuccess){ printf("CUDAERR %s\n",cudaGetErrorString(err)); return 2; }
    if(*d_done) printf("FOUND nonce=%llu\n",*d_found);
    else printf("EXHAUSTED\n");
    return 0;
}
