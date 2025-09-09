from methods_numpy import *
#from methods_mosek import *
import numpy as np
import argparse

parser = argparse.ArgumentParser("sample solver for CILWE for Dilithium")
parser.add_argument("--n", type=int, default=256, help="dimension of the secret key")
parser.add_argument("--m", type=int, default=350, help="number of samples")
parser.add_argument("--tau", type=int, default=39, help="tau of Dilithium")
parser.add_argument("--p", type=float, default=0.1, help="contamination rate")
parser.add_argument("--eta", type=int, default=2, help="key coefficients between -eta and +eta")

args = parser.parse_args()
print(args)

def matching_bits(s,s_hat):
    '''returns the number of matching bits between s and s'''
    return np.count_nonzero(s==np.round(s_hat))
#generate some samples
C, z, y, s = generate_sample(m=args.m, tau=args.tau, p=args.p, n=args.n, eta=args.eta,filter_threshold=2*int(np.sqrt(2*args.tau)))  

#solve with cauchy regression
s_hat,t = irls_cauchy(C, z, s,iterations = 20)

print("Number of matching bits for Cauchy regression: ", matching_bits(s,s_hat))

#solve with huber regression
#s_hat_huber = huber(C, z, huberparam = 0.125)

#print("Number of matching bits for Huber regression: ", matching_bits(s,s_hat_huber))

#solve with ols regression
s_hat_ols = ols(C, z)

print("Number of matching bits for OLS regression: ", matching_bits(s,s_hat_ols))