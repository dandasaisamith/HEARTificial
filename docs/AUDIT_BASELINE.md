### git status
On branch main
Your branch is up to date with 'origin/main'.

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	.agents/
	.gitignore
	AGENTS.md
	CLAUDE.md
	DISCLOSURE.md
	Makefile
	README.md
	SCOPE.md
	WALKTHROUGH.md
	app/
	audit.py
	config.yaml
	data/
	docs/
	pyproject.toml
	requirements.lock.txt
	requirements.txt
	sai.md
	src/
	tests/

nothing added to commit but untracked files present (use "git add" to track)



### git log
a028a8d Initial commit



### pytest
..................................................                       [100%]
50 passed in 4.90s



### eval_results.csv
seed_file,seed,n_transactions,n_accounts,n_fraud_accounts,n_review_accounts,n_groups,ring_full,ring_partial,ring_missed,ring_recall_full,fp_legit_hv_fraud_only,fp_legit_hv_fraud_or_review,precision_fraud,recall_fraud,precision_at_10,precision_at_50,pr_auc,elapsed_s,latency_per_tx_ms,degraded_stages
seedA,42,45332,2005,3,203,78,5,0,0,5/5,0,0,0.0,0.0,0.4,0.34,0.3698,80.71,1.78,none
seedB,7,45023,2005,10,240,51,5,0,0,5/5,0,1,0.6,0.2727,0.3,0.38,0.4239,80.555,1.789,none
seedC,2026,45220,2005,11,227,57,6,0,0,6/6,0,1,0.3636,0.1905,0.0,0.38,0.3357,63.041,1.394,none
demo_small,42,5186,602,5,159,20,2,0,0,2/2,0,0,0.6,0.3,0.5,0.16,0.395,7.151,1.379,none


### UI Smoke
EXCEPTIONS: []

2026-10-07 10:41:47.431 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
Asset not found: C:\Users\Danda Sai Samith\HEARTificial\HEARTificial\app\assets\vis-network.min.css (using fallback)
Asset not found: C:\Users\Danda Sai Samith\HEARTificial\HEARTificial\app\assets\vis-network.min.js (using fallback)
2026-10-07 10:42:29.323 Please replace `st.components.v1.html` with `st.iframe`.

`st.components.v1.html` will be removed after 2026-06-01.


### Determinism
Hash1: ec4f068092a679018c4d0b0ecd5452b71dca25abebb5e2527a4fa345b8aa0a75
Hash2: ec4f068092a679018c4d0b0ecd5452b71dca25abebb5e2527a4fa345b8aa0a75
Equal: True

### Timing
Demo small: 14.70s (0.00283s/tx)
Seed A: 30.00s (0.00066s/tx)

### C1: tx-level decisions with ledger >= 1: True