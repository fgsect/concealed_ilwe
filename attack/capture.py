import chipwhisperer as cw
from helper import *

# Use the CW API to trace the execution of the b2a conversion of 'boolean_shares'.
# If samples < n_samples are received returns array of zeros.
def trace_b2a(scope, target, n_samples, boolean_shares):
    t = np.zeros((n_samples))
    scope.arm()
    target.simpleserial_write('o', bytearray(boolean_shares))
    ret = scope.capture()
    if ret:
        print('Timeout happened during acquisition')
    else:
        t = scope.get_last_trace()[:n_samples]
    return t

# Capture traces of b2a conversion of 'n_y_coeff' random boolean share 
# pairs masking y-coefficients in the range [y_intermediate-y_range, y_intermediate+y_range[. 
# Values < y_intermediate are labeled 0, values >= y_intermediate are labeled 1.
def capture_profiling_traces(scope, y_intermediate=2**17, y_range=16, n_y_coeff=2000):
    target = cw.target(scope, cw.targets.SimpleSerial, flush_on_err=False)
    # Sample 800 to 1200 correspond to the execution of the b2a conversion
    # function bewtween the surrounding nops.
    n_samples = 400
    # 200 cycles of setup function execution including 50 nops.
    scope.adc.offset = 800
    # Number of coefficietns
    n_traces = (y_range*2) * n_y_coeff
    labels = np.zeros(n_traces, dtype=np.uint16)
    traces = np.zeros((n_traces, n_samples))
    boolean_shares = np.zeros(2, dtype=np.uint32)

    label = 0
    coeff_idx = 0
    for y_coeff in tqdm(range(y_intermediate - y_range, (y_intermediate + y_range))):
        if y_coeff == y_intermediate:
            label = 1
        idx = coeff_idx * n_y_coeff
        for i in (range(n_y_coeff)):
            boolean_shares = random_booleanshares(y_coeff, y_intermediate)                
            labels[idx + i] = label
            traces[idx + i] = trace_b2a(scope, target, n_samples, boolean_shares)
        coeff_idx += 1

    return traces, labels

# Capture traces of the b2a conversin of boolean_shares.
# Values < y_intermediate are labeled 0, values >= y_intermediate are labeled 1.
def capture_attack_traces(scope, boolean_shares, y_intermediate=2**17):
    target = cw.target(scope, cw.targets.SimpleSerial, flush_on_err=False)
    # Sample 800 to 1200 correspond to the execution of the b2a conversion
    # function bewtween the surrounding nops.
    n_samples = 400
    # 200 cycles of setup function execution including 50 nops.
    scope.adc.offset = 800
    
    n = len(boolean_shares)
    labels = np.zeros((n))
    traces = np.zeros((n, n_samples))
         
    for i in tqdm(range(n)):
        y_coeff = boolean_shares[i][0] ^ boolean_shares[i][1]
        labels[i] = (y_coeff >= y_intermediate)
        traces[i] = trace_b2a(scope, target, n_samples, boolean_shares[i])

    return traces, labels
