#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown一括変換ツール
ディレクトリ内の全JSONファイルを再帰的にMarkdownに変換

【設計思想】
- シンプルさ重視：to_markdown.py の機能を再利用、重複コードを避ける
- 安全性重視：エラーが出ても処理を続行し、最後にまとめて報告
- 利便性重視：ツリー構造を維持、Obsidian vaultへの直接出力も可能

【前提条件】
- Python 3.x 環境
- 入力：split_conversations.py で分割されたJSONファイル群
- to_markdown.py と同じディレクトリに配置（import するため）

【処理の流れ】
1. 入力ディレクトリを再帰的に探索
2. *.json ファイルを検出（index.json は除外）
3. 各JSONファイルに対して to_markdown.py の関数を呼び出し
4. 出力ディレクトリに同じツリー構造で .md ファイルを生成
5. 処理結果をサマリー表示

【なぜツリー構造を維持するのか】
- 入力：raw/2024/01/2024-01-15-会話.json
- 出力：markdown/2024/01/2024-01-15-会話.md
→ 年月別に整理された状態を保つことで、管理しやすい

【なぜ batch が必要か】
- 1,200+ファイルを1つずつ処理するのは非効率
- エラーハンドリングの一元化
- 進捗表示による処理状況の把握
"""

import sys
from pathlib import Path
from to_markdown import generate_markdown


def batch_convert(input_dir: str, output_dir: str):
    """
    ディレクトリ内の全JSONファイルを一括変換
    
    【この関数の全体的な流れ】
    1. 入力ディレクトリの存在確認
    2. 再帰的にJSONファイルを検索（index.json除く）
    3. 各JSONファイルをループ処理：
       a. 出力先パスを計算（ツリー構造維持）
       b. 出力先ディレクトリを作成
       c. to_markdown.generate_markdown() を呼び出し
       d. 成功/失敗をカウント
    4. 処理結果をサマリー表示
    5. ログファイル出力
    
    【エラーハンドリング方針】
    - 個別のファイルでエラーが出ても処理を続行
    - エラー内容を記録
    - 最後にエラーファイル一覧を表示（最大10件）
    → 1,200+ファイルのうち数個のエラーで全体が止まるのを防ぐ
    
    【進捗表示】
    - 10件ごとに進捗を表示
    - 大量のファイル処理時に「フリーズしてない」ことを確認できる
    
    【ログファイル】
    - 処理中の INFO/WARNING/ERROR を conversion_log.txt に記録
    - ターミナル上では進捗のみ表示
    - 詳細はログファイルで確認
    
    Args:
        input_dir: 入力ディレクトリ（相対/絶対パス対応）
        output_dir: 出力ディレクトリ（相対/絶対パス対応）
    """
    print("="*80)
    print("Markdown一括変換ツール")
    print("="*80)
    
    # 【ステップ1】入力ディレクトリの確認
    # Path オブジェクトに変換（パス操作が簡単になる）
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # 入力ディレクトリの存在確認
    if not input_path.exists():
        print(f"エラー: 入力ディレクトリが見つかりません: {input_dir}")
        sys.exit(1)
    
    # 入力がディレクトリかチェック
    if not input_path.is_dir():
        print(f"エラー: 入力はディレクトリではありません: {input_dir}")
        sys.exit(1)
    
    print(f"\n入力: {input_path}")
    print(f"出力: {output_path}")
    
    # ログファイルの準備
    log_file = Path("conversion_log.txt")
    log_entries = []  # ログエントリを一時保存
    
    print(f"\nJSONファイル検索中...", end="", flush=True)
    
    # 【ステップ2】JSONファイルを再帰的に検索
    # rglob("*.json") で、サブディレクトリも含めて全ての .json ファイルを検索
    # rglob = recursive glob（再帰的なワイルドカード検索）
    json_files = []
    for json_file in input_path.rglob("*.json"):
        # index.json は除外
        # 理由：index.json はメタデータファイルで、会話ログではない
        if json_file.name != "index.json":
            json_files.append(json_file)
    
    print(f" 完了！ ({len(json_files)}ファイル)\n")
    
    # ファイルが1つも見つからなかった場合
    if len(json_files) == 0:
        print("変換対象のJSONファイルが見つかりませんでした")
        return  # 処理終了
    
    # 【ステップ3】変換処理のメインループ
    # 統計情報
    total_files = len(json_files)  # 読み込んだファイル数
    success_count = 0  # 成功したファイル数
    warning_count = 0  # 警告が出たファイル数
    error_count = 0    # エラーが発生したファイル数
    error_files = []   # エラーファイルの情報を記録
    
    # デバッグ用カウンタ
    info_file_count = 0  # INFO が出たファイル数
    no_output_count = 0  # 何も出力しなかったファイル数
    
    # enumerate() でインデックス番号付きループ
    # i: 1から始まる番号（進捗表示用）
    # json_file: 現在処理中のJSONファイルのPathオブジェクト
    for i, json_file in enumerate(json_files, 1):
        try:
            # 【ステップ3-a】相対パスを計算
            # 入力ディレクトリからの相対パスを取得
            # 例：
            #   input_path = raw/
            #   json_file = raw/2024/01/2024-01-15-会話.json
            #   relative_path = 2024/01/2024-01-15-会話.json
            relative_path = json_file.relative_to(input_path)
            
            # 【ステップ3-b】出力先パスを生成（ツリー構造維持）
            # 相対パスを保持したまま、拡張子を .md に変更
            # 例：
            #   output_path = markdown/
            #   relative_path = 2024/01/2024-01-15-会話.json
            #   output_file = markdown/2024/01/2024-01-15-会話.md
            output_file = output_path / relative_path.with_suffix('.md')
            
            # 【ステップ3-c】出力先ディレクトリ作成
            # 出力ファイルの親ディレクトリを取得
            # 例：markdown/2024/01/
            # parents=True: 親ディレクトリも含めて作成
            # exist_ok=True: 既存でもエラーにしない
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 【ステップ3-d】変換実行
            # to_markdown.py の generate_markdown() 関数を呼び出し
            # str() でPathオブジェクトを文字列に変換
            
            # 標準出力をキャプチャするため、一時的にリダイレクト
            import io
            import contextlib
            
            # 標準出力をバッファに保存
            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                generate_markdown(str(json_file), str(output_file))
            
            # キャプチャした出力を解析
            captured_output = output_buffer.getvalue()
            
            # デバッグ: 出力が空のファイルをカウント
            if not captured_output.strip():
                no_output_count += 1
            
            # INFO メッセージをログに記録
            has_warning = False
            for line in captured_output.split('\n'):
                if line.strip():
                    # ログレベル（INFO:, 警告: など）を先頭に配置
                    # 元の形式: [ファイル名] INFO: メッセージ
                    # 新しい形式: INFO: [ファイル名] メッセージ
                    if line.startswith('INFO:') or line.startswith('警告:'):
                        # すでにログレベルがある場合
                        log_entries.append(f"{line.split(':')[0]}: [{json_file.name}] {':'.join(line.split(':')[1:]).strip()}")
                    else:
                        # ログレベルがない場合はそのまま
                        log_entries.append(f"[{json_file.name}] {line}")
                    
                    if 'INFO:' in line:
                        has_warning = True
            
            # 成功カウント
            success_count += 1
            if has_warning:
                warning_count += 1
                info_file_count += 1  # デバッグ用
            
            # 進捗表示（10件ごと、または最後のファイル）
            # 10件ごとに表示することで、処理が進んでいることを確認できる
            # 最後のファイル（i == len(json_files)）も必ず表示
            if i % 10 == 0 or i == total_files:
                print(f"  進捗: {i}/{total_files} ({success_count}成功, {warning_count}警告, {error_count}エラー)")
        
        except Exception as e:
            # 【エラーハンドリング】
            # 個別のファイルでエラーが発生しても処理を続行
            error_count += 1
            
            # エラー情報を記録
            # ファイル名とエラーメッセージを保存
            error_files.append({
                'file': str(json_file),  # ファイルパス
                'error': str(e)          # エラーメッセージ
            })
            
            # ログにも記録
            log_entries.append(f"[ERROR] {json_file.name}: {e}")
            
            # エラーが出ても次のファイルへ進む
            continue
    
    # 【ステップ4】ログファイル出力
    if log_entries:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("Markdown一括変換ログ\n")
            f.write("="*80 + "\n\n")
            for entry in log_entries:
                f.write(entry + "\n")
        print(f"\nログファイル: {log_file}")
    
    # 【ステップ5】結果表示
    print("\n" + "="*80)
    print("変換完了")
    print("="*80)
    print(f"読込: {total_files}ファイル")
    print(f"成功: {success_count}ファイル")
    print(f"\n出力先: {output_path}/")
    print(f"警告: {warning_count}")
    print(f"エラー: {error_count}")
    
    # エラーがあった場合の詳細表示
    if error_count > 0:
        print(f"\nエラーファイル一覧:")
        
        # エラーファイルを最大10件まで表示
        # 理由：大量のエラーが出た場合、全て表示すると見づらい
        for err in error_files[:10]:
            print(f"  {err['file']}")
            print(f"    -> {err['error']}")
        
        # 10件以上エラーがある場合、残りの件数を表示
        if len(error_files) > 10:
            print(f"  ... 他 {len(error_files) - 10}件")
    
    # デバッグ情報を表示
    print(f"\n【デバッグ情報】")
    print(f"INFO が出たファイル: {info_file_count}")
    print(f"出力が空のファイル: {no_output_count}")
    print(f"差分: {total_files - info_file_count} (total - info)")
    print(f"警告カウント: {warning_count} (should equal info_file_count)")
    
    print("="*80)


def main():
    """
    メイン関数
    
    【この関数の役割】
    コマンドライン引数を処理して、batch_convert() を呼び出す
    
    【使い方】
    python3 batch_convert.py <入力ディレクトリ> <出力ディレクトリ>
    
    例：
    python3 batch_convert.py raw/ markdown/
    python3 batch_convert.py raw/ /Users/username/ObsidianVaults/Vault01/GPT_LOG/
    python3 batch_convert.py raw/2026/02/ test_output/
    
    【相対パスと絶対パス】
    どちらも使用可能：
    - 相対パス：raw/ markdown/
    - 絶対パス：/Users/username/raw/ /Users/username/markdown/
    - 混在も可：raw/ /Users/username/ObsidianVaults/GPT_LOG/
    
    【Obsidian vault への直接出力】
    出力ディレクトリにObsidian vaultのパスを指定することで、
    変換結果を直接Obsidianで閲覧可能にできる
    """
    # コマンドライン引数の数をチェック
    # sys.argv[0] はスクリプト名自体
    # sys.argv[1] が入力ディレクトリ
    # sys.argv[2] が出力ディレクトリ
    if len(sys.argv) < 3:
        # 引数が足りない場合、使い方を表示して終了
        print("使い方: python3 batch_convert.py <入力ディレクトリ> <出力ディレクトリ>")
        print("\n例:")
        print("  python3 batch_convert.py raw/ markdown/")
        print("  python3 batch_convert.py raw/ /path/to/output/")
        print("\n説明:")
        print("  入力ディレクトリ内の全JSONファイル（index.json除く）を再帰的に検索し、")
        print("  ツリー構造を維持したまま出力ディレクトリにMarkdownファイルを生成します。")
        sys.exit(1)  # エラーコード1で終了
    
    # コマンドライン引数から取得
    input_dir = sys.argv[1]   # 入力ディレクトリ
    output_dir = sys.argv[2]  # 出力ディレクトリ
    
    # 一括変換を実行
    batch_convert(input_dir, output_dir)


# このスクリプトが直接実行された場合のみ main() を呼び出す
# 他のスクリプトから import された場合は実行されない
if __name__ == "__main__":
    main()
