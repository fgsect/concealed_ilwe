Solving Concealed ILWE and its Application for Breaking Masked Dilithium
===

The paper was published at AsiaCrypt 2025. 

The paper and BibTex is available at https://eprint.iacr.org/2025/1629

In this repository, we provide three main artifacts. 
1. Comparison of regression methods ("regression"): 
   This folder contains a docker image and all the code to rerun our simulated CILWE samples on the basis of Dilithium for all security levels (Figure 6 of the paper)
2. Simulation of CILWE on Dilithium ("simulation_umts24"): 
   This folder contains our simulated attack on Dilithium along the lines of UMTS24 (table 2 of the paper). 
3. Attack on masked Dilithium ("attack"):
   This folder contains the code for our machine learning aided side channel analysis of a first order masked Dilithium implementation.
4. Regression Algorithms ("simulation_umts24"):
   In this folder, we also provide a method that implements the Huber and Cauchy Regression in Python. Please refer to the last section of the readme for usage instructions.

# Comparison of regression methods
We investigated different regression methods for the Concealed Integer Learning with Errors (CILWE) problem.
Given different error rates, we test how many samples an instance must contain to be most likely solvable.

The experiment was originally run with [Mosek](https://www.mosek.com/) as a solver. This solver is commercial, but offers free academic licences.
We included a version with free solvers, that may yield slightly different results.

## Included Methods

* Huber regression
* Cauchy regression/Iterative Reweighted Least Squares
* Ordinary least squares (OLS, L2-norm)
* Least absolute deviation (LAD, L1-norm)
* Integer linear programming (ILP)

## Docker Usage [Recommended]

* OPTIONAL: ensure that your Mosek licence is in the folder `~/mosek`, or adjust the `docker-compose.yml`
* Go to the folder `regression`.
* Call `docker compose up --build -d` to start/resume the large scale experiment for NIST-level 2.  
  * Note that this takes SEVERAL DAYS to finish.
  * The database with the results and the plot are updated during this computation. So, intermediate data is available before the computation finishes.
  * To get quicker results (but less accurate),  reduce the values `TIMEOUT` and `ATTEMPTS` in `regression.py`, or comment out ILP as a method in line 80.
* Call `docker compose down` to stop/interrupt the experiment.
* At the end, the folder `data` contains a database with the results and a PDF with the plot.
* To run the experiment for other NIST-levels, change `NIST_LEVEL = 2` in `regression.py`
* To manually use the code, enter the docker container via `docker compose exec regression bash` and just execute the code as desired.

## Local Usage
If in doubt, use the method via docker as described above.

* Install the requirements from `requirements.txt` with any package manager you like, e.g. `pip3 install -r requirements.txt`
* Run `demo.py` with the desired parameters
  * `python3 demo.py --p 0.07 --m 404`  
  creates 404 equations with a contamination rate of 0.07.
    It calls all regressions methods and prints the results.
  * `python3 demo.py --all`  
  starts the full-scale experiment and plots the result. 
    Note that this takes SEVERAL DAYS to finish.

# Simulation of CILWE on Dilithium
The simulation_umts24 file provides the code to generate the Dilithium signatures, simulate a Machine learning Classifier as described by UMTS24 and run the attack with robust regressions. 
Note that this code needs to generate signatures and save them to disk, before the attack can take place.

Sample calls work like this:

* install the requirements with `python3 -m pip install -r requirements.txt`
* for generation:  
  `python3 simulation_umts24.py --experiment generate --filterthresh 9 --threshold 900000 --verbose`
* for soving:  
  `python3 simulation_umts24.py --experiment solve --filterthresh 9 --threshold 900000 --verbose --stepsize 50000`

# Attack on masked Dilithium
The jupyter notebook attack.ipynb and additional scripts in attack/* contain the code to execute the attack against the first-order [masked Dilithium implementation](https://github.com/fragerar/Masked_Dilithium) [CGTZ23] for NIST security levels 2, 3 and 5 as described in the AsiaCrypt paper.
Install dependencies from requirements_attack.txt to run the attack notebook. Within the notebook the [attack data](https://zenodo.org/records/17291471) (power traces, classifier, signature data) as used in the paper may be downloaded to reproduce
the paper's results. Further descriptions are found within the notebook and the helper scripts inside attack.

The target device's firmware, wrapping the attacked `impconvBA64_rec()` function can be found in `attack/firmware/firmware.c`.

The C and C++ code of the data generator is found in attack/data_generator. To compile the dependencies [libnpy](https://github.com/llohse/libnpy) and [masked Dilithium implementation](https://github.com/fragerar/Masked_Dilithium) need to be installed into attack/data_generator/extern, this can be done from within the notebook. Build using cmake for specified security level (DILITHIUM_MODE) by executing `export DILITHIUM_MODE=<2,3,5> && ./attack/data_generator/build.sh`. The output data (format) is described within the notebook (Section 2.1).

# Implementation of Regression Algorithms
We provide our own implementation of the Huber and Cauchy Regression algorithms, which allow for a more fine-grained control than Scikit-Learn or statspy. If you want to use this, please import "irls" from "simulation_umts24/simulation_umts24". The syntax of the method works as follows:
## Inputs
* C: Data matrix or the matrix of all sample stacked together. Needs to have more rows than columns.
* z: A vector / list of all dependent variables, i.e. the obseverd outputs z.
* s: true value for estimator the secret. This is used in order to implement an early stopping if the correct secret is found. Note that this can be set to an arbitrary value if unknown.
* loss: loss function to choose, supports "cauchy" (cauchy loss function) and "huber" (huber loss function).
* iterations: stops after those iterations if it did not converge to the correct solution
* huberparam: if huber loss is used, this is the parameter for the loss function ("delta"). It controls where the quadratic part is transitioned to the linear part. Can contain real values from $]0,\infty[$. The smaller the value is, the less independet errors are assumed (we chose 1/8, default choice for normal distribution is 1.35).

##	Return Values
The function returns two values:
* s_hat: estimated regressor (estimated key for dilithium)
* t: how many iterations have past?

