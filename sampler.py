import time
import numpy as np

def keygen(length = 256, eta = 2):
	'''generates a key for n dimensions. n should be fixed to 1 for our experiments
	
	length: how many coefficients has the key?
	eta: draws coefficients between -eta and +eta
	
	returns the key'''
	beta = np.random.choice(np.arange(-eta, eta+1), length)
	return beta


def generate_e(n, tau, q, beta, A, filterthresh):
	'''
	not necessarrily efficient method to sample the errors depend on everything
	n: number of samples to generate
	tau: tau of dilithium
	q: contamination rate (Dilithum: p)
	beta: the correct secret key (Dilithium: s)
	A: The data matrix (Dilithium: C)
	filtherthresh: The maximum value of the output (Dilithium: z). Should be set to 2*sqrt(2*tau)

	returns an error vector (Dilithum: y)
	
	'''
	#design choice: We reject cs>tau because it is unlikely to observe them and would introduce a larger error.
	e = np.zeros(n)
	for i in range(n):
		if np.random.rand() < q:
			# rejection sampling
			while True:
				e_i = np.random.uniform(-4*tau, 4*tau)
				b_i = A[i] @ beta + e_i
				if np.abs(b_i) <= filterthresh:
					# e_i as integer
					e[i] = int(e_i)
					break
	return e

def generate_A(n, p, tau):
	'''generates the data matrix:
	n: number of samples (Dilithium: m)
	p: dimensions (Dilithum: n)
	tau: the number of non-zeros in Data matrix (Dilithum tau)
	
	return the Data matrix (Dilithium: C)'''
	A = np.zeros((n, p))
	for i in range(n):
		non_zero_indices = np.random.choice(p, tau, replace=False)
		A[i, non_zero_indices] = np.random.choice([-1, 1], tau)
	return A

def generate_sample(n, tau, q, beta = None, dim = 256, eta = 2, filterthresh = 39):
	'''generates a proper sample using rejection sampling
	
	n: number of samples (Dilithium: m)
	tau: the number of non-zeros in Data matrix (Dilithum tau)
	q: contamination rate (Dilithum: p)
	beta: the correct secret key (Dilithium: s)
	dim: number of dimensions (Dilithium: n)
	eta: draws key coefficients between -eta and +eta
	filtherthresh: The maximum value of the output (Dilithium: z). Should be set to 2*sqrt(2*tau)

	returns:
		the data matrix (Dilithium: C)
		the output vector (Dilithium: z)
		the error vector (Dilithium: y)
		the secret key used (Dilithium: s)
	'''
	p=dim
	A = generate_A(n, p, tau)
	if beta is None:
		beta = keygen(length = dim, eta = eta)
	e = generate_e(n, tau, q, beta, A, filterthresh)
	b = A @ beta + e

	#reject if b > filterthresh, keep promised length
	flag = True
	while flag:
		mask = np.abs(b) <= filterthresh
		if np.all(mask):
			break
		#filter
		b = b[mask]
		A = A[mask]
		e = e[mask]
		#generate missing equations without error
		A_prime = generate_A(n-len(b), p, tau)
		b_prime = A_prime@beta
		#concat with next loop check if valid equations
		A = np.vstack([A,A_prime])
		b = np.concatenate([b, b_prime])
		e = np.concatenate([e, np.zeros_like(b_prime)])

	return A,b,e,beta
