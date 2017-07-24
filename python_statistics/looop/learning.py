import os
import glob
import pandas as pd
from itertools import product
import statsmodels.api as sm
import statsmodels.formula.api as smf
import common
import requests
import json
import time
import calendar_maker
import mpx

VAR_LAG_DEFAULT = 9
VAR_MAX_ITER = 1000


def learn(start_date, end_date, var_lag=VAR_LAG_DEFAULT, maxiter=VAR_MAX_ITER):
    """
    予測用モデルから予測値を取得
    """
    try:
        start_date = pd.Timestamp(start_date).date()
        end_date = pd.Timestamp(end_date).date()
    except Exception as e:
        print("日付(YYYY-MM-DD)を正しく入力してください", e)
        print("start_date:", start_date)
        print("end_date:", end_date)
        return

    # データ読み込み
    jepx_spot_all = read_jepx_spot()
    imbalance = jepx_spot_all.copy()
    jepx_spot_all = preprocess_jepx_spot(jepx_spot_all)
    jikan_all = read_jepx_1hour()
    b_value = read_b_value()
    mpx_spot = mpx.read()
    total_amount = read_total_amount()
    spot_commit = read_spot_commit()

    # インバランス価格
    imbalance_all = make_imbalance(imbalance, b_value)

    # 時間前市場
    spot_time = jepx_spot_all[["time", "年月日"]]
    tenki = read_weather()
    tenki_ = pd.merge(spot_time, tenki, how="left",
                      left_on="time", right_on="年月日時").sort_values("time")
    tenki_full = tenki_.fillna(method="backfill").fillna(method="ffill")

    # 天気ダミー作成
    dummies_step1_tenki = tenki_full[["time", "天気_num_北海道",
                                      "天気_num_東エリア",
                                      "天気_num_西エリア",
                                      "天気_num_九州"]].set_index("time")
    dummies_step1_tenki = dummy_vars_weather(dummies_step1_tenki)

    # 時間帯別ダミー作成
    dummies_step2_time = make_core_time(dummies_step1_tenki)

    # 曜日ダミー作成
    dummies_full = make_dayofweek(dummies_step2_time)

    # ここでols推定を行い、ダミーの結果を取得する
    jikan = make_jikan_for_dummy(jikan_all)
    dummy_input = pd.merge(jikan, imbalance_all,
                           how="left",
                           left_index=True,
                           right_index=True).drop("kai", axis=1)
    dummy_input = pd.merge(dummy_input, dummies_full,
                           how="left", left_index=True, right_index=True)

    # ダミー変数用データの利用期間
    dummies_date = datetime_for_dummy(end_date)
    dummies_start_date = dummies_date["start"].strftime("%Y-%m-%d %H:%M:%S")
    dummies_end_date = dummies_date["end"].strftime("%Y-%m-%d %H:%M:%S")

    res_dummy_jikan = model_ols(
        dummy_input, "price", "天気_東エリア", dummies_start_date, dummies_end_date)
    res_dummy_a = model_ols(
        dummy_input, "a値", "天気_東エリア", dummies_start_date, dummies_end_date)

    """ここからVARモデルインプット用のデータセット作成"""
    # 時間前データVARモデル学習予測用
    var_input_jikan = make_jikan_for_var(jikan_all, jepx_spot_all)
    var_input_imbalance = make_var_input_imbalance(imbalance_all, spot_time)
    var_input = pd.concat([var_input_jikan, var_input_imbalance], axis=1)

    """ここからVARモデルの予測を行い、結果を得る（明日と明後日の分）"""
    res_var_jikan = learn_model(var_input, "price", var_lag, maxiter)
    res_var_a = learn_model(var_input, "a値", var_lag, maxiter)

    """それぞれの結果に対して、ダミー推定の結果を合わせて48コマに展開する。"""
    # 天気予報取得
    tenki_forcast = pd.concat(get_weather_forecast_info())

    output_jikan = prediction(res_var_jikan, res_dummy_jikan, tenki_forcast,
                              "price", "天気_東エリア",
                              start_date, end_date)[["predicted_price"]]
    output_a = prediction(res_var_a, res_dummy_a, tenki_forcast,
                          "a値", "天気_東エリア",
                          start_date, end_date)[["predicted_a値"]]

    """インバランス価格をエリア分算出する。"""
    output_imbalance = pd.merge(output_a, imbalance_all,
                                how="left",
                                left_index=True,
                                right_index=True).drop(["kai", "a値"], axis=1)
    output_imbalance = make_imbalance_price_area(output_imbalance, b_value)
    output = make_output(output_jikan)

    """価格より量を算出する。価格群のroundを取って、その語階段データに当てる。"""
    price_to_amount = read_price_to_amount()
    price_to_amount = make_price_to_amount(price_to_amount)
    output_price_amount = make_amount(
        output, mpx_spot, price_to_amount, start_date, end_date)
    output_final = pd.merge(output_price_amount, output_imbalance,
                            how="left",
                            left_index=True,
                            right_index=True)

    """需要量を計算に含める"""
    output_final = output_amount_area_expansion(output_final, output)
    total_amount = make_total_amount(total_amount)
    spot_commit = make_spot_commit(spot_commit)

    output_final = calculate_imbalance_amount(output_final,
                                              spot_commit, total_amount)
    output_final = pick_up_columns(output_final)
    output_time = make_output_time(output_final)
    output_final = pd.concat([output_time, output_final], axis=1)
    output_final = lot_calculate(output_final)

    output_path = os.path.join(common.data_dir,
                               "predicted/時間前インバランス予測結果.csv")
    output_final.to_csv(output_path, index=False)

    return output_final

