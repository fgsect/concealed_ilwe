"""
Regression methods to retrieve the secret key of CILWE (concealed integer learning-with-errors)
"""
import time
import warnings
import sqlite3
import numpy as np
import cvxpy as cvx
import mosek
from tabulate import tabulate
from sklearn.linear_model import LinearRegression
import argparse

from sampler import generate_sample
from plot import plot
warnings.filterwarnings("ignore")

# PARAMS
VERBOSE = False
TIMEOUT = 120
ATTEMPTS = 100
SUCCESS_THRESHOLD = 0.95
HUBER_PARAM = 0.125
NIST_LEVEL = 2 # must be 2,3 or 5

# parameters given by the setting of ML-DSA
NIST_PARAMS = {2: (2,39), 3: (4,49), 5: (2,60)}
DIMENSION = 256
# derived paramameters
ETA, TAU = NIST_PARAMS[NIST_LEVEL]
SIGMA = np.sqrt(((2 * ETA) ** 2 - 1) / (12 * TAU))
BETA = TAU * ETA
K = DIMENSION * ETA

# CODE

class ILWE():
	"""Instance for integer-LWE with low error rate."""

	def timer(f):
		"""Wrapper for optimisation methods."""
		def inner(self):
			function_name = str(f).split()[1].split('.')[1]
			t0 = time.time()
			try:
				s = f(self)
			except Exception as err:
				self.log.append((time.time(), 'failed to solve via ', function_name))
				self.log.append((time.time(), repr(err)))
				s = None
			t = time.time() - t0
			solved = s is not None and bool((s == self.s).all())
			matching_bits = np.count_nonzero(s == self.s) if s is not None else 0
			# store relevant data of the solution
			self.solutions[function_name] = (t, solved, matching_bits, s)
			return s,t,solved
		return inner

	def __init__(self, m, p, n = DIMENSION, eta = ETA, tau = TAU, seed = None):
		"""Create instance for CILWE

		Input:
			m: number of equations
			n: dimension
			seed: for PRNG, to create instance
		Output: instance, whose attributes satisfy z = C @ s + e
			z: public vector
			C: matrix
			e: noise
			s: private key
		"""
		self.m = m
		self.n = n
		self.eta = eta
		self.tau = tau
		self.log = []
		self.solutions = {} # dictionary method-name -> soltuion data
		self.methods = {
				'ILP': self.ILP, # comment out ILP to speed up the overall process
				'L1': self.L1,
				'L2': self.L2,
				'huber': self.huber,
				'cauchy': self.cauchy
			}

		if seed is not None:
			np.random.seed(seed)
		self.C, self.z, self.e, self.s = generate_sample(m, tau, p, dim = n, eta = eta, filterthresh = tau)
		self.k = int((self.e != 0).sum()) # number of errors

	@timer
	def L1(self):
		"""Solve convex problem to minimise 1-norm, is actually an LP"""
		s = cvx.Variable(self.n)
		e = cvx.Variable(self.m)
		prob = cvx.Problem(cvx.Minimize(cvx.norm(e,1)), [-self.eta <= s, s <= self.eta, self.C @ s == self.z - e])
		prob.solve()
		return np.array(s.value.round(), dtype = np.int64)

	@timer
	def L2(self):
		"""Solve via least-squares"""
		s = np.dot((np.dot(np.linalg.inv(np.dot(self.C.T, self.C)), self.C.T)), self.z)
		return np.array(s.round(), dtype = np.int64)

	@timer
	def huber(self):
		"""Solve convex problem to minimise Huber loss"""
		s = cvx.Variable(self.n)
		e = cvx.Variable(self.m)
		prob = cvx.Problem(cvx.Minimize(cvx.sum(cvx.huber(e,M = HUBER_PARAM))), [-self.eta <= s, s <= self.eta, self.C @ s == self.z - e])
		prob.solve()
		return np.array(s.value.round(), dtype = np.int64)

	@timer
	def cauchy(self):
		"""Solve by Cauchy estimator
		solves an iterative reweighted least squares regression with the following parameters.
		estimates a key and rounds it to the nearest integer. Then compares if actually matches and stops if so.

		stops if estimate doesn't change for more than convergence_eps in at least convergence_min_run consecutive iterations.

		allows to set the following parameters
		* iterations: stops after those iterations if it did not converge to the correct solution
		* convergence_eps: Maximum change in prediction in max norm until convergence counter starts
		* convergence_min_run: How long does convergence needs to get stuck before we break
		
		returns
		beta_est: estimated regressor (estimated key for dilithium)
		"""
		lr = LinearRegression(n_jobs=1)
		convergence_counter = 0
		start = time.time()
		A = self.C
		b = self.z
		n = len(b)
		beta = self.s

		weights = np.ones(n) / n

		last_estimate = np.zeros_like(beta)
		iterations = 1<<32 # limit is given via convergence and timeout
		convergence_eps = 0.01
		convergence_min_run = 10

		for t in range(iterations):
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

			if correct_predictions==256 or convergence_counter >= convergence_min_run: break
			if time.time() - start >= TIMEOUT: break
		self.log.append((time.time(), f'Cauchy: {t} iterations'))
		return np.array(beta_est.round(), dtype = np.int64)

	@timer
	def ILP(self):
		"""get timing for some Dilithium-ILP
		creating instance is happening within the function
		basic instance is guaranteed to be feasible

		Output:
			s|None: solution vector
		"""
		e = cvx.Variable(self.m, boolean = True)
		s = cvx.Variable(self.n, integer = True)
		constraints = [s >= - self.eta, s <= self.eta, self.z - self.C @ s <= K * (1-e), self.z - self.C @ s >= -K * (1-e)]
		objective = cvx.Maximize(cvx.sum(e))
		prob = cvx.Problem(objective, constraints)
		try:
			prob.solve(solver = cvx.MOSEK, mosek_params={mosek.dparam.optimizer_max_time: TIMEOUT}, verbose = VERBOSE)
			return np.array(s.value.round(), dtype = np.int64)
		except cvx.SolverError:
			self.log.append((time.time(),'ILP timeout'))

	def __str__(self):
		"""create table of all computed results."""
		return tabulate([(name, t, solved, bits) for name, (t, solved, bits, _) in self.solutions.items()],['method', 'time', 'solved', 'correct bits'], tablefmt = 'grid')

