import os
import pickle
import random

import matplotlib.pyplot as plt 
import numpy as np 
import tensorflow as tf
import tensorflow.keras as keras

from tensorflow.keras.metrics import Precision, Recall
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense
from tensorflow.keras.activations import relu
from tensorflow.python.ops.numpy_ops import np_config
np_config.enable_numpy_behavior()

from tqdm import tqdm

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from scalib.preprocessing import Quantizer
from scalib.metrics import Ttest, SNR

# Ttest, Power Trace and SNR analysis and plot for input 'traces' and corresponding 'labels'
def analyse_traces(traces, labels):
    n_shares = 2
    n_traces = len(traces)
    n_samples = len(traces[1])

    trace_class_0 = np.zeros((n_traces, n_samples), dtype=np.int16) 
    trace_class_1 = np.zeros((n_traces, n_samples), dtype=np.int16)

    # Mean of power trace groups y<0 and y>=0
    trace_class_0 = np.mean(traces[labels == 0], axis=0)
    trace_class_1 = np.mean(traces[labels == 1], axis=0)
    
    #T-test
    quantizer = Quantizer.fit(traces)
    quantized_traces = quantizer.quantize(traces)
    
    ttest = Ttest(d=1)
    ttest.fit_u(quantized_traces, labels)
    t_univariate = ttest.get_ttest()

    # SNR
    label_snr = labels.reshape(n_traces,1)
    snrobj = SNR(2, use_64bit=True)
    snrobj.fit_u(quantized_traces.astype(np.int16),label_snr.astype(np.uint16))
    snr_val = snrobj.get_snr()[0]

    # T-ritical value of +-4 (p-value < 0.00001)
    upper_threshold=np.zeros(24_000,dtype=np.int16)
    lower_threshold=np.zeros(24_000,dtype=np.int16)
    for i in range(24_000):
        upper_threshold[i] = 4
        lower_threshold[i] = -4
    
    # Create a grid of subplots with 2 rows and 1 column
    fig, axs = plt.subplots(3, 1, figsize=(10, 10))

    axs[0].plot(t_univariate[0], color='red', label='Univariate t-Test')
    axs[0].plot(upper_threshold[:n_samples], color='blue')  
    axs[0].plot(lower_threshold[:n_samples], color='blue') 

    axs[1].plot(trace_class_0, color='blue', label='mean power trace for y<0')
    axs[1].plot(trace_class_1, color='red', label='mean power trace for y>=0')

    axs[2].plot(snr_val, color='red')

    axs[2].set_title('SNR')
    axs[1].set_title('Power traces as a reference')
    axs[0].set_title(f'Univariate t-Test - {n_shares} Shares {n_traces} traces for groups y<0 and y>=0')

    axs[0].legend()
    axs[1].legend()
    
    # Show the plot
    plt.show()

    return trace_class_0, trace_class_1, snr_val, t_univariate[0]

# Return two random booleanshares masking the specified value 'y_coeff'
# in gamma_1 max range y_intermediate*2 = (2: 2**18, 3: 2**20, 5: 2**20).
def random_booleanshares(y_coeff, y_intermediate):
    n_shares = 2
    tmp = np.zeros(n_shares, dtype=np.uint32)
    for i in range(n_shares - 1):
        tmp[i] = (np.random.randint(np.iinfo(np.uint32).max, dtype=np.uint32)) % (y_intermediate*2)
        tmp[n_shares - 1] ^= tmp[i]
    tmp[n_shares - 1] ^= y_coeff
    return tmp

# Use 'classifier' to predict labels of 'traces', evaluate for decision
# threshold of 'threshold' if prediction matches 'labels'.
def predict(classifier, traces, labels, threshold=0.5):
    prediction = (classifier.predict(traces).flatten() > threshold).astype(int)
    
    tp = 0
    fp = 0
    fn = 0
    tn = 0
    for i in range(len(labels)):
        if labels[i] == 1:
            if prediction[i] == 1:
                tp += 1
            else:
                fn += 1
        else:
            if prediction[i] == 0:
                tn += 1
            else:
                fp += 1

    acc = (tp+tn)/ (tp+tn+fp+fn)
    prec = (tp)/ (tp+fp)
    fpr = (fp)/ (tn+fp)
    tpr = (tp)/ (tp+fn)

    print(f"TP: {tp} FP: {fp} TN: {tn} FN: {fn}")
    print(f"Accuracy: {acc}")
    print(f"Precision: {prec}")
    print(f"TPR: {tpr}")
    print(f"FPR: {fpr}")

    return prediction