def lot_calculate(output_final):
    output_final["jikanmae_amount_北海道"] /= 500
    output_final["jikanmae_amount_東北"] /= 500
    output_final["jikanmae_amount_東京"] /= 500
    output_final["jikanmae_amount_中部"] /= 500
    output_final["jikanmae_amount_北陸"] /= 500
    output_final["jikanmae_amount_関西"] /= 500
    output_final["jikanmae_amount_中国"] /= 500
    output_final["jikanmae_amount_四国"] /= 500
    output_final["jikanmae_amount_九州"] /= 500

    return output_final

def datetime_for_dummy(prediction_end_date):
    dummies_start_date = pd.Timestamp(year=2016,
                                      month=prediction_end_date.month,
                                      day=1)
    dummies_end_date = dummies_start_date + \
        pd.offsets.MonthEnd() + pd.Timedelta("23:30:00")

    return {"start": dummies_start_date,
            "end": dummies_end_date}


def make_amount(output, mpx_spot, price_to_amount_2, start_date, end_date):
    mpx_spot = make_mpx_spot(mpx_spot, start_date, end_date)
    output_2 = pd.merge(output, mpx_spot,
                        how="left", left_index=True, right_index=True)
    output_2_round = output_2.round()

    # 東エリア
    output_3 = pd.merge(output_2_round.reset_index(),
                        price_to_amount_2[
                            ["システムプライス", "jikan_price",
                             "jikan_amount_interpolated_adjusted"]],
                        how="left",
                        left_on=["システムプライス", "jikanmae_price_東エリア"],
                        right_on=["システムプライス", "jikan_price"])
    rename_columns = {
        "jikan_amount_interpolated_adjusted": "jikanmae_amount_東エリア"
    }
    output_3 = output_3.rename(columns=rename_columns).drop(["jikan_price"],
                                                            axis=1)
    # 西エリア
    output_3 = pd.merge(output_3,
                        price_to_amount_2[
                            ["システムプライス", "jikan_price",
                             "jikan_amount_interpolated_adjusted"]],
                        how="left",
                        left_on=["システムプライス", "jikanmae_price_西エリア"],
                        right_on=["システムプライス", "jikan_price"])
    rename_columns = {
        "jikan_amount_interpolated_adjusted": "jikanmae_amount_西エリア"
    }
    output_3 = output_3.rename(columns=rename_columns).drop(["jikan_price"],
                                                            axis=1)
    # 北海道
    output_3 = pd.merge(output_3,
                        price_to_amount_2[
                            ["システムプライス", "jikan_price",
                             "jikan_amount_interpolated_adjusted"]],
                        how="left",
                        left_on=["システムプライス", "jikanmae_price_北海道"],
                        right_on=["システムプライス", "jikan_price"])
    rename_columns = {
        "jikan_amount_interpolated_adjusted": "jikanmae_amount_北海道"
    }
    output_3 = output_3.rename(columns=rename_columns).drop(["jikan_price"],
                                                            axis=1)
    # 九州
    output_3 = pd.merge(output_3,
                        price_to_amount_2[
                            ["システムプライス", "jikan_price",
                             "jikan_amount_interpolated_adjusted"]],
                        how="left",
                        left_on=["システムプライス", "jikanmae_price_九州"],
                        right_on=["システムプライス", "jikan_price"])
    rename_columns = {
        "jikan_amount_interpolated_adjusted": "jikanmae_amount_九州"
    }
    output_3 = output_3.rename(columns=rename_columns).drop(["jikan_price"],
                                                            axis=1)

    output_3 = output_3.set_index("年月日").fillna(0)

    output_3["jikanmae_amount_東エリア_adjusted"] = output_3["jikanmae_amount_東エリア"].where(
                                                        output_3["jikanmae_price_東エリア"] - output_3["東_price"] < 0, 0)
    output_3["jikanmae_amount_西エリア_adjusted"] = output_3["jikanmae_amount_西エリア"].where(
                                                        output_3["jikanmae_price_西エリア"] - output_3["西_price"] < 0, 0)
    output_3["jikanmae_amount_北海道_adjusted"] = output_3["jikanmae_amount_北海道"].where(
                                                        output_3["jikanmae_price_北海道"] - output_3["北海道_price"] < 0, 0)
    output_3["jikanmae_amount_九州_adjusted"] = output_3["jikanmae_amount_九州"].where(
                                                        output_3["jikanmae_price_九州"] - output_3["九州_price"] < 0, 0)
    output_4 = output_3.drop(["jikanmae_amount_東エリア",
                              "jikanmae_amount_西エリア",
                              "jikanmae_amount_北海道",
                              "jikanmae_amount_九州"], axis=1)

    return output_4


