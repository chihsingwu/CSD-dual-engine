# Physical Boundary Validation for Grid AI

A compact open-source reference package for **physics-boundary validation** of AI systems in electric power grids.

This project does **not** present a full grid product or a replacement for existing grid AI models. It provides a small, reproducible experimental layer for testing whether AI predictions remain aligned with **dynamic stability physics** near weak-damping and critical-transition regimes.

The current reference implementation focuses on **Critical Slowing Down Early Warning Signals (CSD-EWS)** using the Kundur 4-machine system and a KA excitation-gain sweep.

<img width="1950" height="1350" alt="engine_ab_compare" src="https://github.com/user-attachments/assets/1da9f3ae-1930-42e0-a472-1abc36d17f65" />

## 🚀 Empirical Validation Results

### ⚡ The Core Breakthrough: Weak Damping & Dynamic Small-Signal Instability
Traditional grid monitoring relies heavily on **Voltage Deviation ($V_{dev}$)**. However, as power systems integrate massive renewable energy sources, a catastrophic vulnerability emerges: **dynamic small-signal instability under weak-damping conditions**. In these scenarios, excitation controls artificialy maintain nominal voltage, masking the severe degradation of the system's underlying dynamic structure. **$V_{dev}$ fails completely here, while CSD-EWS thrives**.

---

### 📊 Experiment 1: IEEE 39-Bus Transient Stability
Validated using **ANDES v2.0.0** on the New England 39-bus system across **116 multi-fault scenarios** ($77$ stable, $39$ unstable) with a 60 Hz PMU-equivalent sampling rate.

#### 📈 Boundary Discovery & Performance
* **Critical Clearing Time (CCT) Discovery**: Systematically identified the exact physical bifurcation boundary for a Bus 16 fault between **1.3s (Stable)** and **1.4s (Unstable)**.
* **Pure Data-Driven Inference**: Operating **without any network topology, power flow models, or pre-trained classifiers**, Engine A achieved an exceptional **AUC-ROC of 0.8795** using rolling window metrics.

| Metric Evaluation (Post-Fault Window) | AUC-ROC |
| :--- | :---: |
| **`score_J`** (Mean $\log \max|\lambda(J)|$ - Last 20 windows) | **0.8795** |
| **`score_trend`** (Rolling trend statistic slope) | **0.8025** |
| **`combo`** (Weighted Composite Score) | **0.8768** |

* **Clean Binary Separation**: In single-scenario validation, the rolling trend slope provides an instantaneous binary indicator—a **positive slope** triggers immediate critical alert routing, while a **negative slope** robustly tracks system post-fault recovery[cite: 2, 3].

---

### 📉 Experiment 2: Kundur 4-Machine 2-Area Small-Signal Stability
To simulate the absolute blind spot of conventional AI models, we executed an excitation gain ($K_A$) sweep ($K_A = 10, 20, 50, 200$) to induce progressive **inter-area oscillation damping degradation** near the 0.6 Hz mode[cite: 2].

#### 🚨 CSD Jacobian vs. Traditional Voltage Deviation ($V_{dev}$)
As the excitation gain ($K_A$) scales up to 200, the system approaches a critical transition due to **negative/weak damping**, magnifying inter-area oscillations by **8x**[cite: 2]. 

| Excitation Gain ($K_A$) | System Stability Status | $V_{dev}$ Score (Traditional) | **CSD `score_J` (This Work)** |
| :---: | :--- | :---: | :---: |
| $K_A = 10$ | **Strong Damping (Optimal)** | 0.0502 | **0.0023** |
| $K_A = 20$ | Normal Operation | 0.0480 | **0.0072** |
| $K_A = 50$ | Weak Damping | 0.0471 | **0.0564** |
| $K_A = 200$ | **Negative Damping (Critical Boundary)** | *0.0469 (Looks Better!)* | **0.1201 (Triggered!)** |

#### 🎯 Spearman Correlation ($\rho$) Analysis
* **Conventional $V_{dev}$ Failure ($\rho = -1.000$)**: Traditional voltage indicators point in the **perfect opposite direction**, signaling "improved safety" while the grid's dynamic structure is actually fracturing[cite: 2].
* **CSD Jacobian Success ($\rho = +0.800$)**: Our data-driven Jacobian proxy successfully tracks the true underlying physical degradation of system damping with a powerful positive correlation[cite: 2].

> ⚠️ **Critical Finding**: In modern weak-damping grid environments, traditional voltage deviation acts as a dangerous **anti-indicator** of dynamic stability. CSD-EWS provides the essential physics-informed validation layer required before thresholds are violated[cite: 2].






## Core idea

Modern grid AI methods can be evaluated not only by classification accuracy or OPF feasibility, but also by whether their outputs remain consistent with physical stability margins near dynamic boundaries.

This package frames that validation in three layers:

### Layer 1 — Physical scenario generation

Inspired by recent LLM-driven transient stability assessment workflows, complex power-system scenarios can be generated through simulation tools such as ANDES.

