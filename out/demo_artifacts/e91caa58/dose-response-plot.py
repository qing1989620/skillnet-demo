import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# 4PL 模型
def four_pl(x, bottom, top, log_ic50, hill_slope):
    return bottom + (top - bottom) / (1 + 10 ** ((log_ic50 - x) * hill_slope))

def plot_dose_response(df, ic50_result, output_pdf='dose_response.pdf'):
    """
    绘制出版级剂量-响应曲线。
    df 需包含：log10_dose_uM, inhibition_fraction, sd
    ic50_result 来自 fit_ic50 的字典
    """
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=300)
    x = df['log10_dose_uM'].values
    y = df['inhibition_fraction'].values
    sd = df['sd'].values

    # 散点与误差条
    ax.errorbar(x, y, yerr=sd, fmt='o', color='black', capsize=3, label='Data (mean ± SD)')

    # 拟合曲线
    x_fit = np.linspace(x.min() - 0.5, x.max() + 0.5, 200)
    if ic50_result['model'] == '4PL':
        y_fit = four_pl(x_fit, ic50_result['Bottom'], ic50_result['Top'],
                        ic50_result['logIC50'], ic50_result['HillSlope'])
    else:
        y_fit = four_pl(x_fit, 0, ic50_result['Top'],
                        ic50_result['logIC50'], ic50_result['HillSlope'])
    ax.plot(x_fit, y_fit, '-', color='red', label='4PL fit')

    # IC50 标注
    ic50_log = ic50_result['logIC50']
    ic50_val = ic50_result['IC50_uM']
    ci_low, ci_high = ic50_result['IC50_95CI_uM']
    ax.axvline(ic50_log, color='gray', linestyle='--', alpha=0.7)
    ax.text(ic50_log, 0.5, f'IC50 = {ic50_val:.2f} μM\n95% CI: {ci_low:.2f}–{ci_high:.2f}',
            rotation=90, va='center', ha='right', fontsize=8)

    ax.set_xlabel('log10(dose) [μM]')
    ax.set_ylabel('Inhibition fraction')
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc='best', fontsize=8)
    ax.set_title('Dose-response curve (示意值，需真实数据验证)')
    plt.tight_layout()
    plt.savefig(output_pdf, format='pdf')
    plt.savefig(output_pdf.replace('.pdf', '.svg'), format='svg')
    plt.close()

if __name__ == '__main__':
    import pandas as pd
    # 示例数据（示意值，需真实数据验证）
    df = pd.DataFrame({
        'log10_dose_uM': [-2, -1, 0, 1, 2, 3],
        'inhibition_fraction': [0.03, 0.06, 0.22, 0.55, 0.88, 0.95],
        'sd': [0.01, 0.02, 0.05, 0.08, 0.04, 0.03]
    })
    ic50_result = {
        'model': '4PL', 'Bottom': 0.03, 'Top': 0.96,
        'logIC50': 0.85, 'IC50_uM': 7.08, 'HillSlope': 1.12,
        'IC50_95CI_uM': [5.25, 9.55]
    }
    plot_dose_response(df, ic50_result, 'dose_response.pdf')