def make_price_to_amount(price_to_amount):
    df = pd.melt(price_to_amount, id_vars=["システムプライス"],
                 value_vars=["4", "5", "6", "7", "8", "9", "10", "11",
                             "12", "13", "14", "15", "16", "17",
                             "20", "21", "25"],
                 var_name="jikan_price", value_name="jikan_amount")
    df = df.sort_values(by=["システムプライス", "jikan_amount",
                            "jikan_price"]).reset_index(drop="True")
    df.jikan_price = df.jikan_price.astype(int)
    df_2 = pd.DataFrame(list(
        product(range(df.システムプライス.min(), df.システムプライス.max() + 1),
                range(df.jikan_price.min(), df.jikan_price.max() + 1))
    ), columns=["システムプライス", "jikan_price"])
    df_3 = df_2.merge(df, how="left", on=list(df_2.columns))
    df_3["jikan_amount_interpolated"] = df_3.jikan_amount.interpolate()

    kaidan_list = [7, 8, 9, 10, 11, 12, 13, 14, 15, 20]
    for i in kaidan_list:
        df_3["jikan_amount_interpolated_adjusted"] = df_3["jikan_amount_interpolated"].where(df_3["システムプライス"] == i,
                                                                                             df_3["jikan_amount_interpolated"])

    df_3.loc[(df_3.システムプライス == 16), "jikan_amount_interpolated_adjusted"] = \
        df_3.jikan_amount_interpolated[df_3.システムプライス == 15].values.tolist()
    df_3.loc[(df_3.システムプライス == 17), "jikan_amount_interpolated_adjusted"] = \
        df_3.jikan_amount_interpolated[df_3.システムプライス == 15].values.tolist()

    df_3.loc[(df_3.システムプライス == 18), "jikan_amount_interpolated_adjusted"] = \
        df_3.jikan_amount_interpolated[df_3.システムプライス == 20].values.tolist()
    df_3.loc[(df_3.システムプライス == 19), "jikan_amount_interpolated_adjusted"] = \
        df_3.jikan_amount_interpolated[df_3.システムプライス == 20].values.tolist()

    return df_3


def make_mpx_spot(mpx_spot, start_date, end_date):
    mpx_spot = mpx_spot.set_index("fc_datetime")
    # mpx_spot = mpx_spot[start_date:end_date]

    return mpx_spot


def make_output_time(output):
    output_time = pd.DataFrame({
        "時刻コード": (output.index.hour * 60 + output.index.minute) / 30 + 1,
        "年月日": output.index.date}, index=output.index)

    return output_time


def make_output(output):
    output["jikanmae_price_北海道"] = output["predicted_price"] + 1.5
    output["jikanmae_price_東エリア"] = output["predicted_price"]
    output["jikanmae_price_西エリア"] = output["predicted_price"] - 0.2
    output["jikanmae_price_九州"] = output["predicted_price"] - 0.5
    output = output.drop("predicted_price", axis=1)

    return output


def prediction(res_var, res_dummy, tenki_forcast, dependent_variable,
               tenki_dummy, start_date, end_date):
    start_date = start_date - pd.Timedelta("1d")
    predict_output_day = res_var.predict(start=start_date.isoformat(),
                                         end=end_date.isoformat(),
                                         typ="levels")
    predict_output_day = predict_output_day.add_prefix("pred_")
    # ダミーを付与
    predict_dummies_step1_tenki = make_dummy_weather_forecast_info(
        predict_output_day, tenki_forcast, start_date, end_date)
    predict_dummies_step2_time = make_core_time(predict_dummies_step1_tenki)
    predict_dummies_full = make_dayofweek(predict_dummies_step2_time).rename(
        columns={tenki_dummy: "天気D"})
    output = koma_tenkai(res_dummy, predict_dummies_full, dependent_variable)
    print("finish")

    return output


def learn_model(input_df, dependent_variable, var_lag, maxiter=1000):
    var_output = sm.tsa.VARMAX(
        input_df[[dependent_variable, "kai"]], order=(var_lag, 0), trend="c")
    res_var = var_output.fit(maxiter=maxiter, disp=False)

    return res_var


def read_jepx_spot():
    """JEPX SPOT取引結果ファイル読み込み"""
    jepx_spot_filepath = os.path.join(common.data_dir,
                                      "jepx_spot/spot_*.csv")
    jepx_spot = pd.concat(common.read_csv(f, parse_dates=["年月日"])
                          for f in glob.glob(jepx_spot_filepath))

    return jepx_spot


def read_jepx_1hour():
    """JEPX時間前取引結果ファイル読み込み"""
    jikan_filepath = os.path.join(common.data_dir,
                                  "jepx_1hour/im_trade_summary_*.csv")
    df = pd.concat(common.read_csv(f, parse_dates=["年月日"])
                   for f in glob.glob(jikan_filepath))
    return df


def read_price_to_amount():
    price_to_amount_path = os.path.join(common.data_dir,
                                        "Processed/price_to_amount.csv")
    df = common.read_csv(price_to_amount_path)

    return df


def read_b_value():
    """β値ファイル読み込み"""
    b_value_filepath = os.path.join(common.data_dir,
                                    "Processed/B値.csv")
    df = common.read_csv(b_value_filepath)

    return df


