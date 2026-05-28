#!/usr/bin/env python3
"""
CSD-EWS: Critical Slowing Down Early Warning System
==================================================================
Methodology Demonstration: Engine A (Jacobian) vs Engine B (LFPR)
Experiment: Kundur 4-machine Small-Signal Stability (KA Sweep)

TaiScience Research Group | Open Source Reference Implementation
"""

import os
import andes
import numpy as np
from numpy.linalg import lstsq, eigvals, matrix_rank
from scipy.stats import linregress, spearmanr
from scipy.fft import fft, fftfreq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION & DYNAMIC PATHS
# ============================================================
# Dynamically locate the ANDES kundur case file regardless of the OS
CASE = os.path.join(os.path.dirname(andes.__file__), 'cases', 'kundur', 'kundur_full.xlsx')

# Ensure output directory exists
OUT_DIR = './results'
os.makedirs(OUT_DIR, exist_ok=True)

ALL_IDX = list(range(0, 20))
V_IDX   = list(range(10, 20))
TSTEP   = 1/60
FS      = 60.0          # sampling frequency
F_LOW   = 2.0           # LFPR threshold (Hz)

KA_VALUES = [5, 8, 10, 13, 16, 20, 25, 30, 40, 50,
             70, 100, 130, 160, 200, 250, 300, 400, 500]

