import argparse

from app.pipeline.orchestrator import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="Run the GitStories story-extraction pipeline for a repo.")
    parser.add_argument("--repo", required=True, help="owner/name, e.g. PaperMC/Paper")
    parser.add_argument("--force", action="store_true", help="bypass cache and re-run all passes")
    args = parser.parse_args()

    bundles = run_pipeline(args.repo, force=args.force)
    print(f"\nDone. {len(bundles)} story bundles ready for {args.repo}.")


if __name__ == "__main__":
    main()
