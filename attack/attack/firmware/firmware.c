#include <stdint.h>
#include <assert.h>

#include "hal.h"
#include "simpleserial.h"

#define N_SHARES 2

static unsigned x = 123456789, y = 362436069, z = 521288629;

uint32_t rand32()
{
    unsigned t;
    
    x ^= x << 16;
    x ^= x >> 5;
    x ^= x << 1;
    
    t = x;
    x = y;
    y = z;
    z = t ^ x ^ y; 
    return z;
}

uint64_t rand64() { return ((uint64_t)rand32() << 32) + (uint64_t)rand32(); }

uint64_t Psi64(uint64_t x, uint64_t y) { return (x ^ y) - y; }

uint64_t Psi064(uint64_t x,uint64_t y,int n) { return Psi64(x,y) ^ ((~n & 1) * x); }

void copy64(uint64_t* x ,uint64_t* y ,int n) { for(int i = 0; i < n; i++) x[i] = y[i]; }

void refreshBool64(uint64_t a[],int n)
{
  for(int i=0;i<n-1;i++)
  {
    uint64_t tmp=rand64();
    a[n-1]=a[n-1] ^ tmp;
    a[i]=a[i] ^ tmp;
  }
}

__attribute__((noinline))
static void impconvBA_rec64(uint64_t *D_,uint64_t *x,int n)
{   
    if (n==2) {
        uint64_t r1=rand64();
        uint64_t r2=rand64();
        
        uint64_t y0=(x[0] ^ r1) ^ r2;
        uint64_t y1=x[1] ^ r1;
        uint64_t y2=x[2] ^ r2;
        
        uint64_t z0=y0 ^ Psi64(y0,y1);
        uint64_t z1=Psi64(y0,y2);
        
        D_[0]=y1 ^ y2;
        D_[1]=z0 ^ z1;
        return;
    }

    uint64_t y[n+1];
    copy64(y,x,n+1);
    
    refreshBool64(y,n+1);
    
    uint64_t z[n];
    
    z[0]=Psi064(y[0],y[1],n);
    for(int i=1;i<n;i++)
        z[i]=Psi64(y[0],y[i+1]);
    
    uint64_t A[n-1],B[n-1];
    impconvBA_rec64(A,y+1,n-1);
    impconvBA_rec64(B,z,n-1);
    
    for(int i=0;i<n-2;i++)
        D_[i]=A[i]+B[i];
    
    D_[n-2]=A[n-2];
    D_[n-1]=B[n-2];
}

uint8_t setup(uint8_t* pt, uint8_t len)
{    
    uint64_t boolean_shares[N_SHARES + 1];
    uint64_t arithmetic_shares[N_SHARES];

    boolean_shares[0] = *((uint32_t*)pt);
    boolean_shares[1] = *((uint32_t*)&pt[sizeof(uint32_t)]);
    boolean_shares[N_SHARES] = 0;
    
    arithmetic_shares[0] = rand64();
    arithmetic_shares[1] = rand64();

    trigger_high();
    for (int j = 0; j < 50; j++) asm("nop");
    impconvBA_rec64(arithmetic_shares, boolean_shares, N_SHARES);
    for (int j = 0; j < 50; j++) asm("nop");
    trigger_low();

	return 0;
}

int main(void)
{
    platform_init();
	init_uart();
	trigger_setup();
	 
	putch('O');
	putch('K');
	putch('!');
	putch('\n');
	 
	simpleserial_init();
    simpleserial_addcmd('o', (N_SHARES * sizeof(uint32_t)), setup);

	while(1) simpleserial_get();
}
