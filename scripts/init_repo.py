import os
import pathlib

# CC-V2 Monorepo Structure Definition
STRUCTURE = {
    "adapters": ["alpaca", "tiingo"],
    "agent": ["analyst", "risk", "execution", "macro"],
    "api": ["routes", "dependencies"],
    "core": ["config", "database", "logger", "security"],
    "infra": ["docker", "k8s"],
    "lib": ["physics", "math", "kalman"],
    "scripts": [],
    "tests": ["unit", "integration"],
}


def init_repo():
    base_path = pathlib.Path.cwd()
    print(f"Initializing Monorepo at: {base_path}")

    for root_dir, sub_dirs in STRUCTURE.items():
        # Create Root Directory
        root_path = base_path / root_dir
        root_path.mkdir(exist_ok=True)
        (root_path / "__init__.py").touch()
        print(f"Created: {root_dir}/")

        # Create Subdirectories
        for sub in sub_dirs:
            sub_path = root_path / sub
            sub_path.mkdir(exist_ok=True)
            (sub_path / "__init__.py").touch()
            print(f"  Created: {root_dir}/{sub}/")

    print("Monorepo scaffolding complete.")


if __name__ == "__main__":
    init_repo()
