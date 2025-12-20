import numpy as np
import matplotlib.pyplot as plt
import commpy

class PulseShaper:
    def __init__(self, rc_taps: int, rolloff: float, sps: int, int_delay: int | None = None, frac_delay: float | None = None, sinc_taps: int | None = None, snr: float | None = None):
        # rc_taps: number of taps for raised cosine (odd numbered)
        # rolloff: controls raised cosine oscillations towards zero. Larger rolloff, faster rolloff
        # sps: samples per symbol
        # int_delay: integer value of samples to delay pulses
        # frac_delay: decimal value of sampels to delay pulses (0.0, 1.0)
        # sinc_taps: number of taps for sinc used for delay
        # snr: desired signals to noise ratio for noisy signal
        self.rc_taps = rc_taps
        self.rolloff = rolloff
        self.sps = sps
        self.createrc()
        self.int_delay = int_delay
        self.frac_delay = frac_delay
        self.sinc_taps = sinc_taps
        self.snr = snr

    def createrc(self):
        # Returns numpy.ndarray[np.float64] raised cosine, of shape (rc_taps,)
        # Also creates attribute zero_crossings indicating positions the raised cosine crosses the x-axis
        _, raised_cosine = commpy.rcosfilter(self.rc_taps + 1, self.rolloff, self.sps, 1) # Note: Need to do number of taps + 1 and then delete first element to get an odd number of taps with the center element symmetric. No, I don't know why this is the case
        self.raised_cosine = raised_cosine[1:]
        zero_crossings = np.concatenate((np.flip(np.arange(self.rc_taps//2 - self.sps, -1, -self.sps)), np.arange(self.rc_taps//2, self.rc_taps, self.sps))) # Index positions of RC crossing zero and peak
        self.zero_crossings = np.delete(zero_crossings, len(zero_crossings)//2)
        return self.raised_cosine
    
    def pulseshaping(self, pulses: np.ndarray[np.float64], keep_edges: bool = False):
        # Returns numpy.ndarray[np.float64] of pulses convolved with a raised cosine
        # Output shape dependent on keep_edges.
        # If False, discard transient values froms convolution, shape is (len(pulses),)
        # If True, shape is (len(pulses) + rc_taps-1,)
        # pulses: pulse train of symbols
        # keep_edges: indicator of whether to keep extra values from convolution that did not align with center of raised cosine
        self.pulse_shaped = np.convolve(pulses, self.raised_cosine)
        if not keep_edges:
            self.pulse_shaped = self.pulse_shaped[(self.rc_taps - 1) // 2 : -(self.rc_taps - 1) // 2]
        return self.pulse_shaped
    
    def fractionaldelay(self, keep_edges: bool = False):
        # Returns numpy.ndarray[numpy.float64] delayed pulses of shape (pulse_shaped,)
        # Note: Summation of int_delay and frac_delay gives full delay
        # keep_edges: indicator of whether to keep extra values from convolution that did not align with center of sinc
        if self.int_delay:
            pulse_shaped_int_delayed = np.concatenate((np.zeros(self.int_delay), self.pulse_shaped[:-self.int_delay])) # Integer delay, zero padded
        else:
            pulse_shaped_int_delayed = self.pulse_shaped
        
        if self.frac_delay:
            n = np.arange(-(self.sinc_taps-1)//2, self.sinc_taps//2 + 1) #  np.sinc() centers at index 0, so need positive and negative indexes
            sinc_delay = np.sinc(n - self.frac_delay) * np.hamming(self.sinc_taps) # Sinc with sample delay and windowed
            sinc_delay /= np.sum(sinc_delay) # Will maintain signal amplitude
            self.pulse_shaped_delayed = np.convolve(pulse_shaped_int_delayed, sinc_delay)

            if not keep_edges:
                self.pulse_shaped_delayed = self.pulse_shaped_delayed[(self.sinc_taps - 1) // 2 : -(self.sinc_taps - 1) // 2]

        else:
            self.pulse_shaped_delayed = pulse_shaped_int_delayed

        return self.pulse_shaped_delayed

    def noise(self, is_complex: bool = False):
        # Returns numpy.ndarray[numpy.float64] or numpy.ndarray[numpy.complex128] noisy pulses of shape (pulse_shaped_delayed,)
        # is_complex: controls if AWGN is complex valued
        pulse_power = np.mean(self.pulse_shaped_delayed**2)
        variance = pulse_power / (10**(self.snr / 10)) # From SNR in dB, determine AWGN variance = AWGN power
        
        if is_complex:
            s = np.sqrt(variance / 2) * (np.random.randn(len(self.pulse_shaped_delayed)) + 1j * np.random.randn(len(self.pulse_shaped_delayed)))  
        else:
            s = np.random.normal(0, np.sqrt(variance), self.pulse_shaped_delayed.size)
        
        self.pulse_shaped_delayed_noise = self.pulse_shaped_delayed + s

        return self.pulse_shaped_delayed_noise

    def plot_rc(self, axs = None):
        # Visualize raised cosine
        # axs: matplotlib axis object. If included, plots on provided axis
        if axs is not None:
            axs.plot(self.raised_cosine, '.', label='RC')
            axs.plot(self.zero_crossings, np.zeros(len(self.zero_crossings)), 'x', label='Zero Crossings')
            axs.set_xlabel('Samples')
            axs.set_ylabel('Amplitude')
            axs.legend()
            axs.set_title('Raised Cosine Filter')
            axs.grid(True)
        else:
            plt.figure()
            plt.plot(self.raised_cosine, '.', label='RC')
            plt.plot(self.zero_crossings, np.zeros(len(self.zero_crossings)), 'x', label='Zero Crossings')
            plt.xlabel('Samples')
            plt.ylabel('Amplitude')
            plt.legend()
            plt.title('Raised Cosine Filter')
            plt.grid(True)
    
    def plot_pulse_shaped(self, start_idx: int | None = None, end_idx: int | None = None, axs = None):
        # Visualize shaped pulses
        # start_idx: Index of the pulse stream to plot first
        # end_idx: One higher than the index to be plotted last
        # axs: matplotlib axis object. If included, plots on provided axis
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.pulse_shaped)

        if axs is not None:
            axs.plot(self.pulse_shaped[start_idx:end_idx], '.-', label='Pulse Shaped')
            axs.set_xlabel('Samples')
            axs.set_ylabel('Pulse Amplitude')
            axs.legend()
            axs.set_ylim((np.min(self.pulse_shaped[start_idx:end_idx]) - 0.2, np.max(self.pulse_shaped[start_idx:end_idx]) + 0.2))
            axs.set_title('Symbols after Pulse Shaping with RC')
            axs.grid(True)
        else:
            plt.figure()
            plt.plot(self.pulse_shaped[start_idx:end_idx], '.-', label='Pulse Shaped')
            plt.xlabel('Samples')
            plt.ylabel('Pulse Amplitude')
            plt.legend()
            plt.ylim((np.min(self.pulse_shaped[start_idx:end_idx]) - 0.5, np.max(self.pulse_shaped[start_idx:end_idx]) + 0.5))
            plt.title('Symbols after Pulse Shaping with RC')
            plt.grid(True)

    def plot_pulse_delayed(self, start_idx: int | None = None, end_idx: int | None = None, with_original: bool = False, axs = None):
        # Visualize shaped pulses
        # start_idx: Index of the pulse stream to plot first
        # end_idx: One higher than the index to be plotted last
        # with_original: controls if original pulse shaped is also plotted
        # axs: matplotlib axis object. If included, plots on provided axis
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.pulse_shaped_delayed)

        if axs is not None:
            axs.plot(self.pulse_shaped_delayed[start_idx:end_idx], '.-', label='Delayed Pulse')
            if with_original:
                axs.plot(self.pulse_shaped[start_idx:end_idx], '.-', label='Original Pulse')
            axs.set_xlabel('Samples')
            axs.set_ylabel('Pulse Amplitude')
            axs.legend()
            axs.set_ylim((np.min(self.pulse_shaped_delayed[start_idx:end_idx]) - 0.5, np.max(self.pulse_shaped_delayed[start_idx:end_idx]) + 0.5))
            axs.set_title('Fractional Delayed Pulse Shaped Symbols')
            axs.grid(True)
        else:
            plt.figure()
            plt.plot(self.pulse_shaped_delayed[start_idx:end_idx], '.-', label='Delayed Pulse')
            if with_original:
                plt.plot(self.pulse_shaped[start_idx:end_idx], '.-', label='Original Pulse')
            plt.xlabel('Samples')
            plt.ylabel('Pulse Amplitude')
            plt.legend()
            plt.ylim((np.min(self.pulse_shaped_delayed[start_idx:end_idx]) - 0.5, np.max(self.pulse_shaped_delayed[start_idx:end_idx]) + 0.5))
            plt.title('Fractional Delayed Pulse Shaped Symbols')
            plt.grid(True)
    
    def plot_pulse_noisy(self, start_idx: int | None = None, end_idx: int | None = None, with_delayed: bool = False, is_complex: bool = False, axs = None):
        # Visualize noisy pulses
        # start_idx: Index of the pulse stream to plot first
        # end_idx: One higher than the index to be plotted last
        # with_delayed: controls if delayed pulse is also plotted
        # is_complex: controls if the noisy signal is plotted as real and imag values separately
        # axs: matplotlib axis object. If included, plots on provided axis
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.pulse_shaped_delayed_noise)

        if axs is not None:
            if is_complex:
                axs.plot(self.pulse_shaped_delayed_noise[start_idx:end_idx].real, '.-', label='Re{Noisy Delayed Pulse}')
                axs.plot(self.pulse_shaped_delayed_noise[start_idx:end_idx].imag, '.-', label='Im{Noisy Delayed Pulse}')
            else:
                axs.plot(self.pulse_shaped_delayed_noise[start_idx:end_idx], '.-', label='Noisy Delayed Pulse')
            
            if with_delayed:
                axs.plot(self.pulse_shaped_delayed[start_idx:end_idx], '.-', label='Delayed Pulse')

            axs.set_xlabel('Samples')
            axs.set_ylabel('Pulse Amplitude')
            axs.legend()
            axs.set_ylim((np.min(self.pulse_shaped_delayed_noise[start_idx:end_idx].real) - 0.5, np.max(self.pulse_shaped_delayed_noise[start_idx:end_idx].real) + 0.5))
            axs.set_title('Noisy Delayed Pulse Shaped Symbols')
            axs.grid(True)
        else:
            plt.figure()

            if is_complex:
                plt.plot(self.pulse_shaped_delayed_noise[start_idx:end_idx].real, '.-', label='Re{Noisy Delayed Pulse}')
                plt.plot(self.pulse_shaped_delayed_noise[start_idx:end_idx].imag, '.-', label='Im{Noisy Delayed Pulse}')
            else:
                plt.plot(self.pulse_shaped_delayed_noise[start_idx:end_idx], '.-', label='Noisy Delayed Pulse')
            
            if with_delayed:
                plt.plot(self.pulse_shaped_delayed[start_idx:end_idx], '.-', label='Delayed Pulse')

            plt.xlabel('Samples')
            plt.ylabel('Pulse Amplitude')
            plt.legend()
            plt.ylim((np.min(self.pulse_shaped_delayed_noise[start_idx:end_idx].real) - 0.5, np.max(self.pulse_shaped_delayed_noise[start_idx:end_idx].real) + 0.5))
            plt.title('Noisy Delayed Pulse Shaped Symbols')
            plt.grid(True)