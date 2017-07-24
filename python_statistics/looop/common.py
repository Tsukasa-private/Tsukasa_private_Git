
"""
共通コード
"""
import os
import pandas as pd

base_dir = os.path.dirname(__file__) + "/.."
data_dir = os.path.abspath(base_dir + "/data")


def read_csv(filepath, **kwargs):
    """pd.read_csv for windows/python3.6"""
    with open(filepath) as f:
        return pd.read_csv(f, **kwargs)
