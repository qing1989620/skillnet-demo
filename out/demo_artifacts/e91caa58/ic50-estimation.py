import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.stats import f

# 4PL 模型
def four_pl(x, bottom, top, log_ic50, hill_slope):
    return bottom + (top - bottom) / (1 + 10 ** ((log_ic50 - x) * hill_slope))

# 3PL 模型（Bottom 固定为 0）
def three_pl(x, top, log_ic50, hill_slope):
    return four_pl(x, 0, top, log_ic50, hill_slope)

def fit_ic50(df, model='4PL', n_bootstrap=1000, seed=42):
    """
    拟合 IC50 并计算 bootstrap 95% CI。
    df 需包含列：log10_dose_uM, inhibition_fraction
    """
    x = df['log10_dose_uM'].values
    y = df['inhibition_fraction'].values
    mask = ~np.isnan(x) & ~np.isnan(y)
    x, y = x[mask], y[mask]

    if model == '4PL':
        p0 = [0, 1, np.median(x), 1]
        bounds = ([0, 0.5, x.min()-1, 0.1], [0.2, 1.2, x.max()+1, 10])
        popt, pcov = curve_fit(four_pl, x, y, p0=p0, bounds=bounds, maxfev=10000)
        y_pred = four_pl(x, *popt)
        k = 4
    else:
        p0 = [1, np.median(x), 1]
        bounds = ([0.5, x.min()-1, 0.1], [1.2, x.max()+1, 10])
        popt, pcov = curve_fit(three_pl, x, y, p0=p0, bounds=bounds, maxfev=10000)
        y_pred = three_pl(x, *popt)
        k = 3

    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot
    rse = np.sqrt(ss_res / (len(y) - k))

    # bootstrap
    rng = np.random.default_rng(seed)
    ic50_boot = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, len(x), len(x))
        try:
            if model == '4PL':
                p_boot, _ = curve_fit(four_pl, x[idx], y[idx], p0=popt, bounds=bounds, maxfev=10000)
                ic50_boot.append(p_boot[2])
            else:
                p_boot, _ = curve_fit(three_pl, x[idx], y[idx], p0=popt, bounds=bounds, maxfev=10000)
                ic50_boot.append(p_boot[1])
        except Exception:
            continue

    ic50_ci = np.percentile(ic50_boot, [2.5, 97.5]) if ic50_boot else [np.nan, np.nan]

    if model == '4PL':
        result = {
            'model': '4PL',
            'Bottom': popt[0],
            'Top': popt[1],
            'logIC50': popt[2],
            'IC50_uM': 10 ** popt[2],
            'HillSlope': popt[3],
            'R2': r2,
            'RSE': rse,
            'IC50_95CI_log': ic50_ci,
            'IC50_95CI_uM': [10 ** ic50_ci[0], 10 ** ic50_ci[1]]
        }
    else:
        result = {
            'model': '3PL',
            'Bottom': 0,
            'Top': popt[0],
            'logIC50': popt[1],
            'IC50_uM': 10 ** popt[1],
            'HillSlope': popt[2],
            'R2': r2,
            'RSE': rse,
            'IC50_95CI_log': ic50_ci,
            'IC50_95CI_uM': [10 ** ic50_ci[0], 10 ** ic50_ci[1]]
        }
    return result

if __name__ == '__main__':
    # 示例数据（示意值，需真实数据验证）
    data = pd.DataFrame({
        'log10_dose_uM': [-2, -1, 0, 1, 2, 3],
        'inhibition_fraction': [0.03, 0.06, 0.22, 0.55, 0.88, 0.95]
    })
    res = fit_ic50(data, model='4PL', n_bootstrap=500)
    print(res)
