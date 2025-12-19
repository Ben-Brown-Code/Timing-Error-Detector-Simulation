import numpy as np
import matplotlib.pyplot as plt
import pickle
from SymbolGenerator import SymbolGenerator
from PulseShaper import PulseShaper
from TimingErrorDetector import TimingErrorDetector

seed = 3
np.random.seed(seed) # Reproducibility

SINGLE_RUN = False
SINGLE_RUN_METHOD = 'mueller'
SINGLE_RUN_SNR = 15

COMPARE_RUN = False
MIN_SNR = 1
MAX_SNR = 30
SNR_STEP = 1

SAVE_DATA = False
LOAD_DATA = False
COMPARE_PLOT = False

num_symbols = 100000
sps = 8 # samples per symbol
rc_taps = 101 # raised cosine taps
rolloff = 0.3 # raised cosine rolloff
int_delay = 5
frac_delay = 0.7 # int_delay + frac_delay = total delay in samples
sinc_taps = 21
upsample = 32
is_complex = True

SymbolObj = SymbolGenerator(num_symbols, sps)

if SINGLE_RUN:
    SinglePulseObj = PulseShaper(rc_taps, rolloff, sps, int_delay=int_delay, frac_delay=frac_delay, sinc_taps=sinc_taps, snr=SINGLE_RUN_SNR)
    SinglePulseObj.pulseshaping(SymbolObj.pulse_stream)
    SinglePulseObj.fractionaldelay()
    SinglePulseObj.noise(is_complex=is_complex)

    SingleTED = TimingErrorDetector(upsample)
    SingleTED.interpolator(SinglePulseObj.pulse_shaped_delayed_noise)
    SingleTED.main(len(SinglePulseObj.pulse_shaped_delayed_noise), sps, SINGLE_RUN_METHOD)
    SingleTED.results(SymbolObj.symbol_stream, keep_all=False, print_results=True)
    
    SinglePulseObj.plot_rc()
    SingleTED.plot_interpolated(start_idx = 0, end_idx = 9600, is_complex=False, original=SinglePulseObj.pulse_shaped_delayed_noise)
    SingleTED.plot_final_constellation(SINGLE_RUN_METHOD, keep_all=False)
    SingleTED.plot_offset(SINGLE_RUN_METHOD, sps)

    fig, axs = plt.subplots(2,2)
    SymbolObj.plot_symbols(start_idx = 0, end_idx = 300, axs = axs[0,0])
    SinglePulseObj.plot_pulse_shaped(start_idx = 0, end_idx = 300, axs = axs[0,1])
    SinglePulseObj.plot_pulse_delayed(start_idx = 0, end_idx = 300, with_original=True, axs = axs[1,0])
    SinglePulseObj.plot_pulse_noisy(start_idx = 0, end_idx = 300, is_complex=is_complex, axs = axs[1,1])
    
    plt.show()

if COMPARE_RUN:
    methods = ['mueller', 'gardner', 'earlylategate']
    method_ber = {m: [] for m in methods}
    method_perc_correct = {m: [] for m in methods}
    method_final_offset = {m: [] for m in methods}
    snr_test = np.arange(MIN_SNR, MAX_SNR + 1, SNR_STEP)
    
    PulseObj = PulseShaper(rc_taps, rolloff, sps, int_delay=int_delay, frac_delay=frac_delay, sinc_taps=sinc_taps)
    PulseObj.pulseshaping(SymbolObj.pulse_stream)
    PulseObj.fractionaldelay()
    TED = TimingErrorDetector(upsample)

    iterations = len(methods) * len(snr_test)
    cur_iter = 0
    for snr in snr_test:
        PulseObj.snr = snr
        PulseObj.noise(is_complex=is_complex)

        for method in methods:
            cur_iter += 1
            print(f"Current Iteration: {cur_iter}/{iterations}")
            TED.interpolator(PulseObj.pulse_shaped_delayed_noise)
            TED.main(len(PulseObj.pulse_shaped_delayed_noise), sps, method)
            perc_correct, ber, final_offset = TED.results(SymbolObj.symbol_stream, keep_all=False)
            method_ber[method].append(ber)
            method_perc_correct[method].append(perc_correct)
            method_final_offset[method].append(final_offset)

if SAVE_DATA:
    parameters = {'seed': seed,
                  'num_symbols': num_symbols,
                  'sps': sps,
                  'rc_taps': rc_taps,
                  'rolloff': rolloff,
                  'int_delay': int_delay,
                  'frac_delay': frac_delay,
                  'sinc_taps': sinc_taps,
                  'upsample': upsample,
                  'is_complex': is_complex,
                  'snr': snr_test
                  }

    results_dict = {'parameters': parameters,
                    'ber': method_ber,
                    'perc_correct': method_perc_correct,
                    'final_offset': method_final_offset
                    }

    with open("./TED Simulator/results_dict.pkl", "wb") as f:
        pickle.dump(results_dict, f)

if LOAD_DATA:
    with open("./TED Simulator/results_dict.pkl", "rb") as f:
        results_dict = pickle.load(f)
    method_ber = results_dict['ber']
    snr_test = results_dict['parameters']['snr']

if COMPARE_PLOT:
    plt.figure()
    for key, val in method_ber.items():
        plt.plot(snr_test, val, '--', label=key)
    plt.legend()
    plt.xlabel('SNR (dB)')
    plt.ylabel('BER (%)')
    plt.title('Bit Error Rate (BER) vs. Signal-to-Noise Ratio (SNR)')
    plt.show()