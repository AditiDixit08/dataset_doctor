"""Creates sample_messy.csv: a dataset with problems planted on purpose."""
import numpy as np
import pandas as pd
rng = np.random.default_rng(42)
n = 1000
df = pd.DataFrame({
 "customer_id": range(1, n + 1),
 "age": rng.integers(18, 70, n).astype(float),
 "city": rng.choice(["Pune", "pune", "Mumbai", "Delhi", " Pune"], n),
 "income": rng.normal(50000, 12000, n).round(0),
 "spend_text": rng.integers(100, 5000, n).astype(str), # numbers stored as text
 "referral_code": rng.choice(["A1", "B2", "C3"], n),
 "country": "India", # same value everywhere
})
# Put a few 'unknown' strings in spend_text so it stays text when saved to CSV
df.loc[rng.choice(n, 30, replace=False), "spend_text"] = "unknown"
# Plant outliers (absurdly high incomes)
df.loc[rng.choice(n, 15, replace=False), "income"] = 900000
# A column that is just income in thousands (highly correlated twin)
df["income_k"] = df["income"] / 1000
# Plant missing values
df.loc[rng.choice(n, 120, replace=False), "age"] = np.nan
df.loc[rng.choice(n, 250, replace=False), "income"] = np.nan
df.loc[rng.choice(n, 600, replace=False), "referral_code"] = np.nan
# Plant drift: orders jump in the second half of the data
half = n // 2
df["orders"] = np.concatenate([rng.poisson(3, half), rng.poisson(6, n - half)])
# Plant 40 duplicate rows
df = pd.concat([df, df.sample(40, random_state=1)]).reset_index(drop=True)
df.to_csv("sample_messy.csv", index=False)
print("Saved sample_messy.csv with", len(df), "rows")