# ============================================================
# ENGINE A: OLS Jacobian (Time-Domain CSD)
# ============================================================
def engine_a(t, y, idx, n_vars=6, window=20, tw=10):
    if len(t) < window + tw + 5:
        return np.nan, np.nan
    y_sub = y[:, idx]
    mu = y_sub.mean(0); sig = y_sub.std(0) + 1e-10
    y_sub = (y_sub - mu) / sig
    U, S, _ = np.linalg.svd(y_sub, full_matrices=False)
    y_pca = U[:, :n_vars] * S[:n_vars]
    lme_t, lme_v = [], []
    for start in range(0, len(t) - window, 1):
        end = start + window
        X_t  = y_pca[start:end-1]
        X_t1 = y_pca[start+1:end]
        if matrix_rank(X_t) < n_vars: continue
        J, _, _, _ = lstsq(X_t, X_t1, rcond=None)
        eigs = np.abs(eigvals(J))
        lme_t.append(t[start + window//2])
        lme_v.append(np.log(np.max(eigs) + 1e-10))
    if len(lme_v) < tw + 5:
        return np.nan, np.nan
    lme_t = np.array(lme_t)
    lme_v = np.array(lme_v)
    post  = lme_t >= 1.0
    if post.sum() < tw + 3:
        return np.nan, np.nan
    post_v = lme_v[post]
    trends = [linregress(range(tw), post_v[i-tw:i])[0]
              for i in range(tw, len(post_v))]
    return np.mean(trends[-20:]), np.mean(post_v[-20:])

# ============================================================
# ENGINE B: FFT / LFPR + Spectral Entropy (Frequency-Domain CSD)
# ============================================================
def engine_b(t, y, idx, fault_t=1.0,
             fs=FS, f_low=F_LOW, window=120, stride=10):
    '''
    Compute Low-Frequency Power Ratio (LFPR) and Spectral Entropy.
    window: FFT window size in samples (120 = 2 seconds at 60Hz)
    Returns (score_LFPR, score_Entropy)
    '''
    if len(t) < window + 10:
        return np.nan, np.nan

    y_sub = y[:, idx]
    # per-channel normalisation
    mu  = y_sub.mean(0); sig = y_sub.std(0) + 1e-10
    y_sub = (y_sub - mu) / sig

    freqs = fftfreq(window, d=1.0/fs)
    low_mask = (np.abs(freqs) > 0) & (np.abs(freqs) <= f_low)

    lme_t, lfpr_v, ent_v = [], [], []
    N = len(t)
    for start in range(0, N - window, stride):
        mid_t = t[start + window // 2]
        if mid_t < fault_t:
            continue
        seg = y_sub[start:start + window]   # (window, n_ch)
        # FFT per channel
        F = fft(seg, axis=0)                # (window, n_ch)
        psd = np.abs(F[:window//2]) ** 2    # one-sided PSD
        psd_total = psd.sum(axis=0) + 1e-12

        # LFPR: mean across channels
        low_idx = low_mask[:window//2]
        lfpr_ch = psd[low_idx].sum(axis=0) / psd_total
        lfpr    = float(np.mean(lfpr_ch))

        # Spectral Entropy: mean across channels
        p_norm  = psd / psd_total           # normalised PSD
        entropy = float(np.mean(-np.sum(p_norm * np.log(p_norm + 1e-12), axis=0)))

        lme_t.append(mid_t)
        lfpr_v.append(lfpr)
        ent_v.append(entropy)

    if len(lfpr_v) < 5:
        return np.nan, np.nan

    # score = mean of last 20 windows
    score_LFPR    = float(np.mean(lfpr_v[-20:]))
    score_Entropy = float(np.mean(ent_v[-20:]))   # lower = more concentrated = worse

    return score_LFPR, score_Entropy, np.array(lme_t), np.array(lfpr_v), np.array(ent_v)

# ============================================================
# MAIN SWEEP EXECUTION
# ============================================================
if __name__ == "__main__":
    print(f"CSD-EWS Open-Source Reference Pipeline")
    print(f"Output directory: {OUT_DIR}\n")
    print(f"{'KA':>5} | {'score_J':>8} | {'LFPR':>8} | {'-Entropy':>8} | {'Vdev':>8} | {'da_std':>8}")
    print('-'*70)

    results = []
    for ka in KA_VALUES:
        ss = andes.load(CASE, setup=False, no_output=True)
        ss.EXDC2.KA.v = [ka] * 4
        ss.add('Fault',{'idx':'F1','bus':7,'tf':1.0,'tc':1.1,'xf':0.01})
        ss.setup(); ss.PFlow.run()
        ss.TDS.config.tf = 15.0; ss.TDS.config.tstep = TSTEP
        ss.TDS.run()
        t = ss.dae.ts.t; y = ss.dae.ts.y

        # Engine A
        _, sj = engine_a(t, y, ALL_IDX)

        # Engine B
        eb = engine_b(t, y, ALL_IDX)
        if eb[0] is np.nan:
            s_lfpr, s_ent = np.nan, np.nan
            lme_t_b, lfpr_v, ent_v = None, None, None
        else:
            s_lfpr, s_ent = eb[0], eb[1]
            lme_t_b, lfpr_v, ent_v = eb[2], eb[3], eb[4]

        # Vdev Baseline
        v     = y[:, V_IDX]; v_nom = v[0,:]
        post  = t >= 1.0
        sv    = float(np.mean(np.max(np.abs(v[post]-v_nom), axis=1))) if post.sum() else 0.0

        # Ground truth (Inter-area oscillation amplitude)
        da     = y[:,0] - y[:,2]
        post2  = t > 2.0
        std_da = np.std(da[post2][-120:]) if post2.sum() > 120 else np.nan

        results.append(dict(ka=ka, score_J=sj,
                            score_LFPR=s_lfpr, score_Entropy=s_ent,
                            vdev=sv, std_da=std_da,
                            lme_t_b=lme_t_b, lfpr_v=lfpr_v, ent_v=ent_v))
        print(f"{ka:5d} | {sj:8.5f} | {s_lfpr:8.5f} | {-s_ent:8.5f} | {sv:8.5f} | {std_da:8.5f}")

    # ============================================================
    # SPEARMAN CORRELATION ANALYSIS
    # ============================================================
    std_da  = np.array([r['std_da']        for r in results])
    s_J     = np.array([r['score_J']       for r in results])
    s_LFPR  = np.array([r['score_LFPR']    for r in results])
    s_Ent   = np.array([-r['score_Entropy'] for r in results]) 
    s_vdev  = np.array([r['vdev']          for r in results])
    kas     = np.array([r['ka']            for r in results])

    valid   = ~np.isnan(s_J) & ~np.isnan(s_LFPR)
    rho_J,    p_J    = spearmanr(std_da[valid], s_J[valid])
    rho_LFPR, p_LFPR = spearmanr(std_da[valid], s_LFPR[valid])
    rho_Ent,  p_Ent  = spearmanr(std_da[valid], s_Ent[valid])
    rho_vdev, p_vdev = spearmanr(std_da[valid], s_vdev[valid])

    # Combo: LFPR + score_J
    s_combo = 0.5 * s_J + 0.5 * s_LFPR
    rho_combo, p_combo = spearmanr(std_da[valid], s_combo[valid])

    print('\n=== Spearman rho vs da_std (System Instability Ground Truth) ===')
    print(f'  Engine A score_J:    rho={rho_J:+.3f}  p={p_J:.4f}')
    print(f'  Engine B LFPR:       rho={rho_LFPR:+.3f}  p={p_LFPR:.4f}')
    print(f'  Engine B -Entropy:   rho={rho_Ent:+.3f}  p={p_Ent:.4f}')
    print(f'  Combo (A+B):         rho={rho_combo:+.3f}  p={p_combo:.4f}')
    print(f'  Vdev (baseline):     rho={rho_vdev:+.3f}  p={p_vdev:.4f}  <- WRONG DIRECTION')

    # ============================================================
    # VISUALIZATION EXPORT
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(KA_VALUES)))

    # Top-left: LFPR time series
    ax = axes[0, 0]
    for i, ka in enumerate([10, 50, 200, 500]):
        r = next(x for x in results if x['ka'] == ka)
        if r['lme_t_b'] is not None:
            ax.plot(r['lme_t_b'], r['lfpr_v'], label=f'KA={ka}', lw=1.5)
    ax.set_title(f'Engine B — LFPR Time Series (f_low={F_LOW}Hz)')
    ax.set_ylabel('LFPR'); ax.set_xlabel('Time (s)')
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    # Top-right: Entropy time series
    ax = axes[0, 1]
    for ka in [10, 50, 200, 500]:
        r = next(x for x in results if x['ka'] == ka)
        if r['lme_t_b'] is not None:
            ax.plot(r['lme_t_b'], r['ent_v'], label=f'KA={ka}', lw=1.5)
    ax.set_title('Engine B — Spectral Entropy Time Series')
    ax.set_ylabel('Entropy'); ax.set_xlabel('Time (s)')
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    # Bottom-left: scatter score_J vs da_std
    ax = axes[1, 0]
    ax.scatter(std_da, s_J, color='crimson', s=50, zorder=3, label=f'Engine A score_J (rho={rho_J:.2f})')
    ax.scatter(std_da, s_LFPR, color='steelblue', s=50, marker='^', zorder=3, label=f'Engine B LFPR (rho={rho_LFPR:.2f})')
    for sc, col in [(s_J,'crimson'),(s_LFPR,'steelblue')]:
        m,b = np.polyfit(std_da[valid], sc[valid], 1)
        xl = np.linspace(std_da.min(), std_da.max(), 100)
        ax.plot(xl, m*xl+b, color=col, ls='--', lw=1.2, alpha=0.6)
    ax.set_xlabel('da_std (Inter-area Oscillation Amplitude)')
    ax.set_ylabel('CSD Score')
    ax.set_title('Engine A vs Engine B — Scatter Plot')
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    # Bottom-right: bar chart rho comparison
    ax = axes[1, 1]
    methods = ['Engine A\nscore_J', 'Engine B\nLFPR', 'Engine B\n-Entropy', 'Combo\nA+B', 'Vdev\n(baseline)']
    rhos    = [rho_J, rho_LFPR, rho_Ent, rho_combo, rho_vdev]
    cols    = ['crimson','steelblue','steelblue','darkgreen','orange']
    bars = ax.bar(methods, rhos, color=cols, alpha=0.8)
    ax.axhline(0, color='k', lw=0.8)
    ax.axhline(0.5, color='gray', ls='--', lw=0.8, label='rho=0.5')
    ax.axhline(-0.5, color='gray', ls='--', lw=0.8)
    for bar, rho in zip(bars, rhos):
        ax.text(bar.get_x()+bar.get_width()/2, rho + 0.02*np.sign(rho),
                f'{rho:.2f}', ha='center', va='bottom' if rho>=0 else 'top', fontsize=9)
    ax.set_ylabel('Spearman rho vs da_std')
    ax.set_title('Method Comparison — Spearman rho')
    ax.set_ylim(-1.1, 1.1); ax.grid(True, alpha=0.3)

    plt.suptitle(f'Critical Slowing Down: Engine A vs B (Kundur 19-point KA sweep)', fontsize=12)
    plt.tight_layout()
    
    # Save outputs safely
    fig_path = os.path.join(OUT_DIR, 'engine_ab_compare.png')
    data_path = os.path.join(OUT_DIR, 'kundur_engine_ab.npy')
    plt.savefig(fig_path, dpi=150)
    np.save(data_path, results)
    print(f"\n[Success] Outputs saved to:")
    print(f"  - Figure: {fig_path}")
    print(f"  - Data:   {data_path}")