#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON徹底調査ツール - conversations.jsonの詳細分析
"""

import json
from pathlib import Path
from collections import defaultdict, Counter

def deep_analyze(json_path: str):
    """全スレッドを徹底分析"""
    print("="*80)
    print("JSON徹底調査ツール - 全スレッド分析")
    print("="*80)
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_threads = len(data)
    print(f"\n総スレッド数: {total_threads}\n")
    
    # === 1. default_model_slug分布 ===
    print("="*80)
    print("【1】 default_model_slug の分布")
    print("="*80)
    
    model_counter = Counter()
    model_none_count = 0
    
    for conv in data:
        model = conv.get('default_model_slug')
        if model is None:
            model_none_count += 1
        else:
            model_counter[model] += 1
    
    print(f"None: {model_none_count}回 ({model_none_count/total_threads*100:.2f}%)")
    for model, count in model_counter.most_common():
        print(f"{model}: {count}回 ({count/total_threads*100:.2f}%)")
    
    # === 2. gizmo関連の分析 ===
    print("\n" + "="*80)
    print("【2】 gizmo関連フィールドの分析")
    print("="*80)
    
    gizmo_patterns = Counter()
    
    for conv in data:
        gizmo_id = conv.get('gizmo_id')
        gizmo_type = conv.get('gizmo_type')
        template_id = conv.get('conversation_template_id')
        
        if gizmo_id is None:
            pattern = "通常スレッド（gizmo無し）"
        else:
            pattern = f"カスタムGPT (type={gizmo_type})"
        
        gizmo_patterns[pattern] += 1
    
    for pattern, count in gizmo_patterns.most_common():
        print(f"{pattern}: {count}回 ({count/total_threads*100:.2f}%)")
    
    # === 3. 全メッセージの詳細分析 ===
    print("\n" + "="*80)
    print("【3】 全メッセージの詳細分析（全スレッド走査）")
    print("="*80)
    
    # 統計用変数
    total_messages = 0
    total_nodes = 0
    
    content_type_counter = Counter()
    role_counter = Counter()
    
    # create_timeとroleの関係
    create_time_none_by_role = defaultdict(int)
    create_time_exist_by_role = defaultdict(int)
    
    # partsとtextの使い分け
    has_parts_count = 0
    has_text_count = 0
    has_both_count = 0
    has_neither_count = 0
    
    # metadataの中身
    metadata_keys_counter = Counter()
    
    print("分析中...", end="", flush=True)
    
    for i, conv in enumerate(data):
        if i % 100 == 0:
            print(".", end="", flush=True)
        
        mapping = conv.get('mapping', {})
        total_nodes += len(mapping)
        
        for node_id, node in mapping.items():
            if node.get('message'):
                message = node['message']
                total_messages += 1
                
                # role統計
                author = message.get('author', {})
                role = author.get('role', 'unknown')
                role_counter[role] += 1
                
                # content_type統計
                content = message.get('content', {})
                content_type = content.get('content_type', 'unknown')
                content_type_counter[content_type] += 1
                
                # create_timeとroleの関係
                create_time = message.get('create_time')
                if create_time is None:
                    create_time_none_by_role[role] += 1
                else:
                    create_time_exist_by_role[role] += 1
                
                # partsとtextの使い分け
                has_parts = 'parts' in content and content['parts'] is not None
                has_text = 'text' in content and content['text'] is not None
                
                if has_parts and has_text:
                    has_both_count += 1
                elif has_parts:
                    has_parts_count += 1
                elif has_text:
                    has_text_count += 1
                else:
                    has_neither_count += 1
                
                # metadataの中身
                metadata = message.get('metadata', {})
                for key in metadata.keys():
                    metadata_keys_counter[key] += 1
    
    print(" 完了！\n")
    
    # 結果表示
    print(f"総ノード数: {total_nodes:,}")
    print(f"総メッセージ数: {total_messages:,}")
    print(f"メッセージ率: {total_messages/total_nodes*100:.2f}%\n")
    
    print("-" * 80)
    print("【3-1】 roleの分布")
    print("-" * 80)
    for role, count in role_counter.most_common():
        print(f"{role}: {count:,}回 ({count/total_messages*100:.2f}%)")
    
    print("\n" + "-" * 80)
    print("【3-2】 content_typeの分布")
    print("-" * 80)
    for ctype, count in content_type_counter.most_common():
        print(f"{ctype}: {count:,}回 ({count/total_messages*100:.2f}%)")
    
    print("\n" + "-" * 80)
    print("【3-3】 create_timeとroleの関係")
    print("-" * 80)
    print(f"{'role':<20} {'create_time有り':<20} {'create_time無し':<20} {'None率':<10}")
    print("-" * 80)
    
    all_roles = set(create_time_exist_by_role.keys()) | set(create_time_none_by_role.keys())
    for role in sorted(all_roles):
        exist = create_time_exist_by_role[role]
        none = create_time_none_by_role[role]
        total_role = exist + none
        none_rate = none / total_role * 100 if total_role > 0 else 0
        print(f"{role:<20} {exist:<20,} {none:<20,} {none_rate:>6.2f}%")
    
    print("\n" + "-" * 80)
    print("【3-4】 partsとtextの使い分け")
    print("-" * 80)
    print(f"partsのみ: {has_parts_count:,}回 ({has_parts_count/total_messages*100:.2f}%)")
    print(f"textのみ: {has_text_count:,}回 ({has_text_count/total_messages*100:.2f}%)")
    print(f"両方あり: {has_both_count:,}回 ({has_both_count/total_messages*100:.2f}%)")
    print(f"両方なし: {has_neither_count:,}回 ({has_neither_count/total_messages*100:.2f}%)")
    
    print("\n" + "-" * 80)
    print("【3-5】 metadataの中身（キー出現回数）")
    print("-" * 80)
    if metadata_keys_counter:
        for key, count in metadata_keys_counter.most_common(20):  # 上位20個
            print(f"{key}: {count:,}回 ({count/total_messages*100:.2f}%)")
    else:
        print("metadataにキーが見つかりませんでした")
    
    # === 4. スレッドレベルの統計 ===
    print("\n" + "="*80)
    print("【4】 スレッドレベルの統計")
    print("="*80)
    
    # メッセージ数の分布
    message_counts = []
    for conv in data:
        mapping = conv.get('mapping', {})
        msg_count = sum(1 for node in mapping.values() if node.get('message'))
        message_counts.append(msg_count)
    
    message_counts.sort()
    
    print(f"最小メッセージ数: {message_counts[0]}")
    print(f"最大メッセージ数: {message_counts[-1]}")
    print(f"平均メッセージ数: {sum(message_counts)/len(message_counts):.1f}")
    print(f"中央値: {message_counts[len(message_counts)//2]}")
    
    # 分布
    print("\nメッセージ数の分布:")
    ranges = [(0, 10), (11, 50), (51, 100), (101, 200), (201, 500), (501, 1000), (1001, 99999)]
    for start, end in ranges:
        count = sum(1 for mc in message_counts if start <= mc <= end)
        if count > 0:
            print(f"  {start}~{end}メッセージ: {count}スレッド ({count/total_threads*100:.2f}%)")
    
    # === 5. voice, conversation_originの詳細 ===
    print("\n" + "="*80)
    print("【5】 オプショナルフィールドの詳細")
    print("="*80)
    
    voice_counter = Counter()
    origin_counter = Counter()
    
    for conv in data:
        voice = conv.get('voice')
        if voice is not None:
            voice_counter[voice] += 1
        
        origin = conv.get('conversation_origin')
        if origin is not None:
            origin_counter[origin] += 1
    
    print(f"voice指定あり: {sum(voice_counter.values())}スレッド")
    for voice, count in voice_counter.most_common():
        print(f"  {voice}: {count}回")
    
    print(f"\nconversation_origin指定あり: {sum(origin_counter.values())}スレッド")
    for origin, count in origin_counter.most_common():
        print(f"  {origin}: {count}回")
    
    print("\n" + "="*80)
    print("分析完了")
    print("="*80)


def main():
    """メイン関数"""
    script_dir = Path(__file__).parent
    json_file = script_dir / "conversations.json"
    
    if not json_file.exists():
        print(f"ファイルが見つかりません: {json_file}")
        return
    
    deep_analyze(json_file)


if __name__ == "__main__":
    main()