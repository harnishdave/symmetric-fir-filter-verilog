"""
FIR Filter Reference Model & Verification Script
Generates input stimuli for Verilog simulation and plots results.

Symmetry explanation:
    The 6 stored coefficients [6,12,22,30,34,24] are HALF the filter.
    The full 12-tap symmetric filter is [6,12,22,30,34,24,24,34,30,22,12,6].
    The Verilog exploits symmetry: it adds tap pairs (x[0]+x[11], x[1]+x[10],
    ...) then multiplies each sum by one coefficient — half the multipliers,
    same result.

DC gain:
    sum([6,12,22,30,34,24,24,34,30,22,12,6]) = 256 = 2^8
    Verilog output amplitude = 256 x input amplitude.
    Python plots divide by DC_GAIN to match input scale visually.
    Verilog uses >>> 8 (right shift) to recover input scale exactly.

Command line Usage:
    python gen_noisy_sig.py            # generate files + plot
    python gen_noisy_sig.py --compare  # also compare with Verilog output
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt

# Filter definition
# Half the symmetric filter — these are the 6 values stored in Verilog
COEFF_INT  = np.array([6, 12, 22, 30, 34, 24], dtype=np.int32)

# Full 12-tap symmetric filter used for convolution
FULL_COEFF = np.concatenate([COEFF_INT, COEFF_INT[::-1]])

# DC gain = sum of all 12 coefficients = 256 = 2^8
DC_GAIN    = int(np.sum(FULL_COEFF))

# Input scaling: signal occupies most of 12-bit range with noise headroom
SCALE      = 2000   # max clean signal amplitude (12-bit range is +-2048)

COEFF_LOAD_LATENCY = 4

# Signal generators

def gen_signal(signal_type, t, freq):
    """Generate a normalised [-1, 1] signal of given type and frequency."""
    period = 1.0 / freq
    if signal_type == 'sine':
        return np.sin(2 * np.pi * freq * t)
    elif signal_type == 'square':
        return np.sign(np.sin(2 * np.pi * freq * t))
    elif signal_type == 'cos':
        return np.cos(2 * np.pi * freq * t)
    elif signal_type == 'triangle':
        return 2 * np.abs(2 * (t / period - np.floor(t / period + 0.5))) - 1
    elif signal_type == 'sawtooth':
        return 2 * (t * freq - np.floor(0.5 + t * freq))
    elif signal_type == 'pulse':
        return np.where((t * freq) % 1.0 < 0.3, 1.0, -1.0)
    elif signal_type == 'chirp':
        f0, f1 = 1, 20
        return np.sin(2 * np.pi * (f0 * t + ((f1 - f0) / 2) * t ** 2))
    else:
        raise ValueError(f"Unknown signal type '{signal_type}'. "
                         f"Choose: sine, square, cos, triangle, sawtooth, pulse, chirp")


# Fixed-point conversion

def to_fixed12(signal_float):
    """
    Scale a float [-1, 1] signal to 12-bit signed integers [-2048, 2047].
    Uses SCALE=2000 to leave headroom for noise without clipping clean signal.
    """
    scaled = (signal_float * SCALE).astype(np.int32)
    return np.clip(scaled, -2048, 2047).astype(np.int16)


# File I/O
def save_hex(signal_int, filename):
    """
    Save integer samples as 3-digit 12-bit 2's complement hex, one per line.
    Negative values are stored as their 12-bit 2's complement representation.
    The Verilog testbench reads these with $fscanf(..., "%h", noisy_signal).
    """
    with open(filename, 'w') as f:
        for v in signal_int:
            f.write(f"{int(v) & 0xFFF:03x}\n")

def save_coeffs(filename="coeff_val.txt"):
    """Save the 6 integer coefficients, one per line (decimal)."""
    with open(filename, 'w') as f:
        for c in COEFF_INT:
            f.write(f"{int(c)}\n")


# Reference filter — matches Verilog integer arithmetic exactly
def apply_filter_causal(signal_int):
    """
    Apply the 12-tap symmetric FIR filter using integer arithmetic.

    Uses numpy.convolve with mode='full' — causal, matches Verilog behaviour.
    Output length = len(signal) + len(FULL_COEFF) - 1.
    Output amplitude = DC_GAIN x input amplitude (no normalization — same as Verilog).

    First len(FULL_COEFF)-1 = 11 output samples are startup transients
    (delay line not yet full), matching Verilog's delay-line fill period.
    """
    return np.convolve(signal_int.astype(np.int64), FULL_COEFF, mode='full')


# Verilog output comparison
def compare_with_verilog(filtered_int, verilog_file="filtered_signal.txt",
                          pipeline_latency=3, delay_line_depth=12):
    try:
        verilog_out = np.loadtxt(verilog_file, dtype=np.int64)
    except FileNotFoundError:
        print(f"[WARN] '{verilog_file}' not found — run Verilog simulation first.")
        return

    # Offset = len(FULL_COEFF) - 1 = 11
    # Python mode='full' first 11 outputs are partial sums (startup transient)
    # Verilog gates these out via output_valid, so Verilog[0] = Python[11]
    FULL_COEFF_LEN = len(COEFF_INT) * 2   # = 12
    total_latency  = FULL_COEFF_LEN - 1   # = 11

    py_trim   = filtered_int[total_latency : total_latency + len(verilog_out)]
    vlog_trim = verilog_out[:len(py_trim)]

    mismatches = np.sum(py_trim != vlog_trim)
    print(f"\n--- Verification Report ---")
    print(f"Latency offset   : {total_latency} samples")
    print(f"Samples compared : {len(py_trim)}")
    print(f"Mismatches       : {mismatches}")
    if mismatches == 0:
        print("PASS: Python reference matches Verilog output exactly.")
    else:
        print("FAIL: Discrepancies found — check bit-width or latency.")
        for i in np.where(py_trim != vlog_trim)[0][:10]:
            print(f"  sample {i+total_latency}: Python={py_trim[i]}, Verilog={vlog_trim[i]}")

    # Plot
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    ylim = (-2200, 2200)
    n = np.arange(len(py_trim))

    axes[0].plot(n, py_trim   / DC_GAIN, color='steelblue', lw=1.2,
                 label='Python reference')
    axes[0].plot(n, vlog_trim / DC_GAIN, '--', color='tomato', lw=1.0,
                 alpha=0.8, label='Verilog output')
    axes[0].set_title(f"Python vs Verilog — overlaid (both / {DC_GAIN})")
    axes[0].set_ylabel('Amplitude (counts)')
    axes[0].set_ylim(ylim); axes[0].legend(); axes[0].grid(True)

    diff = py_trim - vlog_trim
    axes[1].plot(n, diff, color='purple', lw=1.0,
                 label=f'Error (Python - Verilog)  max={np.max(np.abs(diff))}')
    axes[1].set_title('Difference')
    axes[1].set_xlabel('Sample index')
    axes[1].set_ylabel('Error (raw counts)')
    axes[1].legend(); axes[1].grid(True)

    plt.suptitle('FIR Filter Verification — Python vs Verilog', fontsize=13)
    plt.tight_layout()
    plt.show()

# User input
def get_user_input():
    print("\nFilter info:")
    print(f"  Coefficients  : {COEFF_INT.tolist()}  (half of symmetric filter)")
    print(f"  Full filter   : {FULL_COEFF.tolist()}")
    print(f"  DC gain       : {DC_GAIN}  (= 2^8, recovered by >>> 8 in Verilog)")
    print(f"  Cutoff        : ~60 Hz  (keep signal freq well below this)")
    print(f"  Sample rate   : fixed at 1000 Hz in this script")
    print()
    print("Signal types: sine, square, cos, triangle, sawtooth, pulse, chirp")
    print()
    num_samples     = int(input  ("Number of samples    [1000]  : ") or 1000)
    freq            = float(input("Signal frequency Hz  [10]    : ") or 10.0)
    noise_amplitude = float(input("Noise amplitude 0-1  [0.3]   : ") or 0.3)
    signal_type     = input      ("Signal type          [square] : ").strip().lower() or 'square'
    return num_samples, freq, noise_amplitude, signal_type


# Main
def main():
    parser = argparse.ArgumentParser(description="FIR filter stimulus generator")
    parser.add_argument('--compare', action='store_true',
                        help='Compare frozen Python reference against Verilog output')
    args = parser.parse_args()

    # --compare mode: skip generation, load frozen reference and compare
    if args.compare:
        try:
            frozen_ref = np.loadtxt('python_reference.txt', dtype=np.int64)
            print("[INFO] Loaded python_reference.txt")
        except FileNotFoundError:
            print("[FATAL] python_reference.txt not found.")
            print("        Run gen_noisy_sig.py (without --compare) first to generate it.")
            return
        compare_with_verilog(frozen_ref)
        return

    # Normal generation mode
    num_samples, freq, noise_amplitude, signal_type = get_user_input()

    # Generate signals
    t           = np.linspace(0, 1, num_samples)
    clean       = gen_signal(signal_type, t, freq)
    noisy_float = clean + np.random.normal(0, noise_amplitude, num_samples)

    # Quantise to 12-bit fixed-point
    noisy_int = to_fixed12(noisy_float)
    clean_int = to_fixed12(clean)

    # Apply reference filter
    filtered_int = apply_filter_causal(noisy_int)

    # Save stimulus files
    save_hex(noisy_int, 'input_signal_square_2.txt')
    save_hex(clean_int, 'clean_signal.txt')
    save_coeffs('coeff_val.txt')

    # Save frozen Python reference — used by --compare later
    # Must be saved here before any re-run changes the noise
    np.savetxt('python_reference.txt', filtered_int, fmt='%d')

    print(f"\nSaved {num_samples} samples  → input_signal_square_2.txt")
    print(f"Saved clean signal       → clean_signal.txt")
    print(f"Saved coefficients       → coeff_val.txt")
    print(f"Saved Python reference   → python_reference.txt")
    print(f"\nNext steps:")
    print(f"  1. Copy txt files to Vivado project folder")
    print(f"  2. Run Vivado simulation  → produces filtered_signal.txt")
    print(f"  3. Copy filtered_signal.txt back here")
    print(f"  4. Run: python gen_noisy_sig.py --compare")

    # Plot all on same amplitude axis (+-2200 counts)
    # noisy_int and clean_int are in raw 12-bit counts (+-2000 nominal)
    # filtered_int is divided by DC_GAIN to bring back to same range
    n_in   = np.arange(num_samples)
    n_filt = np.arange(len(filtered_int))

    fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=False)
    ylim = (-2200, 2200)

    axes[0].plot(n_in, clean_int, color='steelblue', lw=1.2,
                 label=f'Clean {signal_type} — {freq} Hz')
    axes[0].set_title(f'Clean Signal ({signal_type}, {freq} Hz, {num_samples} samples)')
    axes[0].set_ylabel('Amplitude (counts)')
    axes[0].set_ylim(ylim); axes[0].grid(True); axes[0].legend()

    axes[1].plot(n_in, noisy_int, color='tomato', alpha=0.8, lw=0.8,
                 label=f'Noisy input — noise={noise_amplitude}')
    axes[1].set_title(f'Noisy Input (noise amplitude = {noise_amplitude})')
    axes[1].set_ylabel('Amplitude (counts)')
    axes[1].set_ylim(ylim); axes[1].grid(True); axes[1].legend()

    axes[2].plot(n_filt, filtered_int / DC_GAIN, color='seagreen', lw=1.2,
                 label=f'Filtered / {DC_GAIN}  (Python reference)')
    axes[2].set_title(f'Filtered Output — divided by DC gain ({DC_GAIN}) for display')
    axes[2].set_xlabel('Sample index')
    axes[2].set_ylabel('Amplitude (counts)')
    axes[2].set_ylim(ylim); axes[2].grid(True); axes[2].legend()

    plt.suptitle('Symmetric FIR Filter — Python Reference Model', fontsize=13, y=1.01)
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()
