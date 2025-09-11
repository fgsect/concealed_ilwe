Solving Concealed Integer LWE with Robust Regressions
===

This is Code for the AsiaCrypt paper (Damm et al., AsiaCrypt 2025).

# Installation/Usage
The experiment was originally run with [Mosek](https://www.mosek.com/) as a solver. This solver is commercial, but offers free academic licences.
We included a version with free solvers, that may yields slightly different results.

## Docker
* OPTIONAL: ensure that your Mosek licence is in the folder `~/mosek`, or adjust the `docker-compose.yml`
* call `docker compose up --build -d` to start/resume the large scale experiment for NIST-level 2
  Note that this takes SEVERAL DAYS to finish.
* call `docker compose down` to stop/interrupt the experiment
* at the end, the folder `data` contains a database with the results and a PDF with the plot
* to run the experiment for other NIST-levels, change `NIST_LEVEL = 2` in `regression.py`
* to manually use the code, enter the docker container via `docker compose exec regression bash` and just execute the code as desired

## Locally
* install the requirements with any package manager you like. 
* run `demo.py` with the desired parameters
  * `python3 demo.py --p 0.07 --m 404` crates 404 equations with a contamination rate of 0.07.
    It calls all regressions methods and prints the results.
  * `python3 demo.py --all` starts the full-scale experiment and plots the result. 
    Note that this takes SEVERAL DAYS to finish.

# Included Methods
* Huber regression
* Cauchy regression/Iterative Reweighted Least Squares
* Ordinary least squares (OLS, L2-norm)
* Least absolute deviation (LAD, L1-norm)
* Integer linear programming (ILP)

# Simulation of full attack
The simulation_umts24 file provides the code to generate the Dilithium signatures, simulate a Machine learning Classifier as described by UMTS24 and run the attack with robust regressions. 
Note that this code needs to generate signatures and save them to disk, before the attack can take place.
