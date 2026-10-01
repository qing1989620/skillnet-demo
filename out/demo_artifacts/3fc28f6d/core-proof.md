# 核心命题严格证明文本

## 命题 1（弱大数定律）
设 \(X_1, X_2, \dots\) 为 i.i.d. 随机变量，\(E[X_i] = \mu\)，\(\text{Var}(X_i) = \sigma^2 < \infty\)。则样本均值 \(\bar{X}_n = \frac{1}{n}\sum_{i=1}^n X_i\) 依概率收敛于 \(\mu\)。

**证明**：由 Chebyshev 不等式，对任意 \(\epsilon > 0\)，
\[ P(|\bar{X}_n - \mu| \ge \epsilon) \le \frac{\text{Var}(\bar{X}_n)}{\epsilon^2} = \frac{\sigma^2}{n\epsilon^2} \to 0 \]
当 \(n \to \infty\)。故 \(\bar{X}_n \xrightarrow{P} \mu\)。

**收敛模式**：依概率收敛。
**所用定理**：Chebyshev 不等式（适用条件：方差有限）。

## 命题 2（中心极限定理）
在命题 1 条件下，\(\sqrt{n}(\bar{X}_n - \mu) \xrightarrow{d} N(0, \sigma^2)\)。

**证明**：令 \(Y_i = (X_i - \mu)/\sigma\)，则 \(E[Y_i]=0\)，\(\text{Var}(Y_i)=1\)。特征函数 \(\phi_{Y}(t) = 1 - t^2/2 + o(t^2)\)。则 \(\phi_{\sqrt{n}\bar{Y}}(t) = [\phi_Y(t/\sqrt{n})]^n \to e^{-t^2/2}\)。由 Lévy 连续性定理，\(\sqrt{n}\bar{Y} \xrightarrow{d} N(0,1)\)。

**收敛模式**：依分布收敛。
**所用定理**：Lévy 连续性定理、泰勒展开（适用条件：二阶矩有限）。

## 命题 3（积分交换）
若 \(f_n \to f\) 且 \(|f_n| \le g\)，\(E[g] < \infty\)，则 \(\lim E[f_n] = E[f]\)。

**证明**：由控制收敛定理直接得。
**收敛模式**：几乎处处收敛 + 控制收敛。
**所用定理**：控制收敛定理（适用条件：控制函数可积）。

**注：证明为方案级文本，具体推导需根据实际估计量调整。**
