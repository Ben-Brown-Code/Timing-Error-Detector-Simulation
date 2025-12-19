import numpy as np
import matplotlib.pyplot as plt

class SymbolGenerator:
    def __init__(self, num_symbols: int, sps: int):
        # num_symbols: number of symbols
        # sps: samples per symbol
        self.num_symbols = num_symbols
        self.sps = sps
        self.symbolstream()
        self.pulsestream()
    
    def symbolstream(self):
        # Returns numpy.ndarray[numpy.int64] of random BPSK symbol stream {-1,+1} of shape (num_symbols,)
        # Also defines attribute bit_stream, the binary version of symbol_stream
        self.symbol_stream = np.random.choice([-1, 1], size=self.num_symbols)
        self.bit_stream = (self.symbol_stream > 0).astype(int)
        return self.symbol_stream
    
    def pulsestream(self):
        # Returns numpy.ndarray[numpy.float64] of symbol pulses with sps-1 zeros between them, of shape (num_symbols*sps,)
        pulses = np.zeros(self.num_symbols * self.sps)
        pulses[::self.sps] = self.symbol_stream
        self.pulse_stream = pulses
        return pulses
    
    def plot_symbols(self, start_idx: int | None = None, end_idx: int | None = None, axs = None):
        # Visualize symbols and binary pattern
        # start_idx: Index of the pulse stream to plot first
        # end_idx: One higher than the index to be plotted last
        # axs: matplotlib axis object. If included, plots on provided axis
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(self.pulse_stream)
        
        if axs is not None:
            axs.plot(self.pulse_stream[start_idx:end_idx], '.-', label='Pulses')
            check = start_idx % self.sps
            bit_indexes = np.arange(0-check, end_idx-start_idx, self.sps)
            axs.plot(bit_indexes[bit_indexes>=0], self.bit_stream[-(-start_idx//self.sps):(end_idx-1)//self.sps + 1], 'x', label='Bits')
            axs.set_ylim((-1.2,1.2))
            axs.set_xlabel('Samples')
            axs.set_ylabel('Symbol/Bit Value')
            axs.legend()
            axs.set_title('Symbols Pulse Train with Corresponding Bits')
        else:
            plt.figure()
            plt.plot(self.pulse_stream[start_idx:end_idx], '.-', label='Pulses')
            check = start_idx % self.sps
            bit_indexes = np.arange(0-check, end_idx-start_idx, self.sps)
            plt.plot(bit_indexes[bit_indexes>=0], self.bit_stream[-(-start_idx//self.sps):(end_idx-1)//self.sps + 1], 'x', label='Bits')
            plt.ylim((-1.2,1.2))
            plt.xlabel('Samples')
            plt.ylabel('Symbol/Bit Value')
            plt.legend()
            plt.title('Symbols Pulse Train with Corresponding Bits')

