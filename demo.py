import numpy as np
import argparse
from regression import ILWE, run_all

parser = argparse.ArgumentParser('sample solver for CILWE for Dilithium')
parser.add_argument('--n', type = int, default = 256, help = 'dimension of the secret key')
parser.add_argument('--m', type = int, default = 350, help = 'number of samples')
parser.add_argument('--tau', type = int, default = 39, help = 'tau of Dilithium')
parser.add_argument('--p', type = float, default = 0.1, help = 'contamination rate')
parser.add_argument('--eta', type = int, default = 2, help = 'key coefficients between -eta and +eta')
parser.add_argument('--seed', type = int, default = 0, help = 'key coefficients between -eta and +eta')
parser.add_argument('--full', action = 'store_true', default = False, help = 'run large scale experiment and plot results')

args = parser.parse_args()
print(args)

if args.full:
	run_all()
	input()
else:
	instance = ILWE(args.m, args.p, args.n, eta = args.eta, tau = args.tau, seed = args.seed)
	instance.cauchy()
	instance.L1()
	instance.L2()
	instance.huber()
	instance.ILP()
	print(instance)
	print(instance.log)
