import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report

# 示意数据：真实使用时请替换为错题台账 CSV
data = {
    '章节': ['存储系统','CPU','操作系统','计算机网络','数据表示','存储系统','CPU','操作系统','计算机网络','数据表示']*12,
    '知识点': ['Cache','数据通路','页面置换','TCP','浮点数','Cache','数据通路','页面置换','TCP','浮点数']*12,
    '题型': ['综合题','综合题','综合题','综合题','选择题']*24,
    '用时_分钟': np.random.uniform(2, 20, 120),
    '对错': np.random.choice([0, 1], 120, p=[0.4, 0.6])
}
df = pd.DataFrame(data)

# 描述统计：各章错误率与平均用时
def descriptive_stats(df):
    stats = df.groupby('章节').agg(
        错误率=('对错', lambda x: 1 - x.mean()),
        平均用时=('用时_分钟', 'mean'),
        样本量=('对错', 'size')
    ).reset_index()
    return stats

# 基线模型：样本量 >= 100 时使用
def baseline_model(df):
    if len(df) < 100:
        print('样本量 < 100，仅做描述统计')
        return None
    X = pd.get_dummies(df[['章节', '知识点', '题型', '用时_分钟']], drop_first=True)
    y = df['对错']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    lr = LogisticRegression(max_iter=1000)
    lr.fit(X_train, y_train)
    y_pred_lr = lr.predict(X_test)
    dt = DecisionTreeClassifier(random_state=42)
    dt.fit(X_train, y_train)
    y_pred_dt = dt.predict(X_test)
    print('逻辑回归准确率：', accuracy_score(y_test, y_pred_lr))
    print('决策树准确率：', accuracy_score(y_test, y_pred_dt))
    print('逻辑回归分类报告：\n', classification_report(y_test, y_pred_lr))
    return lr, dt

if __name__ == '__main__':
    print('描述统计：')
    print(descriptive_stats(df))
    print('\n基线模型：')
    baseline_model(df)
