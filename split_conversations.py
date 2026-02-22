#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conversations.json分割ツール
スレッドごとにJSON分割 + インデックス生成

【設計思想】
- シンプルさ重視：1スレッド = 1ファイル という分かりやすい構造
- 安全性重視：エラーが出ても処理を続行し、最後にまとめて報告
- 保守性重視：日付別ディレクトリで整理、index.jsonで全体把握

【前提条件】
- Python 3.x 環境
- 入力：ChatGPTからエクスポートした conversations.json
- 出力：raw/YYYY/MM/YYYY-MM-DD-タイトル.json の階層構造

【処理の流れ】
1. conversations.json を読み込み（全スレッドの配列）
2. 各スレッドを個別のJSONファイルとして出力
3. ファイル名にはスレッド作成日とタイトルを使用
4. 日付別ディレクトリに整理（raw/YYYY/MM/）
5. index.json を生成（全スレッドのメタデータ）

【なぜ分割するのか】
- メモリ効率：1,200+スレッドを毎回読み込むのは重い
- 処理速度：1スレッドだけ処理・再処理が高速
- デバッグ：問題のあるスレッドを特定しやすい
- 並列処理：将来的な高速化の余地
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import re


def sanitize_filename(title: str, max_length: int = 50) -> str:
    """
    ファイル名として使えない文字を除去し、適切な長さに調整
    
    【なぜこの処理が必要か】
    ChatGPTのスレッドタイトルには、ファイル名として使えない文字が含まれる場合がある：
    - スラッシュ（/）：ディレクトリの区切りと解釈される
    - コロン（:）：Windowsで使用不可
    - アスタリスク（*）、疑問符（?）：ワイルドカードと解釈される
    - その他の特殊文字
    
    【処理の具体例】
    元のタイトル：「2024/01/15の質問：どうすれば良い？」
    処理後：「20240115の質問どうすれば良い」
    
    Args:
        title: 元のタイトル（ChatGPTのスレッドタイトル）
        max_length: 最大文字数（デフォルト50文字）
    
    Returns:
        サニタイズされたファイル名
        空になった場合は "untitled" を返す
    """
    # 【ステップ1】ファイル名として使えない文字を除去
    # 正規表現で以下の文字を空文字に置換：
    # / \ : * ? " < > |
    invalid_chars = r'[/\\:*?"<>|]'
    sanitized = re.sub(invalid_chars, '', title)
    
    # 【ステップ2】前後の空白を除去
    # 例："  タイトル  " → "タイトル"
    sanitized = sanitized.strip()
    
    # 【ステップ3】空になった場合の処理
    # すべての文字が除去された場合は "untitled" を返す
    if not sanitized:
        return "untitled"
    
    # 【ステップ4】長すぎる場合は切り詰め
    # ファイル名が長すぎるとOSによってはエラーになる
    # また、長すぎると可読性が下がる
    if len(sanitized) > max_length:
        # 指定文字数で切り詰め、末尾の空白を除去
        sanitized = sanitized[:max_length].rstrip()
    
    return sanitized


def get_conversation_dates(conv: dict) -> tuple:
    """
    スレッドの作成日時と更新日時を取得
    
    【create_time と update_time】
    ChatGPTのエクスポートデータには2つの日時情報がある：
    - create_time：スレッドが最初に作成された日時
    - update_time：スレッドが最後に更新された日時
    
    【index.jsonでの活用】
    update_timeを記録することで、異なるエクスポート間での比較が可能：
    - index2026-01-29.json と index2026-02-06.json を比較
    - update_timeが変わっているスレッド = 更新されたスレッド
    - 新しく追加されたスレッドも検出可能
    
    Args:
        conv: 会話データ（1スレッド分の辞書）
    
    Returns:
        (create_time, update_time) のタプル
        どちらもUnixタイムスタンプ（秒）、存在しない場合はNone
    """
    # 会話データから create_time を取得
    # get() メソッドを使うことで、キーが存在しない場合も None が返る
    create_time = conv.get('create_time')
    
    # 会話データから update_time を取得
    update_time = conv.get('update_time')
    
    # タプルとして返す
    # 例：(1740795968.038276, 1740796063.328279)
    return create_time, update_time


