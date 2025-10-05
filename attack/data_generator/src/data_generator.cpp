#include <chrono>
#include <filesystem>
#include <iostream>
#include <random>
#include <thread>

// NPY
#include "npy.hpp"

// Attack includes
#include "data_generator.hpp"

extern "C" {
#include "data_generator.h"

// Dilithium includes
#include "randombytes.h"
#include "rounding.h"
#include "packing.h"
#include "reduce.h"

// Masked Dilitthium includes
#include "masked_sign.h"
#include "random.h"
#include "masking_interface.h"
}

#define MLEN 59

namespace DataGenerator
{
    thread_local std::unique_ptr<Signature> threadlocalSignature;

    void DataGenerator::GenerateData(void)
    {
        std::cout << "###### DataGenerator for " << (mMasked ? "Masked " : "") << "Dilithium (Mode: " << DILITHIUM_MODE << ") ######" << std::endl;
        std::cout << "Gathering " << mSignaturesTarget << " signatures." << std::endl
                  << std::endl;

        auto start = std::chrono::high_resolution_clock::now();

        // Generate signatures in parallel
        std::vector<std::thread> threads(mNThreads);
        for (int i = 0; i < threads.size(); ++i)
            threads[i] = std::thread([this, i]
                                     { this->SignRandomMessages(i); });
        for (std::thread &thread : threads)
            thread.join();

        auto end = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::seconds>(end - start).count();
        std::cout << std::endl << "Execution time: " << duration << " seconds" << std::endl;

        // Write gathered data to .npy files for Python processing
        WriteDataToNPY();

        std::cout << std::endl
                  << "Collected Equations - Y==0: " << mZeroCoefficients << " / Y!=0: " << (mEquationsGlobal.size()- mZeroCoefficients) << std::endl;

        std::cout << std::endl
                  << "Done - data written to ./" << mOutPath << " directory!" << std::endl;
    }

    void DataGenerator::SignRandomMessages(int aThreadId)
    {
        size_t smlen;
        uint8_t sm[MLEN + CRYPTO_BYTES];
        uint8_t m[MLEN + CRYPTO_BYTES];

        int outCount = 0;
        while (true) {
            int tries = mAtomicTries++;
            int zeros = mZeroCoefficients;

            // Progress report on thread 0
            if (!aThreadId) {
                if (!(outCount++ % 500))
                    std::cout << "Signature " << zeros << " / " << mSignaturesTarget << " (Try: " << tries << ")" << std::endl;
            }

            if (zeros >= mSignaturesTarget) break;

            threadlocalSignature.reset(new Signature());

            // Generate random message
            randombytes(m, MLEN);

            uint8_t seedbuf[2*SEEDBYTES + 3*CRHBYTES];
            uint8_t *rho, *tr, *key;
            masked_polyvecl ms1;
            masked_polyveck ms2;
            polyvecl s1;
            polyveck s2, t0;

            rho = seedbuf;
            tr = rho + SEEDBYTES;
            key = tr + CRHBYTES;
            unpack_sk(rho, tr, key, &t0, &s1, &s2, mSecretKey);

            if (mMasked) {
                mask_polyvecl(&ms1, &s1);
                mask_polyveck(&ms2, &s2);
                masked_crypto_sign(sm, &smlen, m, MLEN, seedbuf, &ms1, &ms2, &t0);
            } else {
                crypto_sign(sm, &smlen, m, MLEN, mSecretKey);
            }

            {
                std::lock_guard<std::mutex> lk(mEquationsMutex);
                std::vector<Equation>& eq = threadlocalSignature->mEquationsLocal;
                mEquationsGlobal.insert(mEquationsGlobal.end(), eq.begin(), eq.end());

                if  (threadlocalSignature->mZeroCoefficientsLocal)
                    mZeroCoefficients += threadlocalSignature->mZeroCoefficientsLocal;
            }
        }
    }

