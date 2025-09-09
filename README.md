# Solving Concealed Integer LWE with Robust Regressions

This is Code for the AsiaCrypt paper (Damm et al., AsiaCrypt 2025).

## Install
please install the requirements with any package manager you like. To run this code, Mosek is required as a solver, which requires a license. Please follow the official webset on how to install it.

## Run
The demo file creates one sample an runs it. Methods_numpy contains methods for sampling CILWE instances and solving them with Iterative Reweighted Least Squares (Huber Regression and Cauchy Regression provided). Methods_mosek provides faster Code for the Huber Regression and ILP code.

The simulation_umts24 file provides the code to generate the Dilithium signatures, simulate a Machine learning Classifier as described by UMTS24 and run the attack with robust regressions. Note that this code needs to generate signatures and safe them to disk, before the attack can take place.