def read_weather():
    path_1 = "Receipt/気象情報/札幌（天気【2016年4月1日~2017年3月30日】）.csv"
    path_3 = "Receipt/気象情報/東京（天気【2016年4月1日~2017年3月30日】）.csv"
    path_6 = "Receipt/気象情報/大阪（天気【2016年4月1日~2017年3月30日】）.csv"
    path_9 = "Receipt/気象情報/福岡（天気【2016年4月1日~2017年3月30日】）.csv"

    tenki_filepath_1 = os.path.join(common.data_dir, path_1)
    tenki_filepath_3 = os.path.join(common.data_dir, path_3)
    tenki_filepath_6 = os.path.join(common.data_dir, path_6)
    tenki_filepath_9 = os.path.join(common.data_dir, path_9)

    tenki_1 = common.read_csv(
        tenki_filepath_1, parse_dates=["年月日時"], skiprows=3)
    tenki_3 = common.read_csv(
        tenki_filepath_3, parse_dates=["年月日時"], skiprows=3)
    tenki_6 = common.read_csv(
        tenki_filepath_6, parse_dates=["年月日時"], skiprows=3)
    tenki_9 = common.read_csv(
        tenki_filepath_9, parse_dates=["年月日時"], skiprows=3)

    tenki_1 = tenki_1[["年月日時", "天気"]].rename(
        columns={"天気": "天気_num_北海道"}).drop(0)
    tenki_3 = tenki_3[["天気"]].rename(columns={"天気": "天気_num_東エリア"}).drop(0)
    tenki_6 = tenki_6[["天気"]].rename(columns={"天気": "天気_num_西エリア"}).drop(0)
    tenki_9 = tenki_9[["天気"]].rename(columns={"天気": "天気_num_九州"}).drop(0)

    tenki = pd.concat([tenki_1, tenki_3, tenki_6, tenki_9], axis=1)

    return tenki


def make_imbalance_price_area(output_imbalance, b_value):

    def make_imbalance_price(output_imbalance, b_value,
                             area_name, area_number):
        output_imbalance["imbalance_price_" + area_name] = output_imbalance["predicted_a値"] * \
            output_imbalance[f"回避可能原価{area_name}(円/kWh)"] + 1 \
            + b_value.loc[area_number]["B値"]

        return output_imbalance

    make_imbalance_price(output_imbalance, b_value, "北海道", 0)
    make_imbalance_price(output_imbalance, b_value, "東北", 1)
    make_imbalance_price(output_imbalance, b_value, "東京", 2)
    make_imbalance_price(output_imbalance, b_value, "中部", 3)
    make_imbalance_price(output_imbalance, b_value, "北陸", 4)
    make_imbalance_price(output_imbalance, b_value, "関西", 5)
    make_imbalance_price(output_imbalance, b_value, "中国", 6)
    make_imbalance_price(output_imbalance, b_value, "四国", 7)
    imb = make_imbalance_price(output_imbalance, b_value, "九州", 8).drop(
        ["predicted_a値",
         "回避可能原価北海道(円/kWh)", "回避可能原価東北(円/kWh)",
         "回避可能原価東京(円/kWh)", "回避可能原価中部(円/kWh)",
         "回避可能原価北陸(円/kWh)", "回避可能原価関西(円/kWh)",
         "回避可能原価中国(円/kWh)", "回避可能原価四国(円/kWh)",
         "回避可能原価九州(円/kWh)"], axis=1)

    return imb


def make_imbalance(jepx_spot, b_value):
    """インバランス価格 = α値*n(回避可能原価) + β  を算出する。"""

    jepx_spot["time"] = jepx_spot["年月日"] + \
        (jepx_spot["時刻コード"] - 1) * pd.Timedelta("30m")

    jepx_spot_imbalance = jepx_spot[
        ["time", "年月日", "α速報値×スポット・時間前平均価格(円/kWh)",
         "α確報値×スポット・時間前平均価格(円/kWh)",
         "スポット・時間前平均価格(円/kWh)", "エリアプライス東京(円/kWh)",
         "回避可能原価全国値(円/kWh)", "回避可能原価北海道(円/kWh)", "回避可能原価東北(円/kWh)",
         "回避可能原価東京(円/kWh)", "回避可能原価中部(円/kWh)",
         "回避可能原価北陸(円/kWh)", "回避可能原価関西(円/kWh)",
         "回避可能原価中国(円/kWh)", "回避可能原価四国(円/kWh)",
         "回避可能原価九州(円/kWh)", "買い入札量(kWh)"
         ]
    ].rename(columns={"買い入札量(kWh)": "kai"}).set_index("time")

    jepx_spot_imbalance["a値_速報"] = jepx_spot_imbalance[
        "α速報値×スポット・時間前平均価格(円/kWh)"] / jepx_spot_imbalance["スポット・時間前平均価格(円/kWh)"]
    jepx_spot_imbalance["a値_確報"] = jepx_spot_imbalance[
        "α確報値×スポット・時間前平均価格(円/kWh)"] / jepx_spot_imbalance["スポット・時間前平均価格(円/kWh)"]
    jepx_spot_imbalance["a値"] = jepx_spot_imbalance["a値_確報"].fillna(
        jepx_spot_imbalance["a値_速報"])
    jepx_spot_imbalance = jepx_spot_imbalance[
        ["回避可能原価北海道(円/kWh)", "回避可能原価東北(円/kWh)",
         "回避可能原価東京(円/kWh)", "回避可能原価中部(円/kWh)",
         "回避可能原価北陸(円/kWh)", "回避可能原価関西(円/kWh)",
         "回避可能原価中国(円/kWh)", "回避可能原価四国(円/kWh)",
         "回避可能原価九州(円/kWh)", "kai", "a値"]]

    return jepx_spot_imbalance


