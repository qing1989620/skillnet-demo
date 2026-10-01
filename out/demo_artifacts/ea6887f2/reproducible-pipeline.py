import os
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import lightgbm as lgb

SEED = 42
np.random.seed(SEED)
os.environ['PYTHONHASHSEED'] = str(SEED)

def set_seed(seed=SEED):
    """固定所有随机种子，保证可复现。"""
    np.random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)

def build_pipeline(model, num_cols, cat_cols):
    """构建完整 Pipeline，预处理仅在训练折 fit。"""
    num_pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    cat_pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])
    pre = ColumnTransformer([
        ('num', num_pipe, num_cols),
        ('cat', cat_pipe, cat_cols)
    ])
    return Pipeline([('pre', pre), ('clf', model)])

def run_cv(X, y, num_cols, cat_cols, model, n_splits=5):
    """5 折分层交叉验证，返回每折 AUC。"""
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    aucs = []
    for train_idx, val_idx in cv.split(X, y):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
        pipe = build_pipeline(model, num_cols, cat_cols)
        pipe.fit(X_tr, y_tr)
        prob = pipe.predict_proba(X_val)[:, 1]
        aucs.append(roc_auc_score(y_val, prob))
    return np.array(aucs)

def main():
    set_seed()
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

    lr = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=SEED)
    lgbm = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=31,
                              class_weight='balanced', random_state=SEED, verbose=-1)

    lr_aucs = run_cv(X, y, num_cols, cat_cols, lr)
    lgb_aucs = run_cv(X, y, num_cols, cat_cols, lgbm)

    result = {
        'seed': SEED,
        'lr_auc_mean': float(lr_aucs.mean()),
        'lr_auc_std': float(lr_aucs.std()),
        'lgb_auc_mean': float(lgb_aucs.mean()),
        'lgb_auc_std': float(lgb_aucs.std()),
        'note': '示意值，需真实数据验证'
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
