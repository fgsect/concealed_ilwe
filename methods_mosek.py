import cvxpy as cvx
import numpy as np

#lad
def lad_fast(C,z,eta = 2):
	'''tries to recover the dilithium key by minimising an LP. Parameters have dilithium names
	C: Data Matrix
	z: dependent variable
	eta: the individual components of the key are between +/- eta'''
	m,n = C.shape
	x = cvx.Variable(n)
	e = cvx.Variable(m)
	prob = cvx.Problem(cvx.Minimize(cvx.norm(e,1)), [-eta <= x, x <= eta, C @ x == z - e])
	prob.solve()
	return x.value#np.array(x.value.round(), dtype = np.int64)

# huber
def huber(C,z,huberparam = 0.125):
	'''Solve convex problem to minimise Huber loss. faster than irls but requires cvxpy
	C: Data Matrix
	z: dependent variable'''
	m,n = C.shape
	x = cvx.Variable(n)
	e = cvx.Variable(m)
	prob = cvx.Problem(cvx.Minimize(cvx.sum(cvx.huber(e,M = huberparam))), [-2 <= x, x <= 2, C @ x == z - e])
	prob.solve()
	return np.array(x.value, dtype = np.float32)

#ILP
#Henning?