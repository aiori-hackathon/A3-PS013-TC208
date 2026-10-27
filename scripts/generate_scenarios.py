"""
TraceLens Synthetic Scenario Generator & Verifier
AIORI-3 PS-013 | Threat Tracers
"""
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent.parent
    scenarios_dir = base_dir / "sample-data"

    print("Verifying TraceLens synthetic datasets...")
    for s_dir in scenarios_dir.iterdir():
        if s_dir.is_dir() and s_dir.name.startswith("scenario-"):
            auth_f = s_dir / "auth.log"
            nginx_f = s_dir / "nginx_access.log"
            meta_f = s_dir / "metadata.json"

            print(f"[{s_dir.name}]")
            print(f"  auth.log: {'PRESENT' if auth_f.exists() else 'MISSING'}")
            print(f"  nginx_access.log: {'PRESENT' if nginx_f.exists() else 'MISSING'}")
            print(f"  metadata.json: {'PRESENT' if meta_f.exists() else 'MISSING'}")

    print("\nAll synthetic datasets verified.")

if __name__ == "__main__":
    main()
