import os
import pandas as pd
import common


def make():
    """通常カレンダーの作成
    http://calendar-service.net/api.php から取得したデータをもとに作成

    このプログラムは利用サイト(終了年月の継続可能性が確実ではない、
    かつ取得内容が変更されるかもしれないので実行結果を
    保証できません。

    そのため、2037年までのデータを一括で取得しています。
    今後、祝日が変更や追加された際には、
    data/fixed_calendar.csv を修正してください。

    ※このプログラムを実行する際は、
    ※事前にディレクトリへ整形前CSVをダウンロードしておくこと

    [選択内容]
    開始年月の入力
    終了年月の入力
    年表記：西暦
    月表記：数字のみ
    曜日評議：日本語（日、月）
    出力フォーマット：CSV
    出力内容：チェックをしない
    ゼロ埋め：チェックをする
    """
    # 年,月,日,年号,和暦,曜日,曜日番号,祝日名
    calendar_path = os.path.join(
        common.data_dir, "normal_calendar/calendar.csv")
    fixed_calendar_path = os.path.join(
        common.data_dir, "normal_calendar/fixed_calendar.csv")

    df = common.read_csv(calendar_path, encoding="utf8")

    def to_datetime(row):
        return pd.datetime(int(row["年"]),
                           int(row["月"]),
                           int(row["日"])).date()
    date = df.apply(to_datetime, axis=1)

    fixed_df = pd.DataFrame()
    fixed_df["年月日"] = date
    fixed_df["曜日"] = df["曜日"]
    fixed_df["祝日名"] = df["祝日名"]
    fixed_df["平日"] = df["曜日"].isin(list("月火水木金")).astype(int)
    fixed_df["土曜"] = (df["曜日"] == "土").astype(int)
    fixed_df["日祝"] = (
        (df["曜日"] == "日") | (df["祝日名"].notnull())
    ).astype(int)

    fixed_df.to_csv(fixed_calendar_path, index=False)


def special_calendar():
    fixed_calendar_path = os.path.join(
        common.data_dir, "normal_calendar/fixed_calendar.csv")
    special_calendar_path = os.path.join(
        common.data_dir, "special_calendar/special_calendar.csv")
    fixed = common.read_csv(fixed_calendar_path)
    sp = common.read_csv(special_calendar_path)

    fixed["年月日"] = pd.to_datetime(fixed["年月日"])
    sp["年月日"] = pd.to_datetime(sp["年月日"])
    df = fixed.merge(sp, how="left", on="年月日")

    trend = df["平日"].mask(df["平日"] == 1, "平日")
    trend = trend.mask(df["土曜"] == 1, "土曜")
    trend = trend.mask(df["日祝"] == 1, "日祝")
    trend = trend.mask(df["特別判定"].notnull(), df["特別判定"])

    df["trend"] = trend

    return df
