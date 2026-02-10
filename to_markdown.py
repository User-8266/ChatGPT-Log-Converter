#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown変換ツール
分割済みJSONをMarkdown形式に変換
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


def format_timestamp(unix_time: Optional[float]) -> str:
    """
    Unixタイムスタンプを YYYY-MM-DDTHH:MM 形式に変換
    
    Args:
        unix_time: Unixタイムスタンプ（秒）
    
    Returns:
        フォーマット済み文字列、Noneの場合は空文字列
    """
    if unix_time is None:
        return ""
    
    dt = datetime.fromtimestamp(unix_time)
    return dt.strftime("%Y-%m-%dT%H:%M")


def adjust_headings(text: str) -> str:
    """
    メッセージ内の見出しレベルを1つ下げる（# を1つ追加）
    
    Args:
        text: 元のテキスト
    
    Returns:
        見出しレベルを調整したテキスト
    """
    if not text:
        return text
    
    lines = text.split('\n')
    result = []
    
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('#'):
            # # の数を数える
            heading_level = 0
            for char in stripped:
                if char == '#':
                    heading_level += 1
                else:
                    break
            
            # # を1つ追加
            rest_of_line = stripped[heading_level:]
            adjusted_line = '#' * (heading_level + 1) + rest_of_line
            
            # 元の行の先頭空白を保持
            indent = line[:len(line) - len(stripped)]
            result.append(indent + adjusted_line)
        else:
            result.append(line)
    
    return '\n'.join(result)


def extract_message_content(message: Dict) -> Optional[str]:
    """
    messageからテキストコンテンツを抽出
    
    Args:
        message: メッセージオブジェクト
    
    Returns:
        テキストコンテンツ（空の場合はNone）
    """
    content = message.get('content', {})
    
    # partsを優先
    parts = content.get('parts')
    if parts is not None:
        if not isinstance(parts, list):
            return None
        if len(parts) == 0:
            # 空配列 = スキップ対象
            return None
        # partsの最初の要素を取得
        first_part = parts[0]
        if first_part and isinstance(first_part, str) and first_part.strip():
            return first_part.strip()
        # 空文字列
        return ""
    
    # textをフォールバック
    text = content.get('text')
    if text and isinstance(text, str) and text.strip():
        return text.strip()
    
    return ""


def build_turns(mapping: Dict) -> List[Dict]:
    """
    mappingからTurn構造を構築
    
    Args:
        mapping: 会話のmappingデータ
    
    Returns:
        Turn構造のリスト
    """
    # ノードをツリー順に並べる
    # まずルートを見つける
    root_id = None
    for node_id, node in mapping.items():
        parent = node.get('parent')
        if parent is None:
            root_id = node_id
            break
    
    if root_id is None:
        return []
    
    # ツリーを辿ってメッセージを収集
    messages = []
    
    def traverse(node_id: str):
        node = mapping.get(node_id)
        if not node:
            return
        
        message = node.get('message')
        if message:
            role = message.get('author', {}).get('role')
            # user と assistant のみ
            if role in ['user', 'assistant']:
                # 空のpartsチェック（スキップ対象かどうか）
                content_check = extract_message_content(message)
                if content_check is not None:  # None = スキップ対象
                    messages.append({
                        'node_id': node_id,
                        'role': role,
                        'message': message,
                        'children': node.get('children', [])
                    })
        
        # 子ノードを辿る（複数ある場合は分岐）
        children = node.get('children', [])
        for child_id in children:
            traverse(child_id)
    
    traverse(root_id)
    
    # Turnに整理（0始まり）
    turns = []
    i = 0
    
    while i < len(messages):
        msg = messages[i]
        
        if msg['role'] == 'user':
            turn = {
                'turn_number': len(turns),  # 0始まり
                'user': msg,
                'assistants': []
            }
            
            # 次のメッセージがassistantか確認
            j = i + 1
            while j < len(messages) and messages[j]['role'] == 'assistant':
                turn['assistants'].append(messages[j])
                j += 1
            
            turns.append(turn)
            i = j
        else:
            # assistantが先に来る場合（稀だが）
            i += 1
    
    return turns