def split_conversations(json_path: str, output_base: str = "raw"):
    """
    conversations.jsonを分割
    
    【この関数の全体的な流れ】
    1. conversations.json を読み込み（全スレッドの配列）
    2. 出力先ディレクトリを準備
    3. 各スレッドをループ処理：
       a. 日付情報を取得
       b. ファイル名を生成
       c. ディレクトリ構造を作成
       d. JSONファイルとして出力
       e. index用データを記録
    4. index.json を生成
    5. 処理結果をサマリー表示
    
    【エラーハンドリング方針】
    - 個別のスレッドでエラーが出ても処理を続行
    - エラーカウントを記録
    - 最後にまとめて報告
    → 1,200+スレッドのうち数個のエラーで全体が止まるのを防ぐ
    
    Args:
        json_path: 入力JSONファイルパス（相対/絶対パス対応）
        output_base: 出力先ベースディレクトリ名（デフォルト: "raw"）
                    ハードコーディング箇所：ここを変更すると出力先が変わる
    """
    print("="*80)
    print("conversations.json 分割ツール")
    print("="*80)
    
    # 【ステップ1】入力ファイル読み込み
    # Path オブジェクトに変換（パス操作が簡単になる）
    input_path = Path(json_path)
    
    # ファイルの存在確認
    if not input_path.exists():
        # ファイルが存在しない場合、エラーメッセージを表示して終了
        print(f"エラー: ファイルが見つかりません: {json_path}")
        sys.exit(1)  # エラーコード1で終了
    
    print(f"\n入力ファイル: {input_path}")
    print("読み込み中...", end="", flush=True)
    
    # JSONファイルを開いて読み込む
    # encoding='utf-8' で日本語などのマルチバイト文字に対応
    with open(input_path, 'r', encoding='utf-8') as f:
        # JSONをPythonのリストに変換
        # conversations.json の構造：[{スレッド1}, {スレッド2}, ...]
        data = json.load(f)
    
    # 読み込み完了を表示（スレッド数も表示）
    print(f" 完了！ ({len(data)}スレッド)\n")
    
    # 【ステップ2】出力先ディレクトリ準備
    # 入力ファイルと同じディレクトリ内に output_base ディレクトリを作成
    # 例：conversations.json と同じ場所に raw/ ディレクトリ
    base_dir = input_path.parent / output_base
    
    # ディレクトリを作成（既に存在する場合はそのまま）
    # exist_ok=True により、既存ディレクトリでもエラーにならない
    base_dir.mkdir(exist_ok=True)
    
    print(f"出力先: {base_dir}/")
    print(f"処理中...\n")
    
    # 【ステップ3】各スレッドの処理ループ
    # index.json 用のデータを格納するリスト
    index_data = []
    
    # 統計情報
    success_count = 0  # 成功したスレッド数
    error_count = 0    # エラーが発生したスレッド数
    
    # enumerate() で インデックス番号付きループ
    # i: 1から始まる番号（進捗表示用）
    # conv: 1スレッド分のデータ
    for i, conv in enumerate(data, 1):
        try:
            # 【ステップ3-a】日付情報取得
            create_time, update_time = get_conversation_dates(conv)
            
            # create_time が存在しない場合はスキップ
            # 理由：ファイル名の生成に create_time が必須
            if create_time is None:
                print(f"  警告: スレッド#{i} - create_timeがありません（スキップ）")
                error_count += 1
                continue  # 次のスレッドへ
            
            # 【ステップ3-b】日付変換とファイル名生成
            # Unixタイムスタンプを datetime オブジェクトに変換
            create_dt = datetime.fromtimestamp(create_time)
            
            # 年月日を文字列として抽出
            # strftime() で指定フォーマットに変換
            year = create_dt.strftime("%Y")   # 例：2024
            month = create_dt.strftime("%m")  # 例：01（ゼロパディング）
            day = create_dt.strftime("%d")    # 例：15（ゼロパディング）
            
            # タイトル取得とサニタイズ
            # get() でキーが存在しない場合も 'untitled' を返す
            title = conv.get('title', 'untitled')
            # ファイル名として使える形に変換
            safe_title = sanitize_filename(title)
            
            # ファイル名の生成: YYYY-MM-DD-タイトル.json
            # 例：2024-01-15-プログレとパンクの関係.json
            filename = f"{year}-{month}-{day}-{safe_title}.json"
            
            # 【ステップ3-c】ディレクトリ作成
            # raw/YYYY/MM/ の階層構造を作成
            year_dir = base_dir / year        # 例：raw/2024/
            month_dir = year_dir / month      # 例：raw/2024/01/
            
            # ディレクトリを再帰的に作成
            # parents=True: 親ディレクトリも含めて作成
            # exist_ok=True: 既存でもエラーにしない
            month_dir.mkdir(parents=True, exist_ok=True)
            
            # 【ステップ3-d】出力パスの決定と重複対策
            output_path = month_dir / filename
            
            # 同名ファイルがある場合は番号を付ける
            # 例：同じ日に同じタイトルのスレッドが複数ある場合
            # 2024-01-15-タイトル.json
            # 2024-01-15-タイトル_1.json
            # 2024-01-15-タイトル_2.json
            counter = 1
            original_output_path = output_path
            while output_path.exists():
                # ファイル名（拡張子なし）を取得
                stem = original_output_path.stem
                # 番号を付けた新しいファイル名を生成
                output_path = original_output_path.parent / f"{stem}_{counter}.json"
                counter += 1
            
            # 【ステップ3-e】JSON出力
            # スレッドデータをJSONファイルとして出力
            # ensure_ascii=False: 日本語をそのまま出力（\uXXXX にしない）
            # indent=2: 読みやすいように整形（2スペースインデント）
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(conv, f, ensure_ascii=False, indent=2)
            
            # 【ステップ3-f】インデックスデータ追加
            # base_dir からの相対パスを計算
            # 例：base_dir が raw/ の場合、2024/01/2024-01-15-タイトル.json
            relative_path = output_path.relative_to(base_dir)
            
            # メッセージ数カウント
            # mapping から実際のメッセージノード数を数える
            mapping = conv.get('mapping', {})
            # message が存在するノードだけをカウント
            message_count = sum(1 for node in mapping.values() if node.get('message'))
            
            # index.json 用のエントリを作成
            # このデータを使って異なるエクスポート間での比較が可能
            index_entry = {
                "path": str(relative_path),           # ファイルパス
                "id": conv.get('id', 'unknown'),      # スレッドID
                "title": title,                       # タイトル
                "create_time": create_time,           # 作成日時
                "update_time": update_time,           # 更新日時（重要：これで変更検出）
                "message_count": message_count,       # メッセージ数
                "model": conv.get('default_model_slug')  # 使用モデル
            }
            index_data.append(index_entry)
            
            # 成功カウント
            success_count += 1
            
            # 進捗表示（100件ごと）
            # 大量のスレッドを処理する際の進捗確認用
            if i % 100 == 0:
                print(f"  処理済み: {i}/{len(data)}")
        
        except Exception as e:
            # 【エラーハンドリング】
            # 個別のスレッドでエラーが発生しても処理を続行
            # エラー内容を表示してカウント
            print(f"  エラー: スレッド#{i} - {e}")
            error_count += 1
            continue  # 次のスレッドへ
    
    # 【ステップ4】index.json 出力
    print(f"\nindex.json 生成中...", end="", flush=True)
    index_path = base_dir / "index.json"
    
    # create_time でソート（古い順）
    # これにより index.json 内のスレッドが時系列順に並ぶ
    # key=lambda: create_time が None の場合は 0 として扱う
    index_data.sort(key=lambda x: x['create_time'] if x['create_time'] else 0)
    
    # index.json をファイルとして出力
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(" 完了！")
    
    # 【ステップ5】結果表示
    print("\n" + "="*80)
    print("分割完了")
    print("="*80)
    print(f"成功: {success_count}スレッド")
    
    # エラーがあった場合のみ表示
    if error_count > 0:
        print(f"エラー: {error_count}スレッド")
    
    print(f"\n出力先: {base_dir}/")
    print(f"インデックス: {index_path}")
    print("="*80)


