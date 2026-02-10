# ChatGPT-Log-Converterの使い方

**Note: These documents are written in Japanese.**

**「よく分からない」という方は下の方にある"## 最低限の使い方"をご覧下さい。**

## claudeによる解説

### 1. split_conversations.py

**機能**: conversations.jsonをスレッドごとに分割

**引数**:

```bash
python3 split_conversations.py <conversations.json>
```

**必須引数**:

- `<conversations.json>`: 入力ファイルパス（相対/絶対パス両対応）

**ハードコーディング**:

- 出力先: 入力ファイルと同じディレクトリ内の `raw/` ディレクトリ
- 出力構造: `raw/YYYY/MM/YYYY-MM-DD-タイトル.json`
- index.json: `raw/index.json`

**使用例**:

```bash
# 同じディレクトリにあるファイル
python3 split_conversations.py conversations.json

# 別ディレクトリ
python3 split_conversations.py ../data/conversations2026-02-06.json
```

**出力**:

```
raw/
├─ 2024/01/2024-01-15-会話.json
├─ 2026/02/2026-02-02-GPT-4o引退感想.json
└─ index.json
```

---

### 2. to_markdown.py

**機能**: 単一JSONファイルをMarkdownに変換

**引数**:

```bash
python3 to_markdown.py <input.json> [output.md]
```

**必須引数**:

- `<input.json>`: 入力JSONファイルパス

**オプション引数**:

- `[output.md]`: 出力ファイルパス（省略時は入力ファイルと同名で.md）

**ハードコーディング**:

- なし（すべて引数で指定）

**使用例**:

```bash
# 出力先自動（同じ場所に.md生成）
python3 to_markdown.py raw/2024/01/2024-01-15-会話.json

# 出力先指定
python3 to_markdown.py raw/2024/01/2024-01-15-会話.json output/test.md
```

---

### 3. batch_convert.py

**機能**: ディレクトリ内の全JSONを一括Markdown変換

**引数**:

```bash
python3 batch_convert.py <入力ディレクトリ> <出力ディレクトリ>
```

**必須引数**:

- `<入力ディレクトリ>`: 検索対象ディレクトリ（相対/絶対パス）
- `<出力ディレクトリ>`: 出力先ディレクトリ（相対/絶対パス）

**ハードコーディング**:

- `index.json` を自動除外
- ツリー構造を維持して出力

**使用例**:

```bash
# 基本
python3 batch_convert.py raw/ markdown/

# 絶対パス（Obsidian vaultへ直接出力）
python3 batch_convert.py raw/ /Users/username/ObsidianVaults/Vault01/GPT_LOG/

# サブディレクトリのみ
python3 batch_convert.py raw/2026/02/ test_output/
```

**動作**:

- 入力: `raw/2024/01/file.json`
- 出力: `markdown/2024/01/file.md`（ツリー構造維持）

---

### 4. json_analyzer_deep.py

**機能**: conversations.jsonの詳細分析

**引数**:

```bash
python3 json_analyzer_deep.py
```

**引数なし**

**ハードコーディング**:

- 入力ファイル: スクリプトと同じディレクトリの `conversations.json`

**使用方法**:

```bash
# conversations.json がある場所で実行
cd /path/to/directory/
python3 json_analyzer_deep.py
```

**注意**: ファイル名を `conversations.json` にリネームしてから実行

---

### 5. json_analyzer_priority.py

**機能**: 優先度項目の詳細分析

**引数**:

```bash
python3 json_analyzer_priority.py
```

**引数なし**

**ハードコーディング**:

- 入力ファイル: スクリプトと同じディレクトリの `conversations.json`

**使用方法**:

```bash
# conversations.json がある場所で実行
cd /path/to/directory/
python3 json_analyzer_priority.py
```

---

### 典型的なワークフロー

```bash
# 1. 分析（オプション）
python3 json_analyzer_deep.py

# 2. 分割
python3 split_conversations.py conversations2026-02-06.json
# → raw/ ディレクトリが生成される

# 3. 一括変換
python3 batch_convert.py raw/ markdown/
# または Obsidian vault へ直接
python3 batch_convert.py raw/ /Users/sakusya/ObsidianVaults/Vault01/GPT_LOG/

# 4. 個別テスト（必要に応じて）
python3 to_markdown.py raw/2024/01/2024-01-15-test.json
```

---

### ハードコーディング一覧

|スクリプト|ハードコーディング項目|変更方法|
|---|---|---|
|split_conversations.py|出力先ベース: `raw/`|コード修正が必要|
|to_markdown.py|なし|-|
|batch_convert.py|index.json除外|コード修正が必要|
|json_analyzer_deep.py|入力: `conversations.json`|コード修正が必要|
|json_analyzer_priority.py|入力: `conversations.json`|コード修正が必要|

---

### 相対パス vs 絶対パス

**すべてのスクリプトで両対応**:

```bash
# 相対パス
python3 split_conversations.py conversations.json
python3 batch_convert.py raw/ markdown/

# 絶対パス
python3 split_conversations.py /Users/sakusya/data/conversations.json
python3 batch_convert.py /Users/sakusya/raw/ /Users/sakusya/output/
```

---

## 最低限の使い方

### ① 一括エクスポート

WebブラウザでChatGPTにアクセスして、右下のユーザー名をクリック → 「設定」 → 「データ　コントロール」 → 「データをエクスポートする」  
登録したメールアドレスにダウンロードリンクが送られてきます。  
たまに送られてこない時があります。翌日あたりに再挑戦してみて下さい。

#### 一括エクスポートは「個人アカウント」でのみ有効