def can_adjust(model_res, dummy_name):
    threshold = 0.05
    index = model_res.pvalues.index
    return dummy_name in index and \
        model_res.pvalues[dummy_name] <= threshold


def koma_tenkai(dummies_model_res, df30, dependent_variable):
    """"推定結果を48コマに分割する"""
    df300 = df30.copy()
    adjusted_price = df300["pred_" + dependent_variable]

    # ダミー変数の存在確認してから価格調整
    dummy_value = "曇"
    dummy_name = f"C(天気D)[T.{dummy_value}]"
    if can_adjust(dummies_model_res, dummy_name):
        mock = adjusted_price + dummies_model_res.params[dummy_name]
        adjusted_price = mock.where(df300.天気D == dummy_value, adjusted_price)

    dummy_value = "雨"
    dummy_name = f"C(天気D)[T.{dummy_value}]"
    if can_adjust(dummies_model_res, dummy_name):
        mock = adjusted_price + dummies_model_res.params[dummy_name]
        adjusted_price = mock.where(df300.天気D == dummy_value, adjusted_price)

    dummy_value = "コア1"
    dummy_name = f"C(時間D)[T.{dummy_value}]"
    if can_adjust(dummies_model_res, dummy_name):
        mock = adjusted_price + dummies_model_res.params[dummy_name]
        mock = mock.where(df300.時間D == dummy_value, adjusted_price)
        adjusted_price = mock.where((df300.時間D == dummy_value) & (df300.曜日 == "平日"),
                                    adjusted_price)

    dummy_value = "コア2"
    dummy_name = f"C(時間D)[T.{dummy_value}]"
    if can_adjust(dummies_model_res, dummy_name):
        mock = adjusted_price + dummies_model_res.params[dummy_name]
        adjusted_price = mock.where((df300.時間D == dummy_value) & (df300.曜日 == "平日"),
                                    adjusted_price)

    dummy_value = "コア3"
    dummy_name = f"C(時間D)[T.{dummy_value}]"
    if can_adjust(dummies_model_res, dummy_name):
        mock = adjusted_price + dummies_model_res.params[dummy_name]
        mock = mock.where(df300.時間D == dummy_value, adjusted_price)
        adjusted_price = mock.where(
            (df300.時間D == dummy_value) & (
                (df300.曜日 == "平日") | (df300.曜日 == "土曜")), adjusted_price)

    dummy_value = "コア4"
    dummy_name = f"C(時間D)[T.{dummy_value}]"
    if can_adjust(dummies_model_res, dummy_name):
        mock = adjusted_price + dummies_model_res.params[dummy_name]
        adjusted_price = mock.where(df300.時間D == dummy_value, adjusted_price)

    dummy_value = "コア5"
    dummy_name = f"C(時間D)[T.{dummy_value}]"
    if can_adjust(dummies_model_res, dummy_name):
        mock = adjusted_price + dummies_model_res.params[dummy_name]
        adjusted_price = mock.where(df300.時間D == dummy_value, adjusted_price)

    dummy_value = "コア6"
    dummy_name = f"C(時間D)[T.{dummy_value}]"
    if can_adjust(dummies_model_res, dummy_name):
        mock = adjusted_price + dummies_model_res.params[dummy_name]
        adjusted_price = mock.where((df300.時間D == dummy_value) & (df300.曜日 == "平日"),
                                    adjusted_price)

    dummy_value = "コア7"
    dummy_name = f"C(時間D)[T.{dummy_value}]"
    if can_adjust(dummies_model_res, dummy_name):
        mock = adjusted_price + dummies_model_res.params[dummy_name]
        adjusted_price = mock.where((df300.時間D == dummy_value) & (df300.曜日 == "平日"),
                                    adjusted_price)

    dummy_value = "平日"
    dummy_name = f"C(曜日)[T.{dummy_value}]"
    if can_adjust(dummies_model_res, dummy_name):
        mock = adjusted_price + dummies_model_res.params[dummy_name]
        adjusted_price = mock.where(df300.曜日 == dummy_value, adjusted_price)

    dummy_value = "日祝"
    dummy_name = f"C(曜日)[T.{dummy_value}]"
    if can_adjust(dummies_model_res, dummy_name):
        mock = adjusted_price + dummies_model_res.params[dummy_name]
        adjusted_price = mock.where(df300.曜日 == dummy_value, adjusted_price)

    df300["predicted_" + dependent_variable] = adjusted_price

    return df300


