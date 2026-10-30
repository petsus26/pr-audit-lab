import argparse

from extract import run_extract
from transform import run_transform
from utils import OUTPUT_DIR

def save_report(df):
    """Write the final report as both CSV and Parquet."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = OUTPUT_DIR / "pr_audit_report.csv"
    parquet_path = OUTPUT_DIR / "pr_audit_report.parquet"

  
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_parquet(parquet_path, index=False)

    print(f"Report saved to {csv_path} and {parquet_path}")

def main():
    parser = argparse.ArgumentParser(description="Audit merged GitHub PRs for review and required checks.")
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Reuse existing raw data in data/raw/ instead of calling the GitHub API",
    )
    args = parser.parse_args()

    if not args.skip_extract:
        run_extract()

    df = run_transform()
    save_report(df)


if __name__ == "__main__":
    main()