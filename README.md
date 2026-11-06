# Battlesnake Python Starter Project

## このブランチの実装（humilton-extend）

Solo向けに、餌を避けた外周優先の閉路を作り、左右の空き2マスへ迂回して閉路を拡張します。
周回をシミュレーションし、安全に進める予測区間を後ろから調べて餌への離脱地点を選びます。
餌を取った次のターンは閉路を作り直します。

- [関数の説明](function_introduction.md)：閉路作成、2マス拡張、胴体・体力予測、給餌探索の詳細
- [関数の実行順](function_execution_order.md)：ゲーム開始、毎ターン、食後、終了時の処理
- `main.py`：サーバーの入口と周回・給餌戦略
- `cycle_expansion.py`：閉路への2マス迂回の追加。実行時にはこのファイルも必要です。

### 動きをブラウザで見る（Windows・授業のSolo条件）

PowerShellを2つ開き、どちらも `starter-snake-python` を作業ディレクトリにします。
1つ目でサーバーを起動します。

```powershell
python main.py
```

2つ目で、隣の `battlesnake-cli` フォルダにある公式CLIを起動します。

```powershell
..\battlesnake-cli\battlesnake.exe play --url http://127.0.0.1:8000 -W 6 -H 6 -g solo --foodSpawnChance 0 --minimumFood 3 --browser -d 200 -r 1
```

`-d 200` はターン間の待ち時間（ミリ秒）、`-r 1` は乱数シードです。
遅く見るなら `-d 500`、別の配置なら `-r 2` などに変えます。
コードを変更したら、サーバー側を `Ctrl+C` で止めて起動し直してください。
APIのポートは既定で8000です。環境変数 `PORT` を設定している場合はCLI側のURLも合わせます。

### 検証

`starter-snake-python` で実行します。

```powershell
python -m unittest discover -s tests -v
python _route_test.py
```

`tests` は拡張・給餌予測・計画の再利用などを検証します。
`_route_test.py` は既存の閉路形状と再作成タイミングの検証です。生存ターンの測定や、全経路の自己衝突回避の証明ではありません。

### 現在の制約

- 閉路作成は胴体全体との整合を確認しません。給餌計画では胴体を動かして検証しますが、衝突予測で周回を早く打ち切り、体力が高いうちに食べる場合があります。
- 食後8手の生存経路は存在確認だけです。その経路の実行や、次の閉路への復帰までは保証しません。
- 計画を作れない場合は餌への最短経路やランダムな退避を試します。全体として常に最も遅く食べることや、最長の閉路を選ぶことは保証しません。
- 他の蛇は現在位置を障害物として扱うだけで、将来の移動は予測しません。

## 元のスタータープロジェクトの案内

An official Battlesnake template written in Python. Get started at [play.battlesnake.com](https://play.battlesnake.com).

![Battlesnake Logo](https://media.battlesnake.com/social/StarterSnakeGitHubRepos_Python.png)

This project is a great starting point for anyone wanting to program their first Battlesnake in Python. It can be run locally or easily deployed to a cloud provider of your choosing. See the [Battlesnake API Docs](https://docs.battlesnake.com/api) for more detail. 

[![Run on Replit](https://repl.it/badge/github/BattlesnakeOfficial/starter-snake-python)](https://replit.com/@Battlesnake/starter-snake-python)

## Technologies Used

This project uses [Python 3](https://www.python.org/) and [Flask](https://flask.palletsprojects.com/). It also comes with an optional [Dockerfile](https://docs.docker.com/engine/reference/builder/) to help with deployment.

## Run Your Battlesnake

Install dependencies using pip

```sh
pip install -r requirements.txt
```

Start your Battlesnake

```sh
python main.py
```

You should see the following output once it is running

```sh
Running your Battlesnake at http://0.0.0.0:8000
 * Serving Flask app 'My Battlesnake'
 * Debug mode: off
```

Open [localhost:8000](http://localhost:8000) in your browser and you should see

```json
{"apiversion":"1","author":"","color":"#888888","head":"default","tail":"default"}
```

## Play a Game Locally

Install the [Battlesnake CLI](https://github.com/BattlesnakeOfficial/rules/tree/main/cli)
* You can [download compiled binaries here](https://github.com/BattlesnakeOfficial/rules/releases)
* or [install as a go package](https://github.com/BattlesnakeOfficial/rules/tree/main/cli#installation) (requires Go 1.18 or higher)

Command to run a local game

```sh
battlesnake play -W 11 -H 11 --name 'Python Starter Project' --url http://localhost:8000 -g solo --browser
```

## Next Steps

Continue with the [Battlesnake Quickstart Guide](https://docs.battlesnake.com/quickstart) to customize and improve your Battlesnake's behavior.

**Note:** To play games on [play.battlesnake.com](https://play.battlesnake.com) you'll need to deploy your Battlesnake to a live web server OR use a port forwarding tool like [ngrok](https://ngrok.com/) to access your server locally.
