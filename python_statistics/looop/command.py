import argparse
import learning
import calendar_maker
import mpx


def learn(args):
    """
    予測用モデルから予測値を取得
    """
    learning.learn(args.start_date, args.end_date, args.var_lag)


def make_calendar(args):
    """通常カレンダーの取得と整形"""
    calendar_maker.make()


def make_mpx(args):
    """通常カレンダーの取得と整形"""
    mpx.make()


def get_parser():
    """
    コマンド引数のparser
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # 学習
    learning_parser = subparsers.add_parser('learn', help='予測モデル学習用')
    learning_parser.add_argument("--start_date", required=True,
                                 help="翌日の日付を入力してください(yyyy-mm-dd)")
    learning_parser.add_argument("--end_date", required=True,
                                 help="翌々日の日付を入力してください(yyyy-mm-dd)")
    learning_parser.add_argument("--var_lag", type=int,
                                 default=learning.VAR_LAG_DEFAULT,
                                 help="modelのパラメータ")
    learning_parser.set_defaults(func=learn)

    # カレンダー
    calendar_parser = subparsers.add_parser('calendar', help='通常カレンダー作成用')
    calendar_parser.set_defaults(func=make_calendar)

    # MPXファイル整形
    mpx_parser = subparsers.add_parser("mpx",
                                       help="MPX Excelでのダウンロード後データの整形")
    mpx_parser.set_defaults(func=make_mpx)

    return parser


def main():
    """
    looop用Entry point
    """
    parser = get_parser()
    args = parser.parse_args()
    print("コマンド実行開始", args)
    args.func(args)
    print("コマンド実行完了")


if __name__ == '__main__':
    main()