def main():
    """
    メイン関数
    
    【この関数の役割】
    コマンドライン引数を処理して、split_conversations() を呼び出す
    
    【使い方】
    python3 split_conversations.py <conversations.json>
    
    例：
    python3 split_conversations.py conversations.json
    python3 split_conversations.py conversations2026-02-06.json
    python3 split_conversations.py ../data/conversations.json
    
    【出力先について】
    出力先は入力ファイルと同じディレクトリ内の raw/ ディレクトリ
    これはハードコーディングされている（output_base="raw"）
    変更したい場合は split_conversations() の呼び出しを修正する
    """
    # コマンドライン引数の数をチェック
    # sys.argv[0] はスクリプト名自体なので、最低でも2つ必要
    # sys.argv[1] が入力ファイルパス
    if len(sys.argv) < 2:
        # 引数が足りない場合、使い方を表示して終了
        print("使い方: python3 split_conversations.py <conversations.json>")
        print("\n例:")
        print("  python3 split_conversations.py conversations.json")
        print("  python3 split_conversations.py conversations2026-02-06.json")
        print("  python3 split_conversations.py ../path/to/conversations.json")
        sys.exit(1)  # エラーコード1で終了
    
    # コマンドライン引数から入力ファイルパスを取得
    json_path = sys.argv[1]
    
    # 分割処理を実行
    # output_base="raw" はハードコーディング（変更したい場合はここを修正）
    split_conversations(json_path)


# このスクリプトが直接実行された場合のみ main() を呼び出す
# 他のスクリプトから import された場合は実行されない
if __name__ == "__main__":
    main()
