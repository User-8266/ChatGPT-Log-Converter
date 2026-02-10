#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown一括変換ツール
ディレクトリ内の全JSONファイルを再帰的にMarkdownに変換
"""

import sys
from pathlib import Path
from to_markdown import generate_markdown


def batch_convert(input_dir: str, output_dir: str):
    """
    ディレクトリ内の全JSONファイルを一括変換
    
    Args:
        input_dir: 入力ディレクトリ
        output_dir: 出力ディレクトリ
    """
    print("="*80)
    print("Markdown一括変換ツール")
    print("="*80)
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        print(f"エラー: 入力ディレクトリが見つかりません: {input_dir}")
        sys.exit(1)
    
    if not input_path.is_dir():
        print(f"エラー: 入力はディレクトリではありません: {input_dir}")
        sys.exit(1)
    
    print(f"\n入力: {input_path}")
    print(f"出力: {output_path}")
    print(f"\nJSONファイル検索中...", end="", flush=True)
    
    # JSONファイルを再帰的に検索（index.json は除外）
    json_files = []
    for json_file in input_path.rglob("*.json"):
        if json_file.name != "index.json":
            json_files.append(json_file)
    
    print(f" 完了！ ({len(json_files)}ファイル)\n")
    
    if len(json_files) == 0:
        print("変換対象のJSONファイルが見つかりませんでした")
        return
    
    # 統計
    success_count = 0
    error_count = 0
    error_files = []
    
    # 変換処理
    for i, json_file in enumerate(json_files, 1):
        try:
            # 相対パスを計算
            relative_path = json_file.relative_to(input_path)
            
            # 出力先パスを生成（ツリー構造維持）
            output_file = output_path / relative_path.with_suffix('.md')
            
            # 出力先ディレクトリ作成
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 変換実行
            generate_markdown(str(json_file), str(output_file))
            
            success_count += 1
            
            # 進捗表示（10件ごと）
            if i % 10 == 0 or i == len(json_files):
                print(f"  進捗: {i}/{len(json_files)} ({success_count}成功, {error_count}エラー)")
        
        except Exception as e:
            error_count += 1
            error_files.append({
                'file': str(json_file),
                'error': str(e)
            })
            # エラーが出ても続行
            continue
    
    # 結果表示
    print("\n" + "="*80)
    print("変換完了")
    print("="*80)
    print(f"成功: {success_count}ファイル")
    if error_count > 0:
        print(f"エラー: {error_count}ファイル")
        print(f"\nエラーファイル一覧:")
        for err in error_files[:10]:  # 最初の10件のみ表示
            print(f"  {err['file']}")
            print(f"    -> {err['error']}")
        if len(error_files) > 10:
            print(f"  ... 他 {len(error_files) - 10}件")
    print(f"\n出力先: {output_path}/")
    print("="*80)


def main():
    """メイン関数"""
    if len(sys.argv) < 3:
        print("使い方: python3 batch_convert.py <入力ディレクトリ> <出力ディレクトリ>")
        print("\n例:")
        print("  python3 batch_convert.py raw/ markdown/")
        print("  python3 batch_convert.py raw/ /path/to/output/")
        print("\n説明:")
        print("  入力ディレクトリ内の全JSONファイル（index.json除く）を再帰的に検索し、")
        print("  ツリー構造を維持したまま出力ディレクトリにMarkdownファイルを生成します。")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    batch_convert(input_dir, output_dir)


if __name__ == "__main__":
    main()