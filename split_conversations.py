#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conversations.json分割ツール
スレッドごとにJSON分割 + インデックス生成
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import re


def sanitize_filename(title: str, max_length: int = 50) -> str:
    """
    ファイル名として使えない文字を除去し、適切な長さに調整
    
    Args:
        title: 元のタイトル
        max_length: 最大文字数
    
    Returns:
        サニタイズされたファイル名
    """
    # 使えない文字を除去
    invalid_chars = r'[/\\:*?"<>|]'
    sanitized = re.sub(invalid_chars, '', title)
    
    # 前後の空白を除去
    sanitized = sanitized.strip()
    
    # 空になった場合
    if not sanitized:
        return "untitled"
    
    # 長すぎる場合は切り詰め
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()
    
    return sanitized


def get_conversation_dates(conv: dict) -> tuple:
    """
    スレッドの作成日時と更新日時を取得
    
    Args:
        conv: 会話データ
    
    Returns:
        (create_time, update_time) のタプル
    """
    create_time = conv.get('create_time')
    update_time = conv.get('update_time')
    
    return create_time, update_time


def split_conversations(json_path: str, output_base: str = "raw"):
    """
    conversations.jsonを分割
    
    Args:
        json_path: 入力JSONファイルパス
        output_base: 出力先ベースディレクトリ（相対パス）
    """
    print("="*80)
    print("conversations.json 分割ツール")
    print("="*80)
    
    # 入力ファイル読み込み
    input_path = Path(json_path)
    if not input_path.exists():
        print(f"エラー: ファイルが見つかりません: {json_path}")
        sys.exit(1)
    
    print(f"\n入力ファイル: {input_path}")
    print("読み込み中...", end="", flush=True)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f" 完了！ ({len(data)}スレッド)\n")
    
    # 出力先ディレクトリ準備（入力ファイルと同じディレクトリ）
    base_dir = input_path.parent / output_base
    base_dir.mkdir(exist_ok=True)
    
    print(f"出力先: {base_dir}/")
    print(f"処理中...\n")
    
    # インデックス用データ
    index_data = []
    
    # 統計
    success_count = 0
    error_count = 0
    
    for i, conv in enumerate(data, 1):
        try:
            # 日付情報取得
            create_time, update_time = get_conversation_dates(conv)
            
            if create_time is None:
                print(f"  警告: スレッド#{i} - create_timeがありません（スキップ）")
                error_count += 1
                continue
            
            # 日付変換
            create_dt = datetime.fromtimestamp(create_time)
            year = create_dt.strftime("%Y")
            month = create_dt.strftime("%m")
            day = create_dt.strftime("%d")
            
            # タイトル取得とサニタイズ
            title = conv.get('title', 'untitled')
            safe_title = sanitize_filename(title)
            
            # ファイル名: YYYY-MM-DD-title.json
            filename = f"{year}-{month}-{day}-{safe_title}.json"
            
            # ディレクトリ作成: raw/YYYY/MM/
            year_dir = base_dir / year
            month_dir = year_dir / month
            month_dir.mkdir(parents=True, exist_ok=True)
            
            # 出力パス
            output_path = month_dir / filename
            
            # 同名ファイルがある場合は番号を付ける
            counter = 1
            original_output_path = output_path
            while output_path.exists():
                stem = original_output_path.stem
                output_path = original_output_path.parent / f"{stem}_{counter}.json"
                counter += 1
            
            # JSON出力
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(conv, f, ensure_ascii=False, indent=2)
            
            # インデックスデータ追加
            relative_path = output_path.relative_to(base_dir)
            
            # メッセージ数カウント
            mapping = conv.get('mapping', {})
            message_count = sum(1 for node in mapping.values() if node.get('message'))
            
            index_entry = {
                "path": str(relative_path),
                "id": conv.get('id', 'unknown'),
                "title": title,
                "create_time": create_time,
                "update_time": update_time,
                "message_count": message_count,
                "model": conv.get('default_model_slug')
            }
            index_data.append(index_entry)
            
            success_count += 1
            
            # 進捗表示（100件ごと）
            if i % 100 == 0:
                print(f"  処理済み: {i}/{len(data)}")
        
        except Exception as e:
            print(f"  エラー: スレッド#{i} - {e}")
            error_count += 1
            continue
    
    # index.json 出力
    print(f"\nindex.json 生成中...", end="", flush=True)
    index_path = base_dir / "index.json"
    
    # create_timeでソート（古い順）
    index_data.sort(key=lambda x: x['create_time'] if x['create_time'] else 0)
    
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(" 完了！")
    
    # 結果表示
    print("\n" + "="*80)
    print("分割完了")
    print("="*80)
    print(f"成功: {success_count}スレッド")
    if error_count > 0:
        print(f"エラー: {error_count}スレッド")
    print(f"\n出力先: {base_dir}/")
    print(f"インデックス: {index_path}")
    print("="*80)


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使い方: python3 split_conversations.py <conversations.json>")
        print("\n例:")
        print("  python3 split_conversations.py conversations.json")
        print("  python3 split_conversations.py conversations2026-02-06.json")
        print("  python3 split_conversations.py ../path/to/conversations.json")
        sys.exit(1)
    
    json_path = sys.argv[1]
    split_conversations(json_path)


if __name__ == "__main__":
    main()