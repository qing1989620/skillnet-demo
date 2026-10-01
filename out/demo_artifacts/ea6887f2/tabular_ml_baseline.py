import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import lightgbm as lgb
import joblib

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

def load_data(train_path: str, test_path: str):
    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    return train, test

def build_features(train: pd.DataFrame, test: pd.DataFrame, target_col: str):
    drop_cols = [target_col, 'record_id', 'event_time']
    X_train = train.drop(columns=[c for c in drop_cols if c in train.columns])
    y_train = train[target_col]
    X_test = test.drop(columns=[c for c in drop_cols if c in test.columns])
    y_test = test[target_col] if target_col in test.columns else None
    X_train = pd.get_dummies(X_train, dummy_na=True)
    X_test = pd.get_dummies(X_test, dummy_na=True)
    X_train, X_test = X_train.align(X_test, join='left', axis=1, fill_value=0)
    return X_train, y_train, X_test, y_test

def train_baselines(X_train, y_train, X_test, y_test):
    results = []
    log_reg = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(max_iter=1000, random_state=RANDOM_SEED))
    ])
    log_reg.fit(X_train, y_train)
    pred_lr = log_reg.predict_proba(X_test)[:, 1]
    results.append({
        'model': 'LogisticRegression',
        'auc': roc_auc_score(y_test, pred_lr),
        'f1': f1_score(y_test, (pred_lr > 0.5).astype(int)),
        'accuracy': accuracy_score(y_test, (pred_lr > 0.5).astype(int))
    })
    lgbm = lgb.LGBMClassifier(
        n_estimators=300, learning_rate=0.05, num_leaves=31,
        random_state=RANDOM_SEED, n_jobs=-1
    )
    lgbm.fit(X_train, y_train)
    pred_lgb = lgbm.predict_proba(X_test)[:, 1]
    results.append({
        'model': 'LightGBM',
        'auc': roc_auc_score(y_test, pred_lgb),
        'f1': f1_score(y_test, (pred_lgb > 0.5).astype(int)),
        'accuracy': accuracy_score(y_test, (pred_lgb > 0.5).astype(int))
    })
    return results, log_reg, lgbm

def main():
    train = pd.DataFrame({
        'record_id': range(10),
        'event_time': pd.date_range('2025-01-01', periods=10),
        'feature_1': np.random.randn(10),
        'feature_2': np.random.randn(10),
        'category_1': ['A', 'B'] * 5,
        'target': [0, 1] * 5
    })
    test = train.copy()
    X_train, y_train, X_test, y_test = build_features(train, test, 'target')
    results, log_reg, lgbm = train_baselines(X_train, y_train, X_test, y_test)
    print(pd.DataFrame(results))
    joblib.dump(log_reg, 'baseline_logistic.pkl')
    joblib.dump(lgbm, 'baseline_lgbm.pkl')

if __name__ == '__main__':
    main()

# 注：示例数据为随机生成，指标结果为示意值，需真实数据验证。
