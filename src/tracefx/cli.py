"""CLI entry point for TRACE-FX.

Usage:
    python -m tracefx --help
    python -m tracefx score data/seedA.csv --out reports/
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger(__name__)


def cmd_score(args: argparse.Namespace) -> int:
    """Score a CSV file and write results to out_dir."""
    from . import config as config_mod
    from . import schema as schema_mod
    from . import pipeline as pipeline_mod

    # Load config
    cfg_path = args.config if args.config else None
    try:
        cfg = config_mod.load(None, cfg_path)
    except Exception as exc:
        log.error("Failed to load config: %s", exc)
        return 1

    # Load data
    try:
        df = schema_mod.load(args.input)
    except Exception as exc:
        log.error("Failed to load input: %s", exc)
        return 1

    # Run pipeline
    log.info("Running TRACE-FX pipeline on %s (%d rows)", args.input, len(df))
    result = pipeline_mod.run(df, cfg)

    # Output
    out_dir = Path(args.out) if args.out else Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON result
    json_path = out_dir / "result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(pipeline_mod.result_to_json(result))
    log.info("Result saved to %s", json_path)

    # Save accounts CSV
    accounts_path = out_dir / "accounts.csv"
    result.accounts.to_csv(accounts_path, index=False)
    log.info("Accounts saved to %s", accounts_path)

    # Save TX CSV
    tx_path = out_dir / "transactions.csv"
    result.tx.to_csv(tx_path, index=False)
    log.info("Transactions saved to %s", tx_path)

    if args.json:
        print(pipeline_mod.result_to_json(result))
        return 0

    # Print summary
    m = result.metrics
    print(f"\n{'='*50}")
    print("TRACE-FX Results Summary")
    print(f"{'='*50}")
    print(f"Transactions:    {m['total_transactions']}")
    print(f"Accounts:        {m['total_accounts']}")
    print(f"FRAUD accounts:  {m['fraud_accounts']}")
    print(f"REVIEW accounts: {m['review_accounts']}")
    print(f"LEGIT accounts:  {m['legit_accounts']}")
    print(f"Evidence items:  {m['evidence_items']}")
    print(f"Groups:          {m['groups']}")
    print(f"Elapsed:         {m['elapsed_s']:.2f}s")
    if result.degraded:
        print(f"DEGRADED:        {', '.join(result.degraded)}")
    print(f"Output:          {out_dir}/")
    print(f"{'='*50}\n")

    if args.explain and result.groups:
        from . import explain as explain_mod
        group = result.groups[0]
        print("Top fraud group explanation:")
        print(explain_mod.chain(group))

    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    """Run evaluation on seed files."""
    from . import config as config_mod
    from . import evaluate as eval_mod

    cfg_path = args.config if args.config else None
    try:
        cfg = config_mod.load(None, cfg_path)
    except Exception as exc:
        log.error("Failed to load config: %s", exc)
        return 1

    # Find seed files
    seed_paths = []
    data_dir = Path(args.data_dir) if args.data_dir else Path("data")

    only_list = args.only.split(",") if args.only else []
    for seed_name in ["seedA", "seedB", "seedC", "demo_small", "hybrid_seed"]:
        if only_list and seed_name not in only_list:
            continue
        csv = data_dir / f"{seed_name}.csv"
        truth = data_dir / f"truth_{seed_name}.json"
        if csv.exists() and truth.exists():
            seed_paths.append((str(csv), str(truth)))

    if not seed_paths:
        log.error("No seed files found in %s. Run 'make data' first.", data_dir)
        return 1

    out_dir = Path(args.out) if args.out else Path("reports")
    df = eval_mod.report(seed_paths, cfg, out_dir=out_dir)
    print("\nEvaluation Results:")
    print(df.to_string(index=False))
    return 0


def cmd_data(args: argparse.Namespace) -> int:
    """Generate synthetic datasets."""
    from . import simulate as sim_mod

    data_dir = Path(args.data_dir) if args.data_dir else Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    datasets = [
        ("demo_small", 42, 600, 30, True),
        ("seedA", 42, 2000, 60, False),
        ("seedB", 7, 2000, 60, False),
        ("seedC", 2026, 2000, 60, False),
    ]

    for name, seed, n_acc, n_days, is_demo in datasets:
        log.info("Generating %s (seed=%d, %d accounts, %d days)...", name, seed, n_acc, n_days)
        df, truth = sim_mod.generate(seed=seed, n_accounts=n_acc, n_days=n_days, is_demo=is_demo)
        csv_path, truth_path = sim_mod.save(df, truth, data_dir, name)
        log.info("  → %s (%d rows)", csv_path, len(df))
        log.info("  → %s", truth_path)

    return 0


def main() -> int:
    """TRACE-FX command-line interface."""
    parser = argparse.ArgumentParser(
        prog="tracefx",
        description="TRACE-FX: Fraud Intelligence System",
    )

    subparsers = parser.add_subparsers(dest="command")

    # score
    score_p = subparsers.add_parser("score", help="Score a transaction CSV file")
    score_p.add_argument("input", help="Path to input CSV file")
    score_p.add_argument("--out", "-o", help="Output directory (default: reports/)")
    score_p.add_argument("--config", "-c", help="Path to overlay config.yaml", default=None)
    score_p.add_argument("--explain", "-e", action="store_true", help="Print top group explanation")
    score_p.add_argument("--json", action="store_true", help="Output JSON result to stdout")

    # eval
    eval_p = subparsers.add_parser("eval", help="Run evaluation on seed files")
    eval_p.add_argument("--data-dir", "-d", help="Data directory (default: data/)")
    eval_p.add_argument("--out", "-o", help="Output directory (default: reports/)")
    eval_p.add_argument("--config", "-c", help="Path to overlay config.yaml", default=None)
    eval_p.add_argument("--only", help="Comma-separated list of seeds to run")

    # data
    data_p = subparsers.add_parser("data", help="Generate synthetic datasets")
    data_p.add_argument("--data-dir", "-d", help="Output directory (default: data/)")

    args = parser.parse_args()

    if args.command == "score":
        return cmd_score(args)
    elif args.command == "eval":
        return cmd_eval(args)
    elif args.command == "data":
        return cmd_data(args)
    else:
        parser.print_help()
        return 0
