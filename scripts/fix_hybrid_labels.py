import pandas as pd
import json

df = pd.read_csv('data/external/hybrid_seed.csv')
labels = df[['payer_id', 'label']].drop_duplicates()
truth = {
    'schema_version': '1.0',
    'dataset': 'hybrid_seed',
    'accounts': {}
}

for i, row in labels.iterrows():
    if pd.notnull(row['label']) and row['label'] != 'LEGIT':
        truth['accounts'][row['payer_id']] = {'label': row['label'], 'groups': []}

with open('data/external/truth_hybrid_seed.json', 'w') as f:
    json.dump(truth, f, indent=2)

df.drop(columns=['label'], inplace=True, errors='ignore')
df.to_csv('data/external/hybrid_seed.csv', index=False)
print("Extracted truth to data/external/truth_hybrid_seed.json and removed label from data/external/hybrid_seed.csv")