def generate_markdown(json_path: str, output_path: Optional[str] = None) -> str:
    """
    JSONからMarkdownを生成
    
    Args:
        json_path: 入力JSONファイルパス
        output_path: 出力先パス（Noneの場合は自動生成）
    
    Returns:
        出力ファイルパス
    """
    # JSON読み込み
    input_file = Path(json_path)
    if not input_file.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {json_path}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 基本情報取得
    title = data.get('title', 'Untitled')
    create_time = data.get('create_time')
    update_time = data.get('update_time')
    
    # Turn構造構築
    mapping = data.get('mapping', {})
    turns = build_turns(mapping)
    
    if not turns:
        print(f"警告: {input_file.name} - メッセージが見つかりません")
        return ""
    
    # 最初と最後のメッセージ日時を取得
    # first_message_time は data['create_time'] を使用
    first_message_time = data.get('create_time')
    
    last_message_time = None
    
    # 最後のメッセージ
    for turn in reversed(turns):
        if turn['assistants']:
            last_message_time = turn['assistants'][-1]['message'].get('create_time')
            break
        else:
            last_message_time = turn['user']['message'].get('create_time')
            break
    
    # 会話期間（日数）計算
    duration_days = 0
    if first_message_time and last_message_time:
        duration_seconds = last_message_time - first_message_time
        duration_days = int(duration_seconds / 86400)  # 秒 -> 日
    
    # YAMLフロントマター
    # turn-count は Turn 00 を除く
    actual_turn_count = len([t for t in turns if t['turn_number'] > 0])
    
    yaml_front = f"""---
title: {title}
date: {format_timestamp(create_time)}
date-update: {format_timestamp(update_time)}
first-message-date: {format_timestamp(first_message_time)}
last-message-date: {format_timestamp(last_message_time)}
duration-days: {duration_days}
turn-count: {actual_turn_count}
---
"""
    
    # ヘッダー部
    header = f"""
# {title}

**会話期間**: {format_timestamp(first_message_time)} 〜 {format_timestamp(last_message_time)} ({duration_days}日間)
**ターン数**: {actual_turn_count}
"""
    
    # 本文生成
    body_parts = []
    
    for turn in turns:
        # Turn 00 はスキップ
        if turn['turn_number'] == 0:
            continue
        
        turn_text = f"\n# Turn {turn['turn_number']:02d}\n"
        
        # User部分
        user_msg = turn['user']['message']
        user_content = extract_message_content(user_msg)
        if user_content is None:
            user_content = ""
        user_content = adjust_headings(user_content)
        user_timestamp = format_timestamp(user_msg.get('create_time'))
        
        turn_text += f"\n## User\n\n{user_content}\n\n---\n\n**送信日時:** {user_timestamp}\n\n---\n"
        
        # Assistant部分（複数ある場合は分岐）
        if turn['assistants']:
            for assistant_msg_data in turn['assistants']:
                assistant_msg = assistant_msg_data['message']
                assistant_content = extract_message_content(assistant_msg)
                if assistant_content is None:
                    assistant_content = ""
                assistant_content = adjust_headings(assistant_content)
                assistant_timestamp = format_timestamp(assistant_msg.get('create_time'))
                
                # metadata から model_slug 取得
                metadata = assistant_msg.get('metadata', {})
                model_slug = metadata.get('model_slug', '')
                
                turn_text += f"\n## ChatGPT\n\n{assistant_content}\n\n---\n"
                if assistant_content:  # 本文がある場合のみ
                    turn_text += f"\n**Model:** {model_slug}\n**送信日時:** {assistant_timestamp}\n"
                turn_text += "\n---\n"
        else:
            # Assistant発言なし
            turn_text += f"\n## ChatGPT\n\n---\n\n---\n"
        
        body_parts.append(turn_text)
    
    # 全体を結合
    markdown = yaml_front + header + "\n".join(body_parts)
    
    # 出力先決定
    if output_path is None:
        # 入力ファイルと同じ名前で .md に変換
        output_file = input_file.with_suffix('.md')
    else:
        output_file = Path(output_path)
    
    # 出力
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    return str(output_file)


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使い方: python3 to_markdown.py <input.json> [output.md]")
        print("\n例:")
        print("  python3 to_markdown.py raw/2024/01/2024-01-15-会話.json")
        print("  python3 to_markdown.py raw/2024/01/2024-01-15-会話.json output.md")
        sys.exit(1)
    
    json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result = generate_markdown(json_path, output_path)
        print(f"変換完了: {result}")
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()