'''This file provides the simulation for the attack of UMTS24

This code only works for NIST security level 2 parameters
We recommend generting up to 2* 10^6 signatures to achieve good results.
Recommended setting for solving is threshold = 900000, mininum-signatures = 400000, stepsize = 50000'''

import argparse
import numpy as np
from methods_numpy import irls
from parameters import Parameters
from scipy.linalg import toeplitz
import pickle
import concurrent.futures as concurr
from itertools import product



parser = argparse.ArgumentParser("solving UMTS24 with robust regression")
parser.add_argument("--experiment",type=str, choices=["generate","solve"], default="generate", help="generate samples or solve them")
parser.add_argument("--single_threadded",action="store_true",help="runs this singlethreaded",default=False)
parser.add_argument("--cores",type=int,default=4,help="how many cores to use if multiprocessing")
parser.add_argument("--stepsize",type=int,default=1000)
parser.add_argument("--filepath",type=str,help="filepath to where to save / load from")
parser.add_argument("--filterthresh",type=int,help="sqrt(2tau) * filterthresh for filtering or 39")
parser.add_argument("--repeat",type=int,default=1,help="how many times to repeat the experiment")
parser.add_argument("--threshold",type=int,default=10000,help="how many signatures to generate / process")
parser.add_argument("--verbose",action="store_true",help="prints more output",default=True)

parser.add_argument("--minimum_signatures",type=int,default=400000,help="minimum number of signatures to process")
parser.add_argument("--tpr",type=float,default=0.99,help="true positive rate for Classifier")
parser.add_argument("--fpr",type=float,default=0.01,help="false positive rate for Classifier")
parser.add_argument("--huberparam",type=float,default=0.125,help="huber parameter")
args = parser.parse_args()


############# generate samples #############

def keygen(params: Parameters):
    beta = np.random.choice([-2, -1, 0, 1, 2], (params.l,params.n))
    return beta

def gen_c_np(params: Parameters):
    '''draws the vector c'''
    c_np = np.zeros(params.n)
    non_zero_indices = np.random.choice(params.n, params.tau, replace=False)
    c_np[non_zero_indices] = np.random.choice([-1, 1], params.tau)
    return c_np

def calculate_c_matrix_np(c , params: Parameters):
    """
    Adapted from: https://github.com/KatinkaBou/Probabilistic-Bounds-On-Singular-Values-Of-Rotation-Matrices/blob/c92bfa863fc640ca0c39b321dde1696edf84d467/negacyclic_probabilistic_bound.py#L20
    turn the polynomial into matrix form by using a rotation matrix
    """
    row = np.zeros(c.shape[0], dtype=params.dtype)
    row[0] = c[0]
    row[1:] = -c[-1:0:-1]

    c_matrix = toeplitz(c, row)
    return c_matrix

def filter(C,z,y):
    ''' checks wither some z is less than 2 std deviations away from 0. Keeps only those equations.'''
    mask = np.abs(z) <= FILTER_THRESH
    return C[mask],z[mask],y[mask]

def gen_filter(i):
    """returns: list((C_0,z_0,y_0),(C_1,z_1,y_1),...)"""
    C,z,y = gen_sig(S1,PARAMS)
    eq = list()
    for l in range(PARAMS.l):
        filtered = filter(C,z[l],y[l])
        eq.append(filtered)
    return eq

def gen_sig(s1,params:Parameters):
    C = calculate_c_matrix_np(gen_c_np(params),params)
    rtn_y = list()  
    rtn_z=list()  
    for l in range(params.l):
        y = np.random.randint(params.y_range.start, params.y_range.stop, params.n, dtype=params.dtype)
        mask = [True] # enter the loop. Evaluated with np.any
        while(np.any(mask)):
            z=C@s1[l] +y
            #reject
            mask = np.abs(z) >= (params.gamma_1-params.beta)
            y[mask] = np.random.randint(params.y_range.start,params.y_range.stop,dtype=params.dtype, size= np.count_nonzero(mask) )
        rtn_z.append(z)
        rtn_y.append(y)
    return C,rtn_z,rtn_y

def gen_sig2(s1,params:Parameters):
    C = calculate_c_matrix_np(gen_c_np(params),params)
    rtn_y = list()  
    rtn_z=list()  
    for l in range(params.l):
        mask = [True] # enter the loop. Evaluated with np.any
        while(np.any(mask)):
            y = np.random.randint(params.y_range.start, params.y_range.stop, params.n, dtype=params.dtype)
            z=C@s1[l] +y
            #reject
            mask = (np.abs(z) >= (params.gamma_1 - params.beta))
        rtn_z.append(z)
        rtn_y.append(y)
    return C,rtn_z,rtn_y


############## solve ##############