def dummy_vars_weather(dummies_step2_time):
    """天気カテゴリ作成
    """
    category = {
        1: "晴れ",
        2: "晴れ",
        3: "晴れ",
        4: "曇",
        10: "雨",
        11: "雨",
        12: "雨",
        15: "雨",
    }
    tenki_dummies_1 = dummies_step2_time["天気_num_北海道"].map(
        category).rename("天気_北海道")
    tenki_dummies_3 = dummies_step2_time["天気_num_東エリア"].map(
        category).rename("天気_東エリア")
    tenki_dummies_6 = dummies_step2_time["天気_num_西エリア"].map(
        category).rename("天気_西エリア")
    tenki_dummies_9 = dummies_step2_time["天気_num_九州"].map(
        category).rename("天気_九州")

    return pd.concat([tenki_dummies_1, tenki_dummies_3,
                      tenki_dummies_6, tenki_dummies_9], axis=1)


def hour_category(hour):
    core_ranges = {
        1: [0, 1, 2, 3, 4, 5],
        2: [7, 8],
        3: [11, 14],
        4: [12, 13],
        5: [17, 18, 19],
        6: [20, 21],
        7: [22, 23],
    }
    core_time = 0
    for core, hours in core_ranges.items():
        if hour in hours:
            core_time = core
            break
    return "コア" + str(core_time)


def make_core_time(dummies_step1_tenki):
    """時間帯カテゴリ作成"""
    dummies_step1_tenki["月"] = dummies_step1_tenki.index.month
    hour = pd.Series(dummies_step1_tenki.index.hour,
                     index=dummies_step1_tenki.index)
    dummies_step1_tenki["時間D"] = hour.apply(hour_category)

    return dummies_step1_tenki


def make_dayofweek(dummies_dayofweek):
    """曜日カテゴリ作成"""
    dummies_full = dummies_dayofweek.copy()

    df_calendar = calendar_maker.special_calendar()
    df_calendar["年月日"] = pd.to_datetime(df_calendar["年月日"], format="%Y-%m-%d")
    df_calendar = df_calendar[["trend", "年月日"]]
    dummies_full = pd.merge(dummies_full,
                            df_calendar,
                            how="left",
                            left_index=True,
                            right_on="年月日").fillna(method="ffill")
    dummies_full["曜日"] = dummies_full["trend"]
    dummies_full = dummies_full.drop(["trend"], axis=1).set_index("年月日")

    return dummies_full


def model_ols(df, dependent_variable, tenki_dummy,
              dummies_start_date, dummies_end_date):

    df = df[dummies_start_date: dummies_end_date]
    df = df.rename(columns={tenki_dummy: "天気D"})
    dummies_model = smf.ols(
        dependent_variable + "~ C(天気D) + C(時間D) + C(曜日)", data=df)
    dummies_model_res = dummies_model.fit(maxiter=1000, desp=False)

    return dummies_model_res


def preprocess_jepx_spot(jepx_spot):
    """ここから価格データの加工と天気データの加工"""
    data = jepx_spot[[
        "年月日", "買い入札量(kWh)", "エリアプライス北海道(円/kWh)", "エリアプライス東京(円/kWh)",
        "エリアプライス関西(円/kWh)", "エリアプライス九州(円/kWh)", "時刻コード"]].fillna(0)
    data = data.rename(
        columns={"買い入札量(kWh)": "kai", "エリアプライス北海道(円/kWh)": "price_1",
                 "エリアプライス東京(円/kWh)": "price_3", "エリアプライス関西(円/kWh)": "price_6",
                 "エリアプライス九州(円/kWh)": "price_9"})
    data["time"] = data["年月日"] + (data["時刻コード"] - 1) * pd.Timedelta("30m")
    data.index = data.time

    return data


def make_jikan_for_dummy(jikan):
    jikan["time"] = jikan["年月日"] + (jikan["時刻コード"] - 1) * pd.Timedelta("30m")
    jikan = jikan[["time", "終値（円/kWh）"]
                  ].set_index("time").rename(columns={"終値（円/kWh）": "price"})

    return jikan


def make_jikan_for_var(jikan, jepx_spot):
    """時間前"""
    jikan["time"] = jikan["年月日"] + (jikan["時刻コード"] - 1) * pd.Timedelta("30m")
    jikan_1 = jikan.drop(["時刻コード", "始値（円/kWh）", "高値（円/kWh）",
                          "安値（円/kWh）", "平均（円/kWh）", "約定件数",
                          "約定量合計（MWh/h）"], axis=1)
    jikan_1 = jikan_1.set_index("time").rename(columns={"終値（円/kWh）": "price"})
    jikan_day = jikan_1.reset_index().groupby("年月日").mean()
    jikan_day_m = jikan_day.reset_index()

    jepx_spot_copy = jepx_spot.copy()
    jepx_spot_copy.index = jepx_spot_copy.年月日
    jepx_spot_copy = jepx_spot_copy[["年月日", "kai"]]
    spot_day_m = jepx_spot_copy.groupby("年月日", as_index=False).mean()

    jikan_day = pd.merge(spot_day_m, jikan_day_m, how="left", on="年月日")
    jikan_day = jikan_day.set_index("年月日")

    return jikan_day


