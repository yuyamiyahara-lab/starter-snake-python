# 関数の実行順

ゲーム開始から終了までに呼ばれる関数の順です。見た目を返す `info` は、ゲーム開始より前に呼ばれます。

## ゲーム開始時

`start` が1回呼ばれ、最初のルートを保存します。

1. `start`
2. `_store_route`
3. `_head_and_neck`
4. `build_cycle`
   1. `_cycle_blocked`
   2. `_perimeter_ring`
      1. `_perimeter_cells`
      2. 外周を時計回りにたどる。餌で塞がれた区間では `_bridge` を呼ぶ
      3. `_bridge` は `_bfs` を呼ぶ。`_bfs` は `_neighbors` と `_reconstruct` を使う
      4. `_is_valid_cycle` で閉路かを確認する。判定には `_adjacent` を使う
   3. 頭がその閉路上にあるとき `_rotate_cycle`
   4. 頭が外周の外にあるとき `_splice_head`
      1. `_bfs` で頭から外周上のマスへの路を探す
      2. `_directed_arc` で、選んだ2マスの間の外周を取り出す
      3. `_count_perimeter` で、外周をすべて含む閉路があればそこで打ち切る
      4. 次のマスが首になる候補は除く
   5. `_count_perimeter` と `_steps_to_perimeter` で、外周マスが多く、同じなら外周へ早く着く閉路を選ぶ
5. 選んだ閉路と体長を、ゲームIDごとに保存する

`_is_perimeter` は、外周マスの数と、外周へ着くまでの手数を数えるときに使います。`_in_bounds` は、隣のマスが盤面内かを見るときに使います。

## 毎ターン

`move` が1回呼ばれます。`start` でルートを保存できていれば、通常のターンでは作り直しません。

1. `move`
2. ルートがないときだけ `_store_route`。中の呼び出しはゲーム開始時と同じ
3. 体長が前回より増えているときだけ `_store_route`。このターンは、前のターンに餌を取った次のターン
4. それ以外は、保存済みの体長を今の体長で更新するだけ
5. `_head_and_neck`
6. `_next_move_on_route`
7. `_direction` で、閉路の次のマスへの手を決める。末尾の次は先頭
8. 頭がルート上にないときだけ `_fallback_move`
   1. `_head_and_neck`
   2. `_in_bounds` で盤外の手を除く
   3. 首へ戻る手を除く
   4. 餌を踏まない手を優先し、その中から1つ選ぶ

## ゲーム終了時

`end` が1回呼ばれ、そのゲームIDのルートを捨てます。
