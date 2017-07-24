import os
import openpyxl
import pandas as pd
import common

output_path = os.path.join(common.data_dir,
                           "mpx/MPX_DL.csv")


def make():
    """MPX ダウンロードツールのデータより、
    分析用CSVを作成
    """
    input_path = os.path.join(common.data_dir,
                              "mpx/MPX_DLツール.xlsm")
    wb = openpyxl.load_workbook(input_path)
    SHEET_NAME = "Sheet1"
    ws = wb.get_sheet_by_name(SHEET_NAME)
    START_ROWNUM = 9
    END_ROWNUM = 53048

    def cell_range_values(column):
        cell_range = ws[column + str(START_ROWNUM):column + str(END_ROWNUM)]
        return [cell.value for (cell,) in cell_range]

    mpx = pd.DataFrame()
    mpx["fc_datetime"] = cell_range_values("AS")
    mpx["システムプライス"] = cell_range_values("AQ")
    mpx["東_price"] = cell_range_values("AT")
    mpx["西_price"] = cell_range_values("AW")
    mpx["北海道_price"] = cell_range_values("AZ")
    mpx["九州_price"] = cell_range_values("BC")

    mpx = mpx.dropna()

    mpx.to_csv(output_path, index=False)
    return mpx


def read():
    """分析用CSVを読み込み"""
    return common.read_csv(output_path, parse_dates=["fc_datetime"])
