import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score, make_scorer
import lightgbm as lgb

SEED = 42
np.random.seed(SEED)

def build_preprocessor(num_cols, cat_cols):
    """构建预处理管道，仅在训练折 fit，防泄漏。"""
    num_pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    cat_pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])
    return ColumnTransformer([
        ('num', num_pipe, num_cols),
        ('cat', cat_pipe, cat_cols)
    ])

def evaluate_model(model, X, y, num_cols, cat_cols, n_splits=5):
    """5 折分层交叉验证，返回 AUC 与 F1 的均值和标准差。"""
    pre = build_preprocessor(num_cols, cat_cols)
    pipe = Pipeline([('pre', pre), ('clf', model)])
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    auc = cross_val_score(pipe, X, y, cv=cv, scoring='roc_auc')
    f1 = cross_val_score(pipe, X, y, cv=cv, scoring='f1')
    return {'auc_mean': auc.mean(), 'auc_std': auc.std(),
            'f1_mean': f1.mean(), 'f1_std': f1.std()}

def main():
    # 示例数据（示意值，需替换为真实数据）
    df = pd.DataFrame({
        'age': [25, 40, 35, np.nan, 50, 29, 41, 33, 60, 22],
        'income': [50000, 80000, 60000, 75000, np.nan, 45000, 90000, 55000, 120000, 40000],
        'city': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'B', 'A', 'C'],
        'label': [0, 1, 0, 1, 0, 0, 1, 0, 1, 0]
    })
    X = df.drop(columns=['label'])
    y = df['label']
    num_cols = ['age', 'income']
    cat_cols = ['city']

    # 基线1：逻辑回归
    lr = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=SEED)
    lr_res = evaluate_model(lr, X, y, num_cols, cat_cols)
    print('LogisticRegression:', lr_res)

    # 基线2：LightGBM
    lgbm = lgb.LGBMClassifier(
        n_estimators=200, learning_rate=0.05, num_leaves=31,
        class_weight='balanced', random_state=SEED, verbose=-1
    )
    lgb_res = evaluate_model(lgbm, X, y, num_cols, cat_cols)
    print('LightGBM:', lgb_res)

if __name__ == '__main__':
    main()
