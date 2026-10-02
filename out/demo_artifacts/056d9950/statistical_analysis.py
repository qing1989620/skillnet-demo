import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

RANDOM_SEED = 20240501
np.random.seed(RANDOM_SEED)

def cohens_d(x, y):
    nx, ny = len(x), len(y)
    sx, sy = np.var(x, ddof=1), np.var(y, ddof=1)
    pooled = np.sqrt(((nx - 1) * sx + (ny - 1) * sy) / (nx + ny - 2))
    return (np.mean(x) - np.mean(y)) / pooled

def hedges_g(d, nx, ny):
    correction = 1 - 3 / (4 * (nx + ny) - 9)
    return d * correction

def bootstrap_ci(x, y, stat_func, n_boot=10000, alpha=0.05):
    rng = np.random.default_rng(RANDOM_SEED)
    stats_boot = []
    for _ in range(n_boot):
        xb = rng.choice(x, size=len(x), replace=True)
        yb = rng.choice(y, size=len(y), replace=True)
        stats_boot.append(stat_func(xb, yb))
    lower = np.percentile(stats_boot, 100 * alpha / 2)
    upper = np.percentile(stats_boot, 100 * (1 - alpha / 2))
    return lower, upper

def analyze_independent(df, metric, group_col='group', g1='control', g2='treatment'):
    x = df.loc[df[group_col] == g1, metric].dropna().values
    y = df.loc[df[group_col] == g2, metric].dropna().values
    shapiro_x = stats.shapiro(x)
    shapiro_y = stats.shapiro(y)
    levene = stats.levene(x, y, center='median')
    normal_ok = shapiro_x.pvalue > 0.05 and shapiro_y.pvalue > 0.05
    equal_var = levene.pvalue > 0.05
    if normal_ok and equal_var:
        test = stats.ttest_ind(x, y, equal_var=True)
        test_name = 'Student t-test'
    elif normal_ok and not equal_var:
        test = stats.ttest_ind(x, y, equal_var=False)
        test_name = 'Welch t-test'
    else:
        test = stats.mannwhitneyu(x, y, alternative='two-sided')
        test_name = 'Mann-Whitney U'
    d = cohens_d(x, y)
    g = hedges_g(d, len(x), len(y))
    ci_low, ci_high = bootstrap_ci(x, y, cohens_d)
    return {
        'metric': metric,
        'test': test_name,
        'statistic': float(test.statistic),
        'p_value': float(test.pvalue),
        'cohens_d': float(d),
        'hedges_g': float(g),
        'ci_lower': float(ci_low),
        'ci_upper': float(ci_high),
        'n_group1': len(x),
        'n_group2': len(y),
        'shapiro_p_group1': float(shapiro_x.pvalue),
        'shapiro_p_group2': float(shapiro_y.pvalue),
        'levene_p': float(levene.pvalue),
    }

def apply_fdr(results_df, alpha=0.05):
    reject, p_adj, _, _ = multipletests(results_df['p_value'], alpha=alpha, method='fdr_bh')
    results_df['p_bh'] = p_adj
    results_df['fdr_significant'] = reject
    return results_df

def main():
    df = pd.read_csv('clean-dataset.csv')
    results = []
    for metric in ['metric_a', 'metric_b']:
        results.append(analyze_independent(df, metric))
    results_df = pd.DataFrame(results)
    results_df = apply_fdr(results_df)
    results_df.to_csv('statistical-test-results.csv', index=False)
    print(results_df)

if __name__ == '__main__':
    main()
