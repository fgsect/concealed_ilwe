#include <atomic>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

extern "C" {
// Dilithium includes
#include "packing.h"
#include "params.h"
#include "poly.h"
#include "polyvec.h"
#include "sign.h"

// Masked Dilitthium includes
#include "masking_interface.h"
}

// Only collect equations where z_{i,j} < | tau |
#if DILITHIUM_MODE == 2
#define FILTER_Z 50

#elif DILITHIUM_MODE == 3
#define FILTER_Z 100

#elif DILITHIUM_MODE == 5
#define FILTER_Z 80
#endif

namespace DataGenerator
{
    class Equation
    {
        public:
            uint8_t poly;
            uint8_t coeff;
            int32_t z;
            int32_t y;
            uint32_t bs[N_SHARES];
            int32_t c[N];
    };

    class Signature
    {
    public:
        Signature(void) {
            mEquationsLocal.reserve(L * N); // Allocate space for maximum number of equations, in reality we often need half that space.
        };

        void SetNextBooleanShares(uint64_t* aBooleanShares);
        void GatherEquations(poly *aC, polyvecl *aY, polyvecl *aZ);

        std::vector<Equation> mEquationsLocal;
        uint32_t mBS[L][N][N_SHARES];
        uint32_t mZeroCoefficientsLocal = 0;

    private:
        uint16_t mYIdx = 0;
    };

    class DataGenerator
    {
    public:
        DataGenerator(bool argMasked, unsigned argSignaturesTarget, const std::string& argOutPAth, unsigned argNThreads)
            : mMasked(argMasked), mSignaturesTarget(argSignaturesTarget), mOutPath(argOutPAth), mNThreads(argNThreads)
        {
            mEquationsGlobal.reserve(argSignaturesTarget * L * N); // Allocate space for maximum number of equations, in reality we often need half that space.
            crypto_sign_keypair(mPublicKey, mSecretKey);

            uint8_t seedbuf[2*SEEDBYTES + 3*CRHBYTES];
            uint8_t *rho, *tr, *key;
            polyvecl s1;
            polyveck s2, t0;

            rho = seedbuf;
            tr = rho + SEEDBYTES;
            key = tr + CRHBYTES;
            unpack_sk(rho, tr, key, &t0, &s1, &s2, mSecretKey);

            for(int i = 0; i < L; i++)
                for(int j = 0; j < N; j++)
                    mS1[i][j] = s1.vec[i].coeffs[j];
        };

        void GenerateData(void);

    private:
        uint8_t mPublicKey[CRYPTO_PUBLICKEYBYTES];
        uint8_t mSecretKey[CRYPTO_SECRETKEYBYTES];

        std::atomic<uint32_t> mAtomicTries = 0, mZeroCoefficients = 0;
        std::vector<Equation> mEquationsGlobal;
        std::mutex mEquationsMutex;
        std::mutex mSignatureMutex;

        int32_t mS1[L][N];

        const bool mMasked;
        const unsigned mSignaturesTarget;
        const std::string mOutPath;
        unsigned mNThreads;

        void SignRandomMessages(int aThreadId);
        void WriteDataToNPY(void);
    };

}
