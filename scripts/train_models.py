import sys
from pathlib import Path
import pandas as pd

# Ensure the src directory is in the path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from odrm.ml.train import train_single_target
from odrm.ml.features import TARGETS

def main():
    dataset_path = Path("data/odrm_dataset.parquet")
    model_root = Path("models/odrm")

    if not dataset_path.exists():
        print(f"Error: Could not find dataset at {dataset_path}")
        print("Please run: .\\.venv\\Scripts\\python.exe scripts\\generate_odrm_data.py --n 10000 --seed 7")
        sys.exit(1)

    print(f"Loading dataset from {dataset_path}...")
    df = pd.read_parquet(dataset_path)
    print(f"Loaded {len(df)} rows. Training models...\n")

    for target in TARGETS:
        print(f"--- Training target: {target} ---")
        try:
            metadata = train_single_target(
                df=df,
                target=target,
                model_root=model_root,
                random_state=7
            )
            print(f"SUCCESS: {target}")
            print(f"  R²   : {metadata['metrics']['test_r2']:.4f}")
            print(f"  RMSE : {metadata['metrics']['test_rmse']:.4f}")
            print(f"  Saved: models/odrm/{target}/{metadata['model_version']}\n")
        except Exception as e:
            print(f"FAILED: {target}")
            print(f"  Reason: {e}\n")
            sys.exit(1)

    print("All models trained and passed gates successfully!")

if __name__ == "__main__":
    main()