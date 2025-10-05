Solving Concealed ILWE and its Application for Breaking Masked Dilithium
===

The paper will be published as AsiaCrypt 2025. 

The paper and BibTex is available at https://eprint.iacr.org/2025/1629

# Installation/Usage
The experiment was originally run with [Mosek](https://www.mosek.com/) as a solver. This solver is commercial, but offers free academic licences.
We included a version with free solvers, that may yield slightly different results.

## Docker
* OPTIONAL: ensure that your Mosek licence is in the folder `~/mosek`, or adjust the `docker-compose.yml`
* Call `docker compose up --build -d` to start/resume the large scale experiment for NIST-level 2.  
  Note that this takes SEVERAL DAYS to finish.
* Call `docker compose down` to stop/interrupt the experiment.
* At the end, the folder `data` contains a database with the results and a PDF with the plot.
* To run the experiment for other NIST-levels, change `NIST_LEVEL = 2` in `regression.py`
* To manually use the code, enter the docker container via `docker compose exec regression bash` and just execute the code as desired.

## Locally
* Install the requirements with any package manager you like. 
* Run `demo.py` with the desired parameters
  * `python3 demo.py --p 0.07 --m 404`  
  creates 404 equations with a contamination rate of 0.07.
    It calls all regressions methods and prints the results.
  * `python3 demo.py --all`  
  starts the full-scale experiment and plots the result. 
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

Sample calls work like this:

for generation:  
`python3 simulation_umts24.py --experiment generate --filterthresh 9 --threshold 900000 --verbose`

for soving:  
`python3 simulation_umts24.py --experiment solve --filterthresh 9 --threshold 900000 --verbose --stepsize 50000`

# Attack on masked Dilithium
The jupyter notebook attack.ipynb contains the code to execute the attack against the first-order [masked Dilithium implementation](https://github.com/fragerar/Masked_Dilithium) [CGTZ23] for NIST security levels 2, 3 and 5 as described in the AsiaCrypt paper.
Install dependencies from requirements_attack.txt to run the attack notebook. Within the notebook the attack data (power traces, classifier, signature data) as used in the paper may be downloaded to reproduce
the paper's results. Further descriptions are found within the notebook and the helper scripts inside attack.

The target device's firmware, wrapping the attacked impconvBA64_rec() function can be found in attack/firmware/firmware.c.

The C and C++ code of the data generator is found in attack/data_generator. To compile the dependencies [libnpy](https://github.com/llohse/libnpy) and [masked Dilithium implementation](https://github.com/fragerar/Masked_Dilithium) need to be installed into attack/data_generator/extern, this can be done from within the notebook. Build using cmake for specified security level (DILITHIUM_MODE) by executing `export DILITHIUM_MODE=<2,3,5> && ./attack/data_generator/build.sh`. The output data (format) is described within the notebook (Section 4).

