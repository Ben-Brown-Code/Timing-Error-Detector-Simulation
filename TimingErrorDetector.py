import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import resample_poly

class TimingErrorDetector:
    def __init__(self, upsample: int):
        # upsample: upscaling factor of interpolation
        self.upsample = upsample

    def interpolator(self, signal: np.ndarray[np.float64] | np.ndarray[np.complex128]):
        # Returns numpy.ndarray[numpy.float64] or numpy.ndarray[numpy.complex128] upsampled signal of shape (len(signal)*upsample,)
        # signal: array to be upsampled
        upsample = 32
        self.interpolated_pulse = resample_poly(signal, upsample, 1) # upsample * sps = new number of samples per symbol
        return self.interpolated_pulse

    @staticmethod
    def mueller_muller(val_cur: np.float64 | np.complex128, val_prev: np.float64 | np.complex128, symbol_prev: np.float64):
        # Returns numpy.float64 error using Mueller and Muller method
        # val_cur: interpolated value at current offset
        # val_prev: interpolated value one symbol period before current offset
        # symbol_prev: decided symbol value one symbol period before current offset
        symbol_cur = np.sign(np.real(val_cur))
        error = np.real((val_cur * np.conj(symbol_prev)) - (symbol_cur * np.conj(val_prev)))
        return error
    
    @staticmethod
    def gardner(val_cur: np.float64 | np.complex128, val_prev: np.float64 | np.complex128, val_middle: np.float64 | np.complex128):
        # Returns numpy.float64 error using Gardner method
        # val_cur: interpolated value at current offset
        # val_prev: interpolated value one symbol period before current offset
        # val_middle: interpolated value half a symbol period before current offset
        error = np.real(np.conj(val_middle)*(val_cur - val_prev))
        return error

    @staticmethod
    def earlylategate(val_early: np.float64 | np.complex128, val_late: np.float64 | np.complex128):
        # Returns numpy.float64 error using Early-Late Gate method
        # val_early: interpolated value at current offset minus a small shift
        # val_late: interpolated value at current offset plus a small shift
        error = np.abs(val_early)**2 - np.abs(val_late)
        return error

    def main(self, num_samples: int, sps: int, error_eq: str, tau: float = 0.0, gain: float = 0.1, Kp: float = 0.01, Ki: float = 0.0001, delta: int = 4, symbol_prev: int | np.float64 = 0, use_pi: bool = False):
        # Main timing error detector loop
        # num_samples: length of the signal prior to interpolation
        # sps: samples per symbol
        # error_eq: selection of the error equation. Choose from ['mueller', 'gardner', 'earlylategate]
        # tau: offset (in samples)
        # gain: loop filter gain
        # Kp: proportional gain
        # Ki: integral gain
        # delta: inverse multiplicative factor for early late gate shift. Used as sps / delta = shift
        # symbol_prev: first decided symbol, used as initial condition
        # use_pi: controls if the error is updated using the proportional integral method. Default is loop fitler gain, not PI
        i_cur = sps
        error = [] # Track error
        offset = [] # Track offset
        symbols_pred = [symbol_prev] # Track predicted symbols, first guess is technically symbol_prev, but that's just used as an initial condition
        out_signal = [self.interpolated_pulse[0]] # Store interpolated signal values as sampling aligns. First value will be first inerpolated signal value
        
        if use_pi:
            v = 0.0

        while i_cur < num_samples:
            offset_cur = i_cur*self.upsample + int(tau*self.upsample) # Multiply by upsample to put in index units of the interpolated signal. Round offset tau to nearest integer index
            val_cur = self.interpolated_pulse[offset_cur] # Raw value
            val_prev = self.interpolated_pulse[offset_cur - sps*self.upsample] # Raw value one symbol period before the current one

            if error_eq == 'mueller':
                error.append(self.mueller_muller(val_cur, val_prev, symbol_prev))
            elif error_eq == 'gardner':
                val_middle = self.interpolated_pulse[offset_cur - int(sps*self.upsample/2)]
                error.append(-self.gardner(val_cur, val_prev, val_middle)) # Note: Using negative error here to keep consistent with tau += instead of tau -=
            elif error_eq == 'earlylategate':
                shift = int((sps / delta) * self.upsample)
                if offset_cur + shift > len(self.interpolated_pulse):
                    error.append(error[-1]) # Not enough samples, repeat last error value to avoid distorting result
                else:
                    val_early = self.interpolated_pulse[offset_cur - shift]
                    val_late = self.interpolated_pulse[offset_cur + shift]
                    error.append(-self.earlylategate(val_early, val_late)) # Note: Using negative error here to keep consistent with tau += instead of tau -=


            symbol_prev = np.sign(np.real(val_cur)) # Makes symbol decision, converts raw values to +1 or -1
            symbols_pred.append(symbol_prev)

            if use_pi:
                v += (Ki * error[-1])
                tau += v + Kp * error[-1]
            else:
                tau += gain*error[-1]

            tau %= sps # Constrains tau to be between 0 and sps
            offset.append(tau)
            i_cur += sps # Move forward one sample period for next iteration
            out_signal.append(val_cur)

        self.offset = offset
        self.error = error
        self.symbols_pred = symbols_pred
        self.out_signal = out_signal

        return offset, error, symbols_pred, out_signal

    def results(self, symbols: np.ndarray[np.int64], keep_all: bool = True, print_results: bool = False):
        # Return and/or print statistics of previously ran TED algorithm
        # symbols: original sequence of symbols
        # keep_all: if false, skip the first 30 predicted symbols, considered as a preamble for bit syncing
        # print_results: if true, format print the statistics
        if keep_all:
            num_correct = np.sum(np.array(self.symbols_pred) == symbols)
            num_symbols = len(symbols)
        else:
            num_correct = np.sum(np.array(self.symbols_pred[30:]) == symbols[30:])
            num_symbols = len(symbols[30:])

        perc_correct = (num_correct / num_symbols)*100
        ber = (num_symbols - num_correct) / num_symbols * 100
        final_offset = self.offset[-1]

        if print_results:
            print(f"Correct Symbol Predictions: {num_correct}/{num_symbols} -> {num_correct/num_symbols*100:.2f}%")
            print(f"BER: {(num_symbols - num_correct)/num_symbols*100:.8f}%")
            print(f"Final Offset in Samples: {self.offset[-1]:.1f}")
        
        return perc_correct, ber, final_offset

    def plot_interpolated(self, start_idx: int | None = None, end_idx: int | None = None, is_complex: bool = False, original: np.ndarray[np.float64] | np.ndarray[np.complex128] | None = None, axs = None):
        # Visualize shaped pulses
        # start_idx: index of the pulse stream to plot first
        # end_idx: one higher than the index to be plotted last
        # is_complex: controls if the noisy signal is plotted as real and imag values separately
        # original: signal prior to upsampling
        # axs: matplotlib axis object. If included, plots on provided axis
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.interpolated_pulse)

        if original is not None:
                check = start_idx % self.upsample
                original_indexes = np.arange(0-check, end_idx-start_idx, self.upsample)

        if axs is not None:
            if is_complex:
                axs.plot(self.interpolated_pulse[start_idx:end_idx].real, '.', label='Re{Interpolated Pulses}')
                axs.plot(self.interpolated_pulse[start_idx:end_idx].imag, '.', label='Im{Interpolated Pulses}')

                if original is not None:
                    axs.plot(original_indexes[original_indexes>=0], original[-(-start_idx//self.upsample):(end_idx-1)//self.upsample + 1].real, '.', label='Re{Original Pulses}')
                    axs.plot(original_indexes[original_indexes>=0], original[-(-start_idx//self.upsample):(end_idx-1)//self.upsample + 1].imag, '.', label='Im{Original Pulses}')

            else:
                axs.plot(self.interpolated_pulse[start_idx:end_idx], '.', label='Interpolated Pulses')

                if original is not None:
                    axs.plot(original_indexes[original_indexes>=0], original[-(-start_idx//self.upsample):(end_idx-1)//self.upsample + 1], '.', label='Original Pulses')

            axs.set_xlabel('Samples')
            axs.set_ylabel('Pulse Amplitude')
            axs.legend()
            axs.set_title('Upsampled Pulse Shaped Symbols')
            axs.grid(True)
        else:
            plt.figure()

            if is_complex:
                plt.plot(self.interpolated_pulse[start_idx:end_idx].real, '.', label='Re{Interpolated Pulses}')
                plt.plot(self.interpolated_pulse[start_idx:end_idx].imag, '.', label='Im{Interpolated Pulses}')

                if original is not None:
                    plt.plot(original_indexes[original_indexes>=0], original[-(-start_idx//self.upsample):(end_idx-1)//self.upsample + 1].real, '.', label='Re{Original Pulses}')
                    plt.plot(original_indexes[original_indexes>=0], original[-(-start_idx//self.upsample):(end_idx-1)//self.upsample + 1].imag, '.', label='Im{Original Pulses}')

            else:
                plt.plot(self.interpolated_pulse[start_idx:end_idx], '.', label='Interpolated Pulses')

                if original is not None:
                    plt.plot(original_indexes[original_indexes>=0], original[-(-start_idx//self.upsample):(end_idx-1)//self.upsample + 1], '.', label='Original Pulses')

        plt.xlabel('Samples')
        plt.ylabel('Pulse Amplitude')
        plt.legend()
        plt.title('Upsampled Pulse Shaped Symbols')
        plt.grid(True)
    
    def plot_final_constellation(self, error_eq: str, keep_all: bool = True, axs = None):
        # Visualize I/Q constellation across TED iterations
        # error_eq: selection of the error equation. Choose from ['mueller', 'gardner', 'earlylategate]
        # keep_all: if false, skip the first 30 predicted symbols, considered as a preamble for bit syncing
        # axs: matplotlib axis object. If included, plots on provided axis
        if error_eq == 'mueller':
            title = 'I/Q Constellation using Mueller and Muller'
        elif error_eq == 'gardner':
            title = 'I/Q Constellation using Gardner'
        elif error_eq == 'earlylategate':
            title = 'I/Q Constellation using Early-Late Gate'
        
        if axs is not None:
            if keep_all:
                axs.plot(np.real(self.out_signal), np.imag(self.out_signal), '.', label='IQ Samples')
            else:
                if len(self.out_signal) < 100:
                    raise Exception("Number of symbols must be at least 100 in order to set keep_all to False")
                axs.plot(np.real(self.out_signal[30:]), np.imag(self.out_signal[30:]), '.', label='IQ Samples')

            axs.set_xlabel('I')
            axs.set_ylabel('Q')
            axs.legend()
            axs.set_xlim((np.real(self.out_signal).min() - 0.2, np.real(self.out_signal).max() + 0.2))
            axs.set_ylim((np.imag(self.out_signal).min() - 0.2, np.imag(self.out_signal).max() + 0.2))
            axs.set_title(title)
            axs.grid(True)
        else:
            plt.figure()

            if keep_all:
                plt.plot(np.real(self.out_signal), np.imag(self.out_signal), '.', label='IQ Samples')
            else:
                if len(self.out_signal) < 100:
                    raise Exception("Number of symbols must be at least 100 in order to set keep_all to False")
                plt.plot(np.real(self.out_signal[30:]), np.imag(self.out_signal[30:]), '.', label='IQ Samples')

            plt.xlabel('I')
            plt.ylabel('Q')
            plt.legend()
            plt.xlim((np.real(self.out_signal).min() - 0.2, np.real(self.out_signal).max() + 0.2))
            plt.ylim((np.imag(self.out_signal).min() - 0.2, np.imag(self.out_signal).max() + 0.2))
            plt.title(title)
            plt.grid(True)

    def plot_offset(self, error_eq: str, sps: int, start_idx: int | None = None, end_idx: int | None = None, axs = None):
        # Visualize offset value per iteration
        # error_eq: selection of the error equation. Choose from ['mueller', 'gardner', 'earlylategate]
        # sps: samples per symbol, sets the y-limit
        # start_idx: index of the pulse stream to plot first
        # end_idx: one higher than the index to be plotted last
        # axs: matplotlib axis object. If included, plots on provided axis
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.offset)

        if error_eq == 'mueller':
            title = 'Offset Convergence using Mueller and Muller'
        elif error_eq == 'gardner':
            title = 'Offset Convergence using Gardner'
        elif error_eq == 'earlylategate':
            title = 'Offset Convergence using Early-Late Gate'

        if axs is not None:
            axs.plot(self.offset[start_idx:end_idx], '.', label='Offset')
            axs.set_xlabel('Iteration')
            axs.set_ylabel('Offset (Fractional Samples)')
            axs.set_ylim((0,sps))
            axs.legend()
            axs.set_title(title)
            axs.grid(True)
        else:
            plt.figure()
            plt.plot(self.offset[start_idx:end_idx], '.', label='Offset')
            plt.xlabel('Iteration')
            plt.ylabel('Offset (Fractional Samples)')
            plt.ylim((0,sps))
            plt.legend()
            plt.title(title)
            plt.grid(True)

