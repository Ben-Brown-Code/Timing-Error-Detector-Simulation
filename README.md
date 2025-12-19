# Timing Error Detector Simulation
This repository provides Python code simulating three timing error detectors (TED): Mueller and Muller (M&M), Gardner, and Early-Late Gate. The simulation recovers the timing offset of a noisy, delayed signal that has been digitally modulated using Binary Phase-Shift Keying (BPSK). The purpose of this simulation is to ultimately compare the performance of the TED, mainly using a Bit Error Rate (BER) vs. Signal-to-Noise (SNR) ratio curve to demonstrate robustness of the TED to noise. Furthermore, the code is modular and many of the parameters can be changed to simulate different TED scenarios. The rest of this repository will cover the background. simulation, and results. If someone desires to skip straight to the code, `testbench.py` is main file to run and edit parameters from.

## Background
Once a carrier signal is received and downconverted to baseband, such as through the use of a local oscillator (LO), an analog-to-digital converter (ADC) samples and quantizes it into a digital message signal. At this stage, there are usually two main issues with the signal: noise, and offsets. The noise is usually handled via filtering, which can occur prior to the ADC or after, and aims to maximize the SNR. The offsets are either time or frequency based, where frequency offsets can occur due to LO mistmatches. Timing offsets, the focus of this work, are when the samples we select from the digital signal are misaligned with the ideal positions. When the carrier travels through the air, this takes some amount of time, andit  may experience reflections which all contribute to delay in the signal at arrival time. Therefore, to recover the optimal samples from the message signal, a TED must be used to correct this time delay/offset.

The process for finding this timing offset stays the same for the different TED. First, the digital signal is upsampled so there are more sampels to work with. This allows better resolution for correcting fractional offsets. For example, if our received signal was delayed by 3.7 samples, then at the current sample resolution we'd have to round to a 4 sample offset. However, if we upsample, there are now more samples to choose from in between 3 and 4 which brings us closer to the 3.7 fractional offset.

Next we enter the iterative loop to converge to the correct offset. At the start of every iteration, some currently chosen offset must be applied to select a value from the upsampled signal. This chosen offset updates each loop and should eventually reach an optimal solution. Then, depending on the TED chosen, an error term is calculated, proportionally indicating how far off the current offset is from the ideal offset. This error term is then used to update to a new offset, and the loop repeats itself.

## Simulation
There are two modes that can be ran in the simulation from `testbench.py`: single run, and compare run. Single run mode will generate one BPSK signal and perform the TED loop for one specified method. This is controlled by `SINGLE_RUN` and `SINGLE_RUN_METHOD`. Compare run will generate one BPSK signal, but perform the TED loop for all methods across a range of SNR. This is controlled by `COMPARE_RUN`, `MIN_SNR`, `MAX_SNR`, and `SNR_STEP`. Furthermore, if you want to save or load the results of the compare run, you can use `SAVE_DATA` and `LOAD_DATA`, respectively.

Here I will walk through a single run using the M&M TED to demonstrate the simulation process. So, I set `SINGLE_RUN = False`, `SINGLE_RUN_METHOD = 'mueller'`,  `SINGLE_RUN_SNR = 15`, and the parameters as follows:
```
num_symbols = 100000
sps = 8 # samples per symbol
rc_taps = 101 # raised cosine taps
rolloff = 0.3 # raised cosine rolloff
int_delay = 5
frac_delay = 0.7 # int_delay + frac_delay = total delay in samples
sinc_taps = 21
upsample = 32
is_complex = True
```