**少なくともBusinessプランから作成できるワークスペースには「一括エクスポート」が存在しません。** 何故だOpenAI。こういうのビジネス用途でこそ必須じゃないのか？

---

### ② zip解凍・ファイル取り出し

Mac OSの場合はOS標準搭載のアーカイブユーティリティで解凍できます。

解凍したら、中に画像ファイルやら何やらに混じって

`conversations.json`

というファイルが入っています。  
（ちなみにchat.htmlはconversations.jsonをhtmlで閲覧できるようにした「気を利かせた」存在ですが、データが肥大するとchat.htmlも肥大化し、最終的にはブラウザが拒絶反応するようになります。このchat.htmlからデータを抽出している人も居ます）

適当にフォルダを作って（**場所はよくよく吟味されたし**）conversations.jsonをコピーなり移動なりします。

---

### ③ Python 3のインストール

ガイドは皆様の所のChatGPTに丸投げします。  
ChatGPTのconversations.jsonをいじろうとしてるんだからChatGPTのアカウントくらい持ってるだろ、という短絡思考が理由のひとつ。  
もうひとつの理由は、俺もChatGPTの言われるがままにパソコン操作してPython入れたクチなんで、人様に説明するだけの十分な知識がない、というものです。確かbrewで入れたと思ったんだけどなー……。

---

### ④ スクリプトのダウンロードと配置

- [split_conversations.py](./split_conversations.py)
- [to_markdown.py](./to_markdown.py)
- [batch_convert.py](./batch_convert.py)

以上3つのファイルをconversations.jsonと同じフォルダに置きます。  
残りの2つのスクリプトはオマケなので不要です。

---

### ⑤ スクリプトの実行

ターミナルを起動して、conversations.jsonを置いた場所まで行きます。  
以下のコマンドを入力します。

```bash
python3 split_conversations.py conversations.json
```

成功すると以下のような表示になります。

```bash
【省略】

  処理済み: 900/1203
  処理済み: 1000/1203
  処理済み: 1100/1203
  処理済み: 1200/1203

index.json 生成中... 完了！

================================================================================
分割完了
================================================================================
成功: 1203スレッド

出力先: raw/
インデックス: raw/index.json
================================================================================
```

続いて以下のコマンドを入力します。

```bash
python3 batch_convert.py raw/ markdown/
```

成功時の表示は以下の通り。

```bash
【省略】

  進捗: 1180/1203 (1180成功, 0エラー)
  進捗: 1190/1203 (1190成功, 0エラー)
  進捗: 1200/1203 (1200成功, 0エラー)
  進捗: 1203/1203 (1203成功, 0エラー)

================================================================================
変換完了
================================================================================
成功: 1203ファイル

出力先: markdown/
================================================================================
```

これでconversations.jsonを置いたフォルダに `raw` と `markdown` の2つのサブフォルダが作られていると思います。  
エラーを吐くようでしたらAIにエラーメッセージを読ませる方法が手っ取り早いです。

---

### ⑥ サブフォルダの中身について

サブフォルダの階層は次のようになっています。

**raw/YYYY/MM/YYYY-MM-DD-title.json**  
YYYY = スレッド作成年  
MM = スレッド作成月  
DD = スレッド作成日  
title = スレッドタイトル

markdownフォルダの階層はrawフォルダの階層をそのまま引き継ぎます。

#### raw

conversations.jsonから1スレッド1ファイルで切り分けられた .json が格納されています。  
成果物のみ欲しい人には不要の中間ファイルなので、rawフォルダごと削除しても構いません。  
通常のテキストエディターで開けるサイズになっていると思うので、中身を覗いてみるのも一興です。裏で色々やってます。

#### markdown

成果物である .md ファイルが格納されています。

---

## 初心者向けアドバイス

### エラーが出た時は

お手元のChatGPTにエラーメッセージをコピペして「こんなエラーが出たんだけど」と質問するのが早いと思います。

### .mdファイルの読み方

閲覧だけならChromeの拡張機能ストアから `markdown` で検索して出てくるMarkdownビューワーで見る方法が手っ取り早いです。  
Chromeは入れない主義？主義じゃ仕方ない、頑張って下さい。

### .mdファイルの編集

ChatGPTのMarkdownの使い方はかなりいいかげんなので、手直ししたくなるかも知れません。  
.md の編集はMarkdown対応エディターを使います。皆様のAIさんに「お勧めのMarkdownエディターは？」みたいに質問するといいでしょう。  
俺の場合はObsidianを勧められて導入し、そのまま使い続けています。  
理由： **変に自前のデータベースに吸収せずに .md ファイルを直接編集できる。**  
過去ログを「ファイル」として扱う事が多い身には助かります。

### raw/index.jsonの使い道

index.jsonにはconversations.jsonの構造データが入っています。
これを利用して2つのconversations.jsonの内容を比較したり、メタデータを取得してファイル名を変更したり、といった事ができると思います。

### AI理解の第一歩

「AIと人間で"定義"の定義って違うの？」と質問すると、AIに対する理解がより深まるかも知れません。

### 履歴管理

作業が終わったら、

- conversations.json
- rawフォルダ
- markdownフォルダ

を、例えば以下のようにリネームします。

- conversations2026-02-10.json
- raw2026-02-10
- markdown2026-02-10

日付は一括ダウンロードで取得した日を書き込みます。  
目の前で発言が削除されたり、あるいはちゃんと出力していた事にされてしまった経験をお持ちの方は、このバージョン管理の如き履歴管理をやらずにはいられない気持ちをご理解いただけるかもしれません。

[End of File]