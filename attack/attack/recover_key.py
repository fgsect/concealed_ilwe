import numpy as np
import argparse
import cvxpy as cvx

from sklearn.linear_model import LinearRegression, HuberRegressor
from tqdm import tqdm
from scipy.linalg import toeplitz

# Load data generator signature data
def load_data(file_path):
    try:
        # Load the arrays from the .npy files
        s1 = np.load(file_path + 's1.npy')
        y = np.load(file_path + 'y.npy')
        z = np.load(file_path + 'z.npy')
        c = np.load(file_path + 'c.npy')
        poly = np.load(file_path + 'poly.npy')
        coeff = np.load(file_path + 'coeff.npy')
        try:
            bs = np.load(file_path + 'bs.npy')
        except:
            bs = []
        return s1, y, z, c, bs, poly, coeff
    except Exception as e:
        print(f"An error occurred: {e}")

# Similar to calculate_c_matrix_np in simulation_umts24.py
def calculate_c_matrix_np(c):
	"""
	Adapted from: https://github.com/KatinkaBou/Probabilistic-Bounds-On-Singular-Values-Of-Rotation-Matrices/blob/c92bfa863fc640ca0c39b321dde1696edf84d467/negacyclic_probabilistic_bound.py#L20
	turn the polynomial into matrix form by using a rotation matrix
	"""
	row = np.zeros(c.shape[0], dtype=int)
	row[0] = c[0]
	row[1:] = -c[-1:0:-1]

	c_matrix = toeplitz(c, row)
	return c_matrix

# Cauchy regression similar to regression.py
def cauchy(A, b, beta, iterations=30, convergence_eps=0.01, convergence_min_run = 10):
	'''Solve by Cauchy estimator
	solves an iterative reweighted least squares regression with the following parameters.
	estimates a key and rounds it to the nearest integer. Then compares if actually matches and stops if so.

	stops if estimate doesn't change for more than convergence_eps in at least convergence_min_run consecutive iterations.

	A: Data matrix (C for dilithium)
	b: dependent variable (z for dilithium)
	beta: true value for estimator (s for dilithium)
	iterations: stops after those iterations if it did not converge to the correct solution
	convergence_eps: Maximum change in prediction in max norm until convergence counter starts
	convergence_min_run: How long does convergence needs to get stuck before we break

	returns
	beta_est: estimated regressor (estimated key for dilithium)
	t: how many iterations have past?
	'''
	lr = LinearRegression(n_jobs=1)
	convergence_counter = 0
	n=len(b)

	weights = np.ones(n) / n

	last_estimate = np.zeros_like(beta)

	for t in tqdm(range(iterations)):
		# Fit Least Squares (weighted)
		lr.fit(A, b, sample_weight=weights)
		beta_est = lr.coef_

		# Calculate the number of correct predictions (round beta_est to integer)
		correct_predictions = np.sum(beta == np.round(beta_est))

		# Calculate the residuals
		residuals = b - A @ beta_est

		weights = 1 / (1 + residuals**2)
		weights /= np.sum(weights)

		#assume it converged if max norm of last estimate - current estimate < eps
		converged = np.max(beta_est-last_estimate) < convergence_eps
		if converged:
			convergence_counter += 1
		else:
			convergence_counter = 0

		if correct_predictions==256 or convergence_counter >= convergence_min_run:
			break
	return beta_est, t

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Usage:  <data directory> <prediction.npy>")
    parser.add_argument("directory")
    parser.add_argument("file_name")

    # Parse command line arguments
    args = parser.parse_args()
    # Load attak_data
    s1, y, z, c, bs, poly, coeff = load_data(args.directory + "/")
    # Load predition file
    prediction = np.load(args.file_name, allow_pickle=True)

    # Maximum equations per polynomial
    n = len(prediction)
    # We need equations per polynomial!
    L, N = s1.shape
    eq_n = np.zeros((L), dtype=int)
    eq_z = np.zeros((L, n))
    eq_c = np.zeros((L, n, N))
    
    # Build ILWE instanes from attack data
    print(f"Collecting problem data:")
    positive = 0
    zeroError = 0
    zeroKnowledge = 0
    for i in tqdm(range(n)):
        if prediction[i] == 1:
            l = poly[i]
            n = coeff[i]
            polyIdx = eq_n[l]

            eq_z[l][polyIdx] = z[i]
            eq_c[l][polyIdx] = calculate_c_matrix_np(c[i])[n]

            if y[i] == 0:
                zeroError += 1
            if y[i] < 0:
                zeroKnowledge += 1

            eq_n[l] += 1
            positive += 1
    print()

    independentError = positive - zeroError - zeroKnowledge
    negative = len(prediction) - positive

    print(f"ILWE problem dimension: ({L},{N})")
    print(f"ILWE samples classified as y>=0: {positive}")
    print(f"    Zero-error (y=0): {zeroError} ({((zeroError/positive)*100):.2f})")
    print(f"    Small, Independent Error (y>0): {independentError} ({((independentError/positive)*100):.2f})")
    print(f"    Zero-Knowlledge (y<0): {zeroKnowledge} ({((zeroKnowledge/positive)*100):.2f})")
    print(f"ILWE samples classified as zero-knowledge y<0: {negative}")
    print(f"Samples per polynomial: {sum(eq_n)//L}")
    print(f"Z-Range: [{min(z)},...,{max(z)}]")
    print()

    # Recover secret key!
    for i in range(L):
        print(f"Computing secret key polynomial {i}:")
        z = eq_z[i][:eq_n[i]]
        Cm = eq_c[i][:eq_n[i]]
        s = s1[i]
        res = cauchy(Cm, z, s, iterations=100)
        print(f"Correct coefficients: " + str(np.sum(s == np.round(res[0]))) + f" ({res[1]} iterations)")
        print()
