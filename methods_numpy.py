import numpy as np
from sklearn.linear_model import LinearRegression
import time

def keygen(length=256, eta = 2):
	'''generates a key for n dimensions. n should be fixed to 1 for our experiments
	
	length: how many coefficients has the key?
	eta: draws coefficients between -eta and +eta
	
	returns the key'''
	s = np.random.choice(np.arange(-eta,eta+1), length)
	return s 


def generate_e(m, tau, p, s, C,filter_threshold):
	'''
	not necesarrily efficient method to sample the errors depend on everything
	m: number of samples to generate
	tau: tau of dilithium
	p: contamination rate
	s: the correct secret key 
	C: The data matrix 
	filtherthresh: The maximum value of the output (in Dilithium: z). Should be set to 2*sqrt(2*tau)

	returns an error vector y
	
	'''
	#design choice: We reject cs>tau because it is unlikely to observe them and would introduce a larger error.
	y = np.zeros(m)
	for i in range(m):
		if np.random.rand() < p:
			# rejection sampling
			while True:
				y_i = np.random.uniform(-4*tau, 4*tau)
				b_i = C[i] @ s + y_i
				if np.abs(b_i) <= filter_threshold and y_i != 0:
					# e_i as integer
					y[i] = int(y_i)
					break
	return y

def generate_C(m, n, tau):
	'''generates the data matrix:
	m: number of samples
	n: dimensions
	tau: the number of non-zeros in Data matrix
	
	return the Data matrix C'''
	C = np.zeros((m, n))
	for i in range(m):
		non_zero_indices = np.random.choice(n, tau, replace=False)
		C[i, non_zero_indices] = np.random.choice([-1, 1], tau)
	return C

def generate_sample(m,tau,p,s=None,n = 256, eta =2,filter_threshold = 39):
	'''generates a proper sample using rejection sampling
	
	m: number of samples
	tau: the number of non-zeros in Data matrix
	p: contamination rate
	s: the correct secret key
	n: number of dimensions 
	eta: draws key coefficients between -eta and +eta
	filter_threshold: The maximum value of the output z. Should be set to 2*sqrt(2*tau)

	returns:
		the data matrix C
		the output vector z
		the error vector  y
		the secret key used s
	'''
	C = generate_C(m, n, tau)
	if s is None:
		s = keygen(length=n,eta=eta)
	y = generate_e(m, tau, p, s, C,filter_threshold)
	z = C @ s + y
	
	#reject if b > filterthresh, keep promised length
	flag = True
	while(flag):
		mask = np.abs(z) <= filter_threshold
		if np.all(mask):
			break
		#filter
		z = z[mask]
		C = C[mask]
		y = y[mask]
		#generate missing equations without error
		Cprime = generate_C(m-len(z),n,tau)
		zprime = Cprime@s
		#concat with next loop check if valid equations
		C = np.vstack([C,Cprime])
		z = np.concatenate([z,zprime])
		y = np.concatenate([y,np.zeros_like(zprime)])

	return C,z,y,s

# ols
def ols(C,z):
	'''Return the least-squares approximation'''
	return np.linalg.lstsq(C, z)[0]

#irls

def huber_loss(r, delta=1):
	'''the huber loss function'''
	return np.where(np.abs(r) <= delta, 0.5 * r**2, delta * (np.abs(r) - 0.5 * delta))

def huber_weight(r, delta=1):
	'''the huber weight function with flooring'''
	return np.where(np.abs(r) <= delta, 1, delta /(0.0000001 + np.abs(r)))


def irls(C,z,s,loss = "cauchy",iterations=100,huberparam = 0.125):
	'''
	solves an iterative reweighted least squares regression with the following parameters.
	estimates a key and rounds it to the nearest integer. Then compares if actually matches and stops if so.

	C: Data matrix
	z: dependent variable
	s: true value for estimator
	loss: loss function to choose, supports "cauchy" (cauchy loss function) and "huber" (huber loss function)
	iterations: stops after those iterations if it did not converge to the correct solution
	huberparam: if huber loss is used, this is the parameter for the loss function ("delta")
	
	returns
	s_hat: estimated regressor (estimated key for dilithium)
	t: how many iterations have past?
	'''
	m,n = C.shape
	lr = LinearRegression(n_jobs=1)
	weights = np.ones(m) / m

	for t in range(iterations):
		# Fit Least Squares (weighted)
		lr.fit(C, z, sample_weight = weights)
		s_hat = lr.coef_
		# Calculate the number of correct predictions (round beta_est to integer)
		correct_predictions = np.sum(s == np.round(s_hat))
		# Calculate the residuals
		residuals = z - C @ s_hat
		if loss == "cauchy":
			weights = 1 / (1 + residuals**2)
			weights /= np.sum(weights)
		elif loss == "huber":
			weights = huber_weight(residuals,delta=huberparam)
			weights /= np.sum(weights)
		else:
			raise NotImplementedError("the loss function you chose is not implemented.")

		if correct_predictions >= n: break
	return s_hat,t

def irls_cauchy(C,z,s,iterations = 1024, convergence_eps = 0.01, convergence_min_run = 10, timeout = 3600, x0 = None):
	'''
	solves an iterative reweighted least squares regression with Cauchy loss.
	estimates a key and rounds it to the nearest integer. Then compares if actually matches and stops if so.

	stops if estimate doesn't change for more than convergence_eps in at least convergence_min_run consecutive iterations.

	C: Data matrix
	z: dependent output variable
	s: true value for estimator / secret key
	iterations: stops after those iterations if it did not converge to the correct solution
	convergence_eps: Maximum change in prediction in max norm until convergence counter starts
	convergence_min_run: How long does convergence needs to get stuck before we break

	
	returns
	s_hat: estimated regressor (estimated key for Dilithium)
	t: how many iterations have past?
	'''
	lr = LinearRegression(n_jobs=1)
	convergence_counter = 0
	m,n = C.shape
	start = time.time()

	weights = np.ones(m) / m

	last_estimate = np.zeros_like(s)

	for t in range(iterations):
		# Fit Least Squares (weighted)
		lr.fit(C, z, sample_weight=weights)
		s_hat = lr.coef_

		# Calculate the number of correct predictions (round s_hat to integer)
		correct_predictions = np.sum(s == np.round(s_hat))

		# Calculate the residuals
		residuals = z - C @ s_hat

		# cauchy weight function
		weights = 1 / (1 + residuals**2)
		weights /= np.sum(weights)

		#assume it converged if max norm of last estimate - current estimate < eps
		converged = np.max(s_hat-last_estimate) < convergence_eps
		if converged:
			convergence_counter += 1
		else: 
			convergence_counter = 0
	   
		if correct_predictions==n or convergence_counter >= convergence_min_run: break
		if time.time() - start >= timeout: break
	return s_hat, t
