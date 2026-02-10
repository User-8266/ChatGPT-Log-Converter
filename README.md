# ChatGPT-Log-Converter

**Note: These documents are written in Japanese.**

ChatGPTのconversations.jsonを.mdに変換するPythonスクリプト群です。
動作環境はMac OS 26上で動くPython 3.9.6となります。

コードを書いたのはウチのAIチームのclaudeです。

## ユーザーズ・ノート

初めて一括エクスポートした時に「何じゃあ、こりゃ！？」ってなりましてね。chat.htmlから切り分けてくれるスクリプトを探したんですけど、無かったんですよ。  
仕方ないので自分とこのAIに作らせました。  
最初はもっと多機能な単一スクリプトで動くやつが完成間近だったんですけど、あまりにも巨大になりすぎて、ちょっとした修正でもclaudeが沼るようになったので、封印。イチから作り直す事にしました。

なお、ガッチガチにハードコーティングされてます。ライセンスはCC0ですので、お手持ちのAIさんにカスタマイズしてもらってご利用いただくのがよろしいと思われます。

## スクリプト構成

詳しい使い方は[manual.md](./manual.md)に書かれています。

- [split_conversations.py](./split_conversations.py)
	- ChatGPTの「一括エクスポート」機能で入手できるconversations.jsonを1スレッド1ファイルに切り分けるスクリプトです。
- [to_markdown.py](./to_markdown.py)
	- 切り分けた .json ファイルを .md に変換するスクリプトです。
- [batch_convert.py](./batch_convert.py)
	- to_markdown.pyをバッチ処理にかけ、指定したフォルダ内（サブフォルダを含む）のindex.json以外の全ての .json を .md に変換します。
- [json_analyzer_deep.py](./json_analyzer_deep.py)
	- スクリプト作成のために作ったconversations.json分析スクリプトその1です。
- [json_analyzer_priority.py](./json_analyzer_priority.py)
	- スクリプト作成のために作ったconversations.json分析スクリプトその2です。

## テキスト

- [manual.md](./manual.md)
	- スクリプト群の使い方が書かれています。「よくわからない」人用のコーナーもあります。
- [technical_notes.md](technical_notes.md)
	- claudeによるテクニカル・ノートです。
- [designers_notes.md](./designers_notes.md)
	- claudeによるデザイナーズ・ノートです。

## 免責事項

- スクリプトの動作は、これを保証しない。
- 投稿者は、バグフィックスおよびバージョンアップの義務を負わない。
- スクリプトを書いたのはAIなので、実行前に精査する事を強く奨める。

### 注意事項

claudeくんが「これも書いた方がいいですよ」だってさ。

- 元データ（conversations.json）のバックアップを取ってから実行すること。
- 変換されたMarkdownファイルには会話内容がそのまま含まれる。公開・共有時は個人情報やセンシティブな内容に注意すること。
- Python 3.x 環境での動作を想定。他環境での動作は未検証。
- OpenAIがエクスポート形式を変更した場合、動作しなくなる可能性がある。

## バージョン履歴

- v1.0
	- 初版リリース

[End of File]