Examples include:

* clearing-time sweeps,
* excitation-gain sweeps,
* weak-damping regimes,
* renewable-penetration stress cases,
* line, bus, or generator disturbance scenarios.

In this package, the reference demo uses a Kundur 4-machine KA sweep as a controlled physical boundary case.

### Layer 2 — CSD-EWS dynamic safety margin

The package computes interpretable early-warning indicators that quantify whether a system is approaching dynamic instability.

The current dual-engine implementation includes:

* **Engine A — Time-domain Jacobian proxy**  
Estimates a local linear transition operator from multichannel PMU-like trajectories and summarizes the eigenvalue trajectory.
* **Engine B — Spectral CSD indicator**  
Computes low-frequency power ratio (LFPR) and spectral entropy from sliding FFT windows.

These indicators act as a **damping-aware physical scale** for weak-damping and low-frequency oscillation regimes.

### Layer 3 — AI prediction cross-validation interface

The intended next step is a standardized interface where any AI system can submit predictions for the same physical scenarios.

Examples of candidate AI systems include:

* grid-native models such as GridSFM-style approaches,
* cross-domain physical foundation models such as TokaMind-style approaches,
* LLM-generated TSA classifiers,
* conventional CNN/LSTM/Transformer stability classifiers.

Their predictions can then be cross-checked against CSD-EWS indicators, damping trends, LFPR, and instability ground truth.

The goal is not to claim that CSD-EWS replaces these models. The goal is to provide a **physics-informed validation layer**:

> Does the AI prediction remain consistent with damping-aware stability evidence near the physical boundary? By establishing this cross-validation interface, we enable rigorous benchmarking of diverse AI architectures—ranging from grid-native foundation models like GridSFM to cross-domain models like TokaMind—against the immutable physical laws governing dynamic stability.

## What this package currently provides

This v0.1 release provides the CSD-EWS reference layer only:

* Engine A: data-driven Jacobian proxy score.
* Engine B: LFPR and spectral entropy score.
* Kundur KA sweep demo using ANDES.
* Spearman correlation analysis against inter-area oscillation amplitude.
* Reproducible figure and data export.

It is intentionally small. It does not include a database, web service, Docker stack, CI pipeline, or full AI benchmark server.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .
```

Core engine dependencies:

```bash
pip install numpy scipy matplotlib
```

For the Kundur simulation demo, install ANDES:

```bash
pip install andes openpyxl
```

## Quick smoke test

```bash
pytest -q
```

## Run Kundur KA sweep

Small sweep:

```bash
csd-dual-engine --ka-values 10,50,200,500 --output-dir results\_demo
```

Full default 19-point sweep:

```bash
csd-dual-engine --output-dir results
```

Expected outputs:

```text
results/
├─ kundur\_engine\_ab\_summary.csv
├─ kundur\_engine\_ab.npy
└─ engine\_ab\_compare.png
```

## Programmatic use

```python
import numpy as np
from csd\_dual\_engine import engine\_a\_jacobian, engine\_b\_spectral

t = np.arange(0, 15, 1/60)
y = np.column\_stack(\[
    np.sin(2\*np.pi\*0.5\*t),
    np.cos(2\*np.pi\*0.8\*t),
])

a = engine\_a\_jacobian(t, y, n\_vars=2)
b = engine\_b\_spectral(t, y, fs=60.0)

print(a.log\_max\_eigenvalue\_score)
print(b.lfpr\_score, b.spectral\_entropy\_score)
```

## Example interpretation

In a weak-damping KA sweep, voltage deviation may decrease because excitation control keeps voltage regulated, even as inter-area oscillation damping deteriorates.

CSD-EWS is designed to catch this type of mismatch:

* voltage can look acceptable,
* damping can still worsen,
* LFPR or Jacobian-proxy indicators can expose the dynamic boundary.

This makes the package useful as a **validation reference** for AI models that claim to understand grid stability.

## Intended research use

Use this package to:

* generate or analyze controlled physical-boundary cases,
* compute damping-aware CSD indicators,
* compare AI predictions against interpretable physical evidence,
* build small benchmark notes for grid AI evaluation,
* support technical discussions around physical AI reliability.

Do not overinterpret this release as:

* a complete PMU production system,
* a certified protection relay,
* a replacement for full power-system studies,
* a complete benchmark for all grid AI models.

## Notes

* The Kundur demo requires ANDES and its bundled `kundur\_full.xlsx` case.
* Engine A uses a PCA-reduced local linear transition operator, then summarizes the final post-fault eigenvalue trajectory.
* Engine B computes LFPR and spectral entropy over sliding windows.
* The package intentionally stays small: no database, no web server, no Docker, no CI by default.

## Citation / attribution

TaiScience Research Group — Open Source Reference Implementation.

If you use this package, please cite or acknowledge:

```text
TaiScience Research Group. Physical Boundary Validation for Grid AI: CSD-EWS Dual-Engine Reference Implementation, 2026.
```

## 

