import pandas as pd
from sklearn.model_selection import train_test_split

def prepare_dataset(df: pd.DataFrame, test_size: float = 0.2, random_state: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filters out rejected rows and performs a stratified train/test split 
    based on the carbon_risk_class.
    """
    # 1. Filter out rejected rows
    valid_df = df[df["quality_flag"] != "rejected"].copy()
    
    # 2. Check if we have enough data to stratify
    # (If a class has only 1 row, train_test_split will crash)
    class_counts = valid_df["carbon_risk_class"].value_counts()
    if any(class_counts < 2):
        raise ValueError("Cannot stratify: Not enough samples in one or more carbon_risk_class categories.")

    # 3. Perform the stratified split
    train_df, test_df = train_test_split(
        valid_df,
        test_size=test_size,
        random_state=random_state,
        stratify=valid_df["carbon_risk_class"]
    )
    
    return train_df, test_df