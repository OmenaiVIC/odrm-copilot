import pandas as pd
from sklearn.model_selection import train_test_split  # type: ignore


def prepare_dataset(
    df: pd.DataFrame, test_size: float = 0.2, random_state: int = 7
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filters out rejected rows and performs a stratified train/test split
    based on the carbon_risk_class.
    """
    valid_df = df[df["quality_flag"] != "rejected"].copy()

    class_counts = valid_df["carbon_risk_class"].value_counts()
    if any(class_counts < 2):
        raise ValueError(
            "Cannot stratify: Not enough samples in one or more carbon_risk_class categories."
        )

    train_df, test_df = train_test_split(
        valid_df,
        test_size=test_size,
        random_state=random_state,
        stratify=valid_df["carbon_risk_class"],
    )

    return train_df, test_df