    void DataGenerator::WriteDataToNPY(void)
    {
        if (std::filesystem::exists("./" + mOutPath))
            std::filesystem::remove_all("./" + mOutPath);
        std::filesystem::create_directories("./" + mOutPath);

        npy::npy_data_ptr<uint8_t> k;
        /* // Write pk
        k.data_ptr = mPublicKey;
        k.shape = { CRYPTO_PUBLICKEYBYTES };
        npy::write_npy(mOutPath + "/pk.npy", k);
        // Write sk
        k.data_ptr = mSecretKey;
        k.shape = { CRYPTO_SECRETKEYBYTES };
        npy::write_npy(mOutPath + "/sk.npy", k); */

        size_t n = mEquationsGlobal.size();

        uint8_t* poly = (uint8_t*) malloc(n * sizeof(uint8_t));
        uint8_t* coeff = (uint8_t*) malloc(n * sizeof(uint8_t));
        int32_t* z = (int32_t*) malloc(n * sizeof(int32_t));
        int32_t* y = (int32_t*) malloc(n * sizeof(int32_t));
        int32_t* c = (int32_t*) malloc(n * N * sizeof(int32_t));
        uint32_t* bs = (uint32_t*) malloc(n * N_SHARES * sizeof(uint32_t));

        int32_t* s1 = (int32_t*) malloc(L * N * sizeof(int32_t));

        for (int i = 0; i < n; i++) {
            Equation& eq = mEquationsGlobal[i];
            z[i] = eq.z;
            y[i] = eq.y;
            poly[i] = eq.poly;
            coeff[i] = eq.coeff;

            for (int l = 0; l < N; l++) {
                c[i * N + l] = eq.c[l];
            }

            for (int l = 0; l < N_SHARES; l++) {
                bs[i * N_SHARES + l] = eq.bs[l];
            }
        }

        int idx = 0;
        for (int l = 0; l < L; l++) {
            for (int n = 0; n < N; n++) {
                s1[idx++] = mS1[l][n];
            }
        }

        // Write polynomial indices
        k.data_ptr = poly;
        k.shape = { n };
        npy::write_npy(mOutPath + "/poly.npy", k);
        // Write coefficient indices
        k.data_ptr = coeff;
        k.shape = { n };
        npy::write_npy(mOutPath + "/coeff.npy", k);

        npy::npy_data_ptr<int32_t> d;
        // Write s1 data
        d.data_ptr = s1;
        d.shape = { L, N };
        npy::write_npy(mOutPath + "/s1.npy", d);
        // Write c data
        d.data_ptr = c;
        d.shape = { n, N };
        npy::write_npy(mOutPath + "/c.npy", d);
        // Write y data
        d.data_ptr = y;
        d.shape = { n };
        npy::write_npy(mOutPath + "/y.npy", d);
        // Write z data
        d.data_ptr = z;
        d.shape = { n };
        npy::write_npy(mOutPath + "/z.npy", d);

        npy::npy_data_ptr<uint32_t> b;
        if (mMasked) {
            // Write boolean shares data
            b.data_ptr = bs;
            b.shape = {n, N_SHARES};
            npy::write_npy(mOutPath + "/bs.npy", b);
        }

        free(c);
        free(coeff);
        free(poly);
        free(s1);
        free(y);
        free(z);
        free(bs);
    }

    void Signature::GatherEquations(poly *aC, polyvecl *aY, polyvecl *aZ)
    {
        for (int i = 0; i < L; ++i) {
            for (int j = 0; j < N; ++j) {
                if (std::abs(aZ->vec[i].coeffs[j]) >= FILTER_Z) continue;
                if (aY->vec[i].coeffs[j] == 0) mZeroCoefficientsLocal++;

                Equation eq;
                eq.poly = i;
                eq.coeff = j;

                eq.z = aZ->vec[i].coeffs[j];
                eq.y = aY->vec[i].coeffs[j];

                for (int l = 0; l < N; l++) {
                    eq.c[l] = aC->coeffs[l];
                }

                for (int l = 0; l < N_SHARES; l++) {
                    eq.bs[l] = mBS[i][j][l];
                }

                mEquationsLocal.push_back(eq);
            }
        }
    }

    void Signature::SetNextBooleanShares(uint64_t* aBooleanShares)
    {
        // Reset if indices are higher then possible, this happens on rejection.
        if (mYIdx >= L * N) mYIdx = 0;

        uint16_t polyIdx = mYIdx / N;
        uint16_t coeffIdx = mYIdx % N;

        for (int i = 0; i < N_SHARES; i++) {
            mBS[polyIdx][coeffIdx][i] = (uint32_t) aBooleanShares[i];
        }

        mYIdx++;
    }

    extern "C" {
        void SetCYZC(poly* aC, polyvecl* aY, polyvecl* aZ)
        {
            threadlocalSignature->GatherEquations(aC, aY, aZ);
        }

        void SetNextBooleanSharesC(uint64_t* aBooleanShares)
        {
            threadlocalSignature->SetNextBooleanShares(aBooleanShares);
        }

        uint32_t rand32(void)
        {
            static thread_local std::mt19937 gen;
            std::uniform_int_distribution<uint32_t> dist(0, UINT32_MAX);
            return dist(gen);
        }

        uint16_t rand16(void)
        {
            return (uint16_t)rand32() & (0xFFFF);
        }

        uint64_t rand64(void)
        {
            return ((uint64_t)rand32() << 32) + (uint64_t)rand32();
        }
    }
}

int main(int argc, char* argv[]) {
    if (argc < 4 || argc > 5) {
        std::cout << "###### DataGenerator for " << "Dilithium (Mode: " << DILITHIUM_MODE << ") ######" << std::endl;
        std::cout << "Usage: " << argv[0] << " <bool Masked> <unsigned SignaturesTarget> <string OutPath> (optional: <unsigned NThreads>)" << std::endl;
        return 1;
    }

    bool masked = (std::string(argv[1]) == "true" || std::string(argv[1]) == "1");
    unsigned size = std::stoul(argv[2]);

    unsigned threads = 1;
    if (argc == 5) threads = std::stoul(argv[4]);

    DataGenerator::DataGenerator dataGenerator(masked, size, argv[3], threads);
    dataGenerator.GenerateData();

    return 0;
}