def make_var_input_imbalance(imbalance, spot_time):

    def imbalance_day(imbalance, spot_time):
        imbalance = pd.merge(imbalance, spot_time, how="left",
                             left_index=True, right_index=True)
        imbalance_day = imbalance.groupby("年月日").mean()

        return imbalance_day

    imb_a_varinput = imbalance_day(imbalance[["a値"]], spot_time)

    return imb_a_varinput


def normalize_halex_forecast_info(json_info):
    weather_jp = {
        100: "晴れ",
        200: "曇",
        300: "雨",
        400: "雪",
        500: "みぞれ",
    }
    weather_jp_for_analysis = {
        100: "晴れ",
        200: "曇",
        300: "雨",
        400: "雨",
        500: "雨",
    }
    for dt, value in json_info.items():
        df = pd.io.json.json_normalize(value)
        df["予測天気"] = df["weatherForecast"].astype(int).map(weather_jp)
        df["予測天気分析用"] = df["weatherForecast"].astype(
            int).map(weather_jp_for_analysis)
        df["予測日時"] = pd.Timestamp(dt)
        yield df


def make_dummy_weather_forecast_info(predict_output_day, tenki_forcast,
                                     start_date, end_date):
    start_date = start_date + pd.Timedelta("1d")
    end_date = end_date + pd.Timedelta("1d")

    tenki_forcast = tenki_forcast.pivot(
        index="予測日時", columns="統合エリア名", values="予測天気分析用")
    # コマ区切りのdatetimeのみを取得
    time_koma = make_time_koma(tenki_forcast)

    predict_output_koma = pd.merge(time_koma, predict_output_day,
                                   how="left",
                                   left_index=True, right_index=True)
    predict_output_koma = predict_output_koma.fillna(method="ffill")

    predict_output_koma = predict_output_koma[start_date:end_date].drop(
        ["date", "datetime"], axis=1)
    return pd.merge(predict_output_koma, tenki_forcast,
                    how="left",
                    left_index=True, right_index=True).fillna(method="ffill")


def get_weather_forecast_info():
    access_key = "L001-D7jk6TDf"
    area_location = {
        "天気_北海道": {"longitude": "141.354376", "latitude": "43.062096"},
        "天気_東エリア": {"longitude": "139.691706", "latitude": "35.689488"},
        "天気_西エリア": {"longitude": "135.502165", "latitude": "34.693837"},
        "天気_九州": {"longitude": "130.401716", "latitude": "33.590355"},
    }
    for area_name, location in area_location.items():
        longitude = location["longitude"]
        latitude = location["latitude"]
        url = "http://fspweb01.halex.co.jp:8080/" \
            f"wimage/hpd?sid=wimage72-service&rem=all&key={access_key}&" \
            f"lat={latitude}&lon={longitude}"

        # 取得先負荷軽減のため必ず１秒待つ
        response = requests.get(url)
        time.sleep(1)

        http_json = json.loads(response.text)
        weather_forecast = pd.concat(
            normalize_halex_forecast_info(http_json["ForecastInfos"]))
        weather_forecast["統合エリア名"] = area_name
        yield weather_forecast


def make_time_koma(df):
    """天気予報のデータが出力の日付を決める。（本日から数えて次の日と、その次の日）"""
    df_time = df.copy()
    dt_index = pd.date_range(start=df_time.index.min(),
                             end=df_time.index.max() + pd.Timedelta("30m"),
                             freq="30min")
    dt_df = pd.DataFrame({
        "date": dt_index.date,
        "datetime": dt_index,
    }, index=dt_index)
    dt_df.head()

    return dt_df


def read_total_amount():
    total_amount_filepath = os.path.join(
        common.data_dir,
        "Receipt/計画値_集計（201607～201704）修正版/計画値_集計（201607～201704）修正版.csv")

    df = common.read_csv(total_amount_filepath, parse_dates=["時間"])

    return df


def make_total_amount(total_amount):
    total_amount = total_amount.pivot(index='時間', columns='エリア',
                                      values='需要予測量[kWh]')
    map_columns = {
        1: "total_amount_北海道",
        2: "total_amount_東北",
        3: "total_amount_東京",
        4: "total_amount_中部",
        5: "total_amount_北陸",
        6: "total_amount_関西",
        7: "total_amount_中国",
        8: "total_amount_四国",
        9: "total_amount_九州",
    }
    return total_amount.rename(columns=map_columns)


def read_spot_commit():
    spot_commit_filepath = os.path.join(common.data_dir,
                                        "Receipt/抽出データ_修正/Looop_スポット_約定.csv")

    df = common.read_csv(spot_commit_filepath, parse_dates=["日時"])

    return df


def make_spot_commit(spot_commit):
    spot_commit = spot_commit[["日時", "エリア", "約定量"]]
    spot_commit = spot_commit.groupby(["日時", "エリア"])["約定量"].sum().to_frame()
    spot_commit = spot_commit.reset_index()
    spot_commit = spot_commit.pivot(index="日時", columns="エリア",
                                    values="約定量").fillna(0)
    map_columns = {
        1: "commit_amount_北海道",
        2: "commit_amount_東北",
        3: "commit_amount_東京",
        4: "commit_amount_中部",
        5: "commit_amount_北陸",
        6: "commit_amount_関西",
        7: "commit_amount_中国",
        8: "commit_amount_四国",
        9: "commit_amount_九州"
    }

    return spot_commit.rename(columns=map_columns)