def run_method(n, m, p, eta, tau, cursor, conn, method : str):
	"""Get the instance with given parameters from DB and run given method on it."""
	cursor.execute('select seed from instance, run, method where method_id = method.rowid and instance_id = instance.rowid and m = ? and n = ? and p = ? and eta = ? and tau = ? and method.name = ?;', (m,n,p,eta,tau,method))
	seeds_done = [_[0] for _ in cursor.fetchall()]
	fails = 0
	for seed in range(ATTEMPTS):
		if seed in seeds_done: continue
		# Main loop, create next instance, run all methods and put results into database
		if open('status').read().strip() != 'run': break
		instance_id, instance = get_instance(m, n, eta, tau, p, seed, cursor, conn)
		_, runtime, success = getattr(instance, method)()
		success = int(success)
		cursor.execute('insert into run (instance_id, method_id,time,solved,timestamp) select ?,rowid,?,?,? from method where name = ?;', (instance_id, runtime, success, int(time.time()), method))
		conn.commit()
		fails += (1-success)
		if fails >= round((1 - SUCCESS_THRESHOLD) * ATTEMPTS): break

def get_instance(m, n, eta, tau, p, seed, cursor, conn):
	"""Return ID and instance of the chosen parameters

	create and insert into DB if none existed before"""
	instance = ILWE(m, p, n = n, eta = eta, tau = tau, seed = seed)
	cursor.execute('select rowid from instance where m = ? and n = ? and p = ? and eta = ? and tau = ? and seed = ?;', (m, n, p, eta, tau, seed))
	instance_id = cursor.fetchone()
	if instance_id is not None: return instance_id[0], instance

	cursor.execute('insert into instance (m,n,eta,tau,p,seed,errors) values (?,?,?,?,?,?,?);', (m, n, eta, tau, p, seed, instance.k))
	instance_id = cursor.lastrowid
	conn.commit()
	return instance_id, instance

def run_all():
	conn = sqlite3.connect('data/runs.db')
	cursor = conn.cursor()

	# dictionary for all methods with their ID in database
	dummy_instance = ILWE(300, 0.05, DIMENSION, ETA, TAU, 0)
	active_methods = list(dummy_instance.methods.keys())
	cursor.execute('select rowid, name from method;')
	methods = {name: ID for ID,name in cursor.fetchall() if name in active_methods}

	# bisection, how large m has to be for given success threshold
	for method in methods.keys():
		for p in [0.01,0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9]:
		# setting an upper bound, by always doubling the maximum
			while True:
				if open('status').read().strip() != 'run': break
				cursor.execute('''
					select m, sum(solved) as solved, count(*) as count, 1.0*sum(solved)/count(*) as chance
					from instance left join run on instance_id = instance.rowid
					where method_id = ? and p = ? and eta = ? and tau = ? 
					group by m, p, eta, tau;''', (methods[method], p, ETA, TAU))
				results = cursor.fetchall()
				# compute all parameter with less than N instances
				gaps = [row for row in results if row[2] < ATTEMPTS and row[2] - row[1] < round((1 - SUCCESS_THRESHOLD) * ATTEMPTS)]
				if gaps != []:
					for row in gaps:
						run_method(DIMENSION, row[0], p, ETA, TAU, cursor, conn, method)
				else:
					if any(float(row[-1]) >= SUCCESS_THRESHOLD for row in results): break # found an upper bound, continue with next part
					if results == []:
						# no instance tested for these parameters, yet
						m = int(DIMENSION / (1 - p))
					else:
						m = 2*max(row[0] for row in results)
						if m >= 41000: break
					run_method(DIMENSION, m, p, ETA, TAU, cursor, conn, method)

			# actual bisection
			while True:
				if open('status').read().strip() != 'run': break
				cursor.execute('''
					select m,eta,tau,p,sum(solved) as solved,count(*) as count, printf("%.3f", 1.0*sum(solved)/count(*)) as chance
					from instance left join run on instance_id = instance.rowid
					where method_id = ? and p = ? and eta = ? and tau = ? 
					group by m,p, eta, tau;''', (methods[method], p, ETA, TAU))
				results = cursor.fetchall()
				try:
					m_good = min(row[0] for row in results if float(row[-1]) >= SUCCESS_THRESHOLD)
				except ValueError: # no upper bound
					print(f'{method} has no bound for {p}')
					break
				try:
					m_bad = max(row[0] for row in results if float(row[-1]) < SUCCESS_THRESHOLD)
				except ValueError:
					#256 is lower bound for fail
					m_bad = 256
				if float(m_good) / m_bad <= 1.01:
					break
				m = (m_good + m_bad) >> 1
				run_method(DIMENSION, m, p, ETA, TAU, cursor, conn, method)

	conn.close()
	plot(NIST_LEVEL)

if __name__ == '__main__':
	run_all()
	input()