def process_sigs(data_unbatched,filt,tpr,fpr):
    #output format looks like this. assume that l=4.
    Cs = [[],[],[],[]]
    zs = [[],[],[],[]]
    ys = [[],[],[],[]]
    
    #for sig in itemgetter(*idx)(data_unbatched):
    for sig in data_unbatched:
        for l in range(4):
            Cs[l].append(sig[l][0])
            zs[l].append(sig[l][1])
            ys[l].append(sig[l][2])

    #unify to one matrix
    for l in range(4):
        Cs[l] = np.vstack(Cs[l])
        zs[l] = np.concatenate(zs[l])
        ys[l] = np.concatenate(ys[l])


    #apply fpr and tpr
    CsSel = [[],[],[],[]]
    zsSel = [[],[],[],[]]
    ysSel = [[],[],[],[]]

    #see UMTS24 algorithm 5
    for l in range(4):
        mask = np.zeros_like(ys[l],dtype=bool)
        for i in range(len(ys[l])):
            if ys[l][i] == 0:
                if np.random.random()<tpr:
                    mask[i]=1
            else:
                if np.abs(ys[l][i])< filt and np.random.random()<fpr:
                    mask[i]=1
        CsSel[l]= Cs[l][mask]
        zsSel[l]= zs[l][mask]
        ysSel[l]= ys[l][mask]
    return CsSel,zsSel,ysSel

def log_to_file(file_path, log_string):
    """
    Logs a string to a file. If the file doesn't exist, it will be created.

    :param file_path: Path to the log file.
    :param log_string: The string to log.
    """
    with open(file_path+".csv", 'a') as file:  # Open the file in append mode
        file.write(log_string + '\n')  # Add a newline for each log entry


def no_errors(s,shat):
    '''number of error in estimate'''
    return np.count_nonzero((np.round(shat) -s)!=0)

def load_sigs(i,filepath):
    '''loads signatures and keys to it. Please provide just the stem.'''
    filepath = filepath+str(i)
    with open(filepath+"_key.pkl","rb") as f:
        key = pickle.load(f)

    with open(filepath+".pkl","rb") as f1:
        data = pickle.load(f1)

    #data_unbatched =[sig for batch in data for sig in batch]
    data_unbatched = data
    return data_unbatched , key

def run_attack(PARAMS,CsSel,zsSel,ysSel,S1,methods,repeat,nosigs,filepath,verbose=True):
    for l in range(PARAMS.l):
        for meth in methods:
            if verbose:
                print(meth)
            if meth == "cauchy":
                shat,_ = irls(C=CsSel[l],z=zsSel[l],s=S1[l],loss="cauchy",iterations=30)
            if meth == "huber":
                #solved with irls to make this experiment independent of mosek license.
                shat,_ = irls(C=CsSel[l],z=zsSel[l],s=S1[l],loss="huber",iterations=30,huberparam = HUBER_PARAM)

            #logging results
            if verbose:
                print("log "+meth)
            num_eq = len(zsSel[l])
            true_eq = np.count_nonzero(ysSel[l]==0)
            contamination = (num_eq-true_eq)/num_eq 
            logstring = ",".join(map(str,[repeat,l,nosigs,num_eq,contamination,meth,no_errors(S1[l],shat)]))
            
            log_to_file(filepath,logstring)

######## main ########

if __name__ == '__main__':

    if args.experiment == "generate":
        PARAMS = Parameters.get_nist_security_level(2)
        FILTER_THRESH = args.filterthresh * np.sqrt(2*PARAMS.tau)
        for rep in range(args.repeat):
    
            S1 = keygen(params=PARAMS)
            final_results = list()
            step = range(args.threshold)
            final_results = list(map(gen_filter,step))

            # for i in range(0,args.threshold,args.stepsize):
            #     if args.verbose:
            #         print(rep,i,args.threshold)

            #     step = range(args.stepsize)
            #     if args.single_threadded:
            #         #single threaded for debugging
            #         results = list(map(gen_filter,step))
            #         #[print(r) for r in results]

            #     else:
            #         raise ValueError("fail.")
            #         with concurr.ProcessPoolExecutor(max_workers=args.cores) as executor:
            #             results = list(executor.map(gen_filter,step))

            #     final_results.append(results)

            with open(args.filepath+str(rep)+".pkl","wb") as f1:
                pickle.dump(final_results,f1)
            with open(args.filepath+str(rep)+"_key.pkl","wb") as f2:
                pickle.dump(S1,f2)
    
    if args.experiment == "solve":
        methods = ["cauchy","huber"]
        assert args.minimum_signatures < args.threshold, "need to have at least as many signatures as threshold"
        # recommended parameters for rage are range(400000,900000,50000)

        HUBER_PARAM = args.huberparam
        filepathwrite = args.filepath+"results"+str(args.tpr)+"_"+str(args.fpr)
        log_to_file(filepathwrite,"repeat,l,no_sigs,num_eq,contamination,method,num_errors")    
        print("hello")
        for rep in range(args.repeat):
            ##load sigs
            data_unbatched, s1 = load_sigs(rep,args.filepath)
            print("data loaded")
            for no_sigs in range(args.minimum_signatures,args.threshold+1,args.stepsize):
                if args.verbose:
                    print("rep",rep,"num sigs",no_sigs)

                #write output line wise to file to be crash resistant

                PARAMS = Parameters.get_nist_security_level(2)
                FILTER_THRESH = 2*np.sqrt(2*PARAMS.tau)

                ##unpack sigs to 4 parts
                CsSel,zsSel,ysSel = process_sigs(data_unbatched[:no_sigs],FILTER_THRESH,fpr=args.fpr,tpr=args.tpr)
                #sanity check
                for l in range(PARAMS.l):
                    assert np.all(zsSel[l] == ysSel[l] + CsSel[l]@s1[l]), "something went wrong unpacking the signatures"
                ##recover real key
                ##attack
                run_attack(PARAMS,CsSel,zsSel,ysSel,s1,methods,rep,no_sigs,filepathwrite,verbose=False)

