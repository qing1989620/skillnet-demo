import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# 预注册参数
SEED = 42
N_SIM = 1000
SAMPLE_SIZES = [10, 50, 100, 500, 1000, 5000]
ALPHA = 0.05

np.random.seed(SEED)

def simulate_estimator(n, dist='normal'):
    """生成样本并计算估计量（此处以样本均值示意）"""
    if dist == 'normal':
        samples = np.random.normal(loc=0, scale=1, size=n)
    elif dist == 'cauchy':
        samples = np.random.standard_cauchy(size=n)
    else:
        raise ValueError("Unsupported distribution")
    return np.mean(samples)

def run_monte_carlo():
    results = {}
    for n in SAMPLE_SIZES:
        estimates = [simulate_estimator(n) for _ in range(N_SIM)]
        mean_est = np.mean(estimates)
        std_est = np.std(estimates, ddof=1)
        # 理论标准误（正态分布下）
        theoretical_se = 1 / np.sqrt(n)
        # 偏差
        bias = mean_est - 0.0
        # 置信区间
        ci_low = mean_est - 1.96 * std_est / np.sqrt(N_SIM)
        ci_high = mean_est + 1.96 * std_est / np.sqrt(N_SIM)
        # 正态性检验
        _, p_value = stats.normaltest(estimates)
        results[n] = {
            'mean': mean_est,
            'std': std_est,
            'theoretical_se': theoretical_se,
            'bias': bias,
            'ci': (ci_low, ci_high),
            'p_value': p_value
        }
    return results

def plot_convergence(results):
    ns = list(results.keys())
    empirical_se = [results[n]['std'] for n in ns]
    theoretical_se = [results[n]['theoretical_se'] for n in ns]
    plt.figure()
    plt.loglog(ns, empirical_se, 'o-', label='Empirical SE')
    plt.loglog(ns, theoretical_se, 's--', label='Theoretical SE ~ n^{-1/2}')
    plt.xlabel('Sample size n')
    plt.ylabel('Standard error')
    plt.legend()
    plt.title('Convergence rate check (示意值，需真实数据验证)')
    plt.savefig('convergence_plot.png')
    plt.close()

if __name__ == '__main__':
    res = run_monte_carlo()
    for n, stats_dict in res.items():
        print(f"n={n}: mean={stats_dict['mean']:.4f}, std={stats_dict['std']:.4f}, "
              f"theoretical_se={stats_dict['theoretical_se']:.4f}, "
              f"bias={stats_dict['bias']:.4f}, CI=({stats_dict['ci'][0]:.4f}, {stats_dict['ci'][1]:.4f}), "
              f"p_value={stats_dict['p_value']:.4f}")
    plot_convergence(res)
    print("蒙特卡洛模拟完成。所有数值为示意值，需真实数据验证。")
