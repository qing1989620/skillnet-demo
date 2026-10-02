import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.stats import t

# 4PL 模型
def four_pl(x, bottom, top, log_ic50, hill_slope):
    return bottom + (top - bottom) / (1 + 10 ** ((log_ic50 - x) * hill_slope))

# 3PL 模型（Bottom 固定为 0）
def three_pl_bottom0(x, top, log_ic50, hill_slope):
    return top / (1 + 10 ** ((log_ic50 - x) * hill_slope))

def fit_and_plot(csv_path='clean_dose_response.csv', output_pdf='dose_response_curve.pdf'):
    """
    读取干净数据，拟合 4PL/3PL，绘制出版级剂量-响应曲线。
    注意：示例数据为示意值，需真实数据验证。
    """
    df = pd.read_csv(csv_path)
    # 仅使用 qc_flag == 'ok' 的数据
    df = df[df['qc_flag'] == 'ok'].copy()
    x = df['log10_dose'].values
    y = df['response'].values

    # 初始值
    bottom0 = np.min(y)
    top0 = np.max(y)
    log_ic500 = np.median(x)
    hill0 = 1.0

    # 拟合 4PL
    popt4, pcov4 = curve_fit(four_pl, x, y, p0=[bottom0, top0, log_ic500, hill0], maxfev=10000)
    # 拟合 3PL（Bottom 固定为 0）
    popt3, pcov3 = curve_fit(lambda x, top, log_ic50, hill: three_pl_bottom0(x, top, log_ic50, hill),
                             x, y, p0=[top0, log_ic500, hill0], maxfev=10000)

    # 计算 IC50 与置信区间（4PL）
    log_ic50_4 = popt4[2]
    ic50_4 = 10 ** log_ic50_4
    # 残差标准误
    resid = y - four_pl(x, *popt4)
    rse = np.sqrt(np.sum(resid ** 2) / (len(y) - len(popt4)))
    # 95% CI（近似）
    ci = 1.96 * rse

    # 绘图
    fig, ax = plt.subplots(figsize=(6, 4.5))
    # 散点
    ax.scatter(x, y, color='black', label='Data', zorder=3)
    # 拟合曲线
    x_fit = np.linspace(min(x), max(x), 200)
    y_fit = four_pl(x_fit, *popt4)
    ax.plot(x_fit, y_fit, color='red', label='4PL fit')
    # 置信带（示意，基于残差标准误）
    ax.fill_between(x_fit, y_fit - ci, y_fit + ci, color='red', alpha=0.2, label='95% CI')
    # 标注 IC50
    ax.axvline(log_ic50_4, color='blue', linestyle='--', label=f'IC50 = {ic50_4:.2f} μM')
    ax.set_xlabel('log10(dose) [μM]')
    ax.set_ylabel('Inhibition fraction')
    ax.set_title('Dose-response curve (4PL fit)')
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_pdf, format='pdf')
    plt.savefig(output_pdf.replace('.pdf', '.svg'), format='svg')
    print(f'IC50 = {ic50_4:.3f} μM (示意值，需真实数据验证)')
    print(f'HillSlope = {popt4[3]:.3f}')
    print(f'Top = {popt4[1]:.3f}, Bottom = {popt4[0]:.3f}')
    print(f'RSE = {rse:.4f}')

if __name__ == '__main__':
    # 示例调用：需先准备 clean_dose_response.csv
    fit_and_plot('clean_dose_response.csv', 'dose_response_curve.pdf')