def output_amount_area_expansion(output_final, output):
    output_final["jikanmae_price_北海道"] = output[["jikanmae_price_北海道"]]
    output_final["jikanmae_price_東北"] = output[["jikanmae_price_東エリア"]]
    output_final["jikanmae_price_東京"] = output[["jikanmae_price_東エリア"]]
    output_final["jikanmae_price_中部"] = output[["jikanmae_price_西エリア"]]
    output_final["jikanmae_price_北陸"] = output[["jikanmae_price_西エリア"]]
    output_final["jikanmae_price_関西"] = output[["jikanmae_price_西エリア"]]
    output_final["jikanmae_price_中国"] = output[["jikanmae_price_西エリア"]]
    output_final["jikanmae_price_四国"] = output[["jikanmae_price_西エリア"]]
    output_final["jikanmae_price_九州"] = output[["jikanmae_price_九州"]]

    output_final["jikanmae_amount_北海道"] = output_final[["jikanmae_amount_北海道_adjusted"]] * 500
    output_final["jikanmae_amount_東北"] = output_final[["jikanmae_amount_東エリア_adjusted"]] * 500
    output_final["jikanmae_amount_東京"] = output_final[["jikanmae_amount_東エリア_adjusted"]] * 500
    output_final["jikanmae_amount_中部"] = output_final[["jikanmae_amount_西エリア_adjusted"]] * 500
    output_final["jikanmae_amount_北陸"] = output_final[["jikanmae_amount_西エリア_adjusted"]] * 500
    output_final["jikanmae_amount_関西"] = output_final[["jikanmae_amount_西エリア_adjusted"]] * 500
    output_final["jikanmae_amount_中国"] = output_final[["jikanmae_amount_西エリア_adjusted"]] * 500
    output_final["jikanmae_amount_四国"] = output_final[["jikanmae_amount_西エリア_adjusted"]] * 500
    output_final["jikanmae_amount_九州"] = output_final[["jikanmae_amount_九州_adjusted"]] * 500

    return output_final


def calculate_imbalance_amount(output_final, spot_commit, total_amount):
    def calculate(output_final, area_name):
        output_final["imbalance_amount_" + area_name] = \
            output_final["total_amount_" + area_name] -\
            output_final["commit_amount_" + area_name] * 500 -\
            output_final["jikanmae_amount_" + area_name]
        return output_final

    output_final = pd.merge(output_final, spot_commit,
                            how="left",
                            left_index=True,
                            right_index=True)
    output_final = pd.merge(output_final, total_amount,
                            how="left",
                            left_index=True,
                            right_index=True)

    output_final = calculate(output_final, "北海道")
    output_final = calculate(output_final, "東北")
    output_final = calculate(output_final, "東京")
    output_final = calculate(output_final, "中部")
    output_final = calculate(output_final, "北陸")
    output_final = calculate(output_final, "関西")
    output_final = calculate(output_final, "中国")
    output_final = calculate(output_final, "四国")
    output_final = calculate(output_final, "九州")

    return output_final


def pick_up_columns(output_final):
    output_final = output_final[
        ["jikanmae_price_北海道", "jikanmae_price_東北",
         "jikanmae_price_東京", "jikanmae_price_中部",
         "jikanmae_price_北陸", "jikanmae_price_関西",
         "jikanmae_price_中国", "jikanmae_price_四国",
         "jikanmae_price_九州",
         "jikanmae_amount_北海道", "jikanmae_amount_東北",
         "jikanmae_amount_東京", "jikanmae_amount_中部",
         "jikanmae_amount_北陸", "jikanmae_amount_関西",
         "jikanmae_amount_中国", "jikanmae_amount_四国",
         "jikanmae_amount_九州",
         "imbalance_price_北海道", "imbalance_price_東北",
         "imbalance_price_東京", "imbalance_price_中部",
         "imbalance_price_北陸", "imbalance_price_関西",
         "imbalance_price_中国", "imbalance_price_四国",
         "imbalance_price_九州",
         "imbalance_amount_北海道", "imbalance_amount_東北",
         "imbalance_amount_東京", "imbalance_amount_中部",
         "imbalance_amount_北陸", "imbalance_amount_関西",
         "imbalance_amount_中国", "imbalance_amount_四国",
         "imbalance_amount_九州"]
    ]

    output_final = output_final.mask(output_final < 0, 0)
    output_final = output_final.round({
         "jikanmae_price_北海道":2, "jikanmae_price_東北":2,
         "jikanmae_price_東京":2,   "jikanmae_price_中部":2,
         "jikanmae_price_北陸":2,   "jikanmae_price_関西":2,
         "jikanmae_price_中国":2,   "jikanmae_price_四国":2,
         "jikanmae_price_九州":2,
         "imbalance_price_北海道":2, "imbalance_price_東北":2,
         "imbalance_price_東京":2,   "imbalance_price_中部":2,
         "imbalance_price_北陸":2,   "imbalance_price_関西":2,
         "imbalance_price_中国":2,   "imbalance_price_四国":2,
         "imbalance_price_九州":2
    })

    return output_final
