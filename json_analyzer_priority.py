#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON優先度調査ツール - 高・中優先度項目の詳細分析
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def analyze_priority_items(json_path: str):
    """優先度の高い項目を詳細分析"""
    print("="*80)
    print("JSON優先度調査ツール - 高・中優先度項目の詳細分析")
    print("="*80)
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_threads = len(data)
    print(f"\n総スレッド数: {total_threads}\n")
    
    # ============================================================
    # 高優先度1: metadata.timestamp_の形式確認
    # ============================================================
    print("="*80)
    print("【高優先度1】 metadata.timestamp_ の形式確認")
    print("="*80)
    
    timestamp_types = Counter()
    timestamp_samples = []
    create_time_none_with_timestamp = 0
    create_time_none_without_timestamp = 0
    timestamp_values = []
    
    for conv in data:
        mapping = conv.get('mapping', {})
        for node_id, node in mapping.items():
            if node.get('message'):
                message = node['message']
                create_time = message.get('create_time')
                metadata = message.get('metadata', {})
                timestamp_ = metadata.get('timestamp_')
                
                if timestamp_ is not None:
                    timestamp_types[type(timestamp_).__name__] += 1
                    if len(timestamp_samples) < 5:
                        timestamp_samples.append({
                            'timestamp_': timestamp_,
                            'create_time': create_time,
                            'role': message.get('author', {}).get('role')
                        })
                    timestamp_values.append(timestamp_)
                
                # create_timeがNoneの時のtimestamp_の有無
                if create_time is None:
                    if timestamp_ is not None:
                        create_time_none_with_timestamp += 1
                    else:
                        create_time_none_without_timestamp += 1
    
    print(f"\ntimestamp_の型分布:")
    for ttype, count in timestamp_types.most_common():
        print(f"  {ttype}: {count:,}回")
    
    print(f"\nサンプル値:")
    for i, sample in enumerate(timestamp_samples, 1):
        print(f"  サンプル{i}:")
        print(f"    timestamp_: {sample['timestamp_']}")
        print(f"    create_time: {sample['create_time']}")
        print(f"    role: {sample['role']}")
        
        # 型がstrなら、Unixタイムスタンプに変換可能かチェック
        if isinstance(sample['timestamp_'], str):
            try:
                if sample['timestamp_'].startswith('absolute__'):
                    ts_str = sample['timestamp_'].replace('absolute__', '')
                    ts_float = float(ts_str)
                    dt = datetime.fromtimestamp(ts_float)
                    print(f"    -> 変換後: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                pass
    
    print(f"\ncreate_timeがNoneの場合:")
    print(f"  timestamp_あり: {create_time_none_with_timestamp}件")
    print(f"  timestamp_なし: {create_time_none_without_timestamp}件")
    if create_time_none_with_timestamp > 0:
        coverage = create_time_none_with_timestamp / (create_time_none_with_timestamp + create_time_none_without_timestamp) * 100
        print(f"  timestamp_でカバー可能: {coverage:.2f}%")
    
    # ============================================================
    # 高優先度2: content_type別の構造
    # ============================================================
    print("\n" + "="*80)
    print("【高優先度2】 content_type別の構造")
    print("="*80)
    
    content_type_structures = defaultdict(lambda: {
        'count': 0,
        'has_parts': 0,
        'has_text': 0,
        'has_both': 0,
        'has_neither': 0,
        'other_fields': Counter(),
        'samples': []
    })
    
    for conv in data:
        mapping = conv.get('mapping', {})
        for node_id, node in mapping.items():
            if node.get('message'):
                message = node['message']
                content = message.get('content', {})
                content_type = content.get('content_type', 'unknown')
                
                stats = content_type_structures[content_type]
                stats['count'] += 1
                
                has_parts = 'parts' in content and content['parts'] is not None
                has_text = 'text' in content and content['text'] is not None
                
                if has_parts and has_text:
                    stats['has_both'] += 1
                elif has_parts:
                    stats['has_parts'] += 1
                elif has_text:
                    stats['has_text'] += 1
                else:
                    stats['has_neither'] += 1
                
                # その他のフィールド
                for key in content.keys():
                    if key not in ['content_type', 'parts', 'text']:
                        stats['other_fields'][key] += 1
                
                # サンプル保存（各タイプ2個まで）
                if len(stats['samples']) < 2:
                    sample = {
                        'content_type': content_type,
                        'fields': list(content.keys()),
                        'role': message.get('author', {}).get('role')
                    }
                    if has_parts and content['parts']:
                        sample['parts_preview'] = str(content['parts'][0])[:100] if content['parts'][0] else 'None'
                    if has_text:
                        sample['text_preview'] = content['text'][:100]
                    stats['samples'].append(sample)
    
    print("\ncontent_type別の構造分析:")
    for ctype, stats in sorted(content_type_structures.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"\n【{ctype}】 ({stats['count']:,}件)")
        print(f"  partsのみ: {stats['has_parts']}件 ({stats['has_parts']/stats['count']*100:.1f}%)")
        print(f"  textのみ: {stats['has_text']}件 ({stats['has_text']/stats['count']*100:.1f}%)")
        print(f"  両方: {stats['has_both']}件")
        print(f"  どちらもなし: {stats['has_neither']}件")
        
        if stats['other_fields']:
            print(f"  その他のフィールド:")
            for field, count in stats['other_fields'].most_common(5):
                print(f"    - {field}: {count}件")
        
        if stats['samples']:
            print(f"  サンプル:")
            for i, sample in enumerate(stats['samples'], 1):
                print(f"    サンプル{i} (role={sample['role']}):")
                print(f"      フィールド: {sample['fields']}")
                if 'parts_preview' in sample:
                    print(f"      parts: {sample['parts_preview']}")
                if 'text_preview' in sample:
                    print(f"      text: {sample['text_preview']}")
    
    # ============================================================
    # 高優先度3: toolメッセージの詳細
    # ============================================================
    print("\n" + "="*80)
    print("【高優先度3】 toolメッセージの詳細")
    print("="*80)
    
    tool_message_count = 0
    tool_content_types = Counter()
    tool_samples = []
    
    # Turn構造の確認（user→tool→assistant）
    turn_patterns = Counter()
    
    for conv in data:
        mapping = conv.get('mapping', {})
        
        # メッセージをツリー順に並べる
        messages = []
        for node_id, node in mapping.items():
            if node.get('message'):
                message = node['message']
                messages.append({
                    'role': message.get('author', {}).get('role'),
                    'content_type': message.get('content', {}).get('content_type'),
                    'content': message.get('content', {}),
                    'node_id': node_id,
                    'parent': node.get('parent')
                })
        
        # toolメッセージの統計
        for msg in messages:
            if msg['role'] == 'tool':
                tool_message_count += 1
                tool_content_types[msg['content_type']] += 1
                
                if len(tool_samples) < 5:
                    tool_samples.append({
                        'content_type': msg['content_type'],
                        'fields': list(msg['content'].keys()),
                        'content_preview': str(msg['content'])[:200]
                    })
        
        # Turn構造パターンの確認（簡易版）
        for i in range(len(messages) - 2):
            pattern = f"{messages[i]['role']}→{messages[i+1]['role']}→{messages[i+2]['role']}"
            turn_patterns[pattern] += 1
    
    print(f"\n総toolメッセージ数: {tool_message_count:,}")
    print(f"\ntoolメッセージのcontent_type分布:")
    for ctype, count in tool_content_types.most_common():
        print(f"  {ctype}: {count:,}件 ({count/tool_message_count*100:.2f}%)")
    
    print(f"\ntoolメッセージのサンプル:")
    for i, sample in enumerate(tool_samples, 1):
        print(f"  サンプル{i}:")
        print(f"    content_type: {sample['content_type']}")
        print(f"    フィールド: {sample['fields']}")
        print(f"    内容: {sample['content_preview']}")
    
    print(f"\n主なTurnパターン（上位10個）:")
    for pattern, count in turn_patterns.most_common(10):
        print(f"  {pattern}: {count:,}回")
    
    # ============================================================
    # 中優先度4: citations, finish_detailsの構造
    # ============================================================
    print("\n" + "="*80)
    print("【中優先度4】 citations, finish_detailsの構造")
    print("="*80)
    
    citations_samples = []
    finish_details_samples = []
    
    for conv in data:
        mapping = conv.get('mapping', {})
        for node_id, node in mapping.items():
            if node.get('message'):
                message = node['message']
                metadata = message.get('metadata', {})
                
                # citations
                citations = metadata.get('citations')
                if citations and len(citations_samples) < 3:
                    citations_samples.append({
                        'type': type(citations).__name__,
                        'content': str(citations)[:300]
                    })
                
                # finish_details
                finish_details = metadata.get('finish_details')
                if finish_details and len(finish_details_samples) < 5:
                    finish_details_samples.append({
                        'type': type(finish_details).__name__,
                        'content': str(finish_details)[:200]
                    })
    
    print("\ncitationsのサンプル:")
    for i, sample in enumerate(citations_samples, 1):
        print(f"  サンプル{i} (型: {sample['type']}):")
        print(f"    {sample['content']}")
    
    print("\nfinish_detailsのサンプル:")
    for i, sample in enumerate(finish_details_samples, 1):
        print(f"  サンプル{i} (型: {sample['type']}):")
        print(f"    {sample['content']}")
    
    # ============================================================
    # 中優先度5: Turn構造の確認
    # ============================================================
    print("\n" + "="*80)
    print("【中優先度5】 Turn構造の確認")
    print("="*80)
    
    # user→assistantペアの完全性チェック
    complete_turns = 0
    incomplete_turns = 0
    turns_with_tool = 0
    
    for conv in data:
        mapping = conv.get('mapping', {})
        
        # メッセージをリストに
        messages = []
        for node_id, node in mapping.items():
            if node.get('message'):
                message = node['message']
                role = message.get('author', {}).get('role')
                if role in ['user', 'assistant']:
                    messages.append(role)
        
        # user→assistantのペアをカウント
        i = 0
        while i < len(messages):
            if messages[i] == 'user':
                if i + 1 < len(messages) and messages[i + 1] == 'assistant':
                    complete_turns += 1
                    i += 2
                else:
                    incomplete_turns += 1
                    i += 1
            else:
                i += 1
    
    # toolが含まれるTurnのカウント
    for conv in data:
        mapping = conv.get('mapping', {})
        messages = []
        for node_id, node in mapping.items():
            if node.get('message'):
                message = node['message']
                messages.append(message.get('author', {}).get('role'))
        
        # user→tool→assistantパターンを探す
        for i in range(len(messages) - 2):
            if messages[i] == 'user' and messages[i+1] == 'tool' and messages[i+2] == 'assistant':
                turns_with_tool += 1
    
    print(f"\nTurn構造の統計:")
    print(f"  完全なuser→assistantペア: {complete_turns:,}個")
    print(f"  不完全なTurn: {incomplete_turns:,}個")
    print(f"  toolを含むTurn (user→tool→assistant): {turns_with_tool:,}個")
    
    # ============================================================
    # 中優先度6: ブランチングの実態
    # ============================================================
    print("\n" + "="*80)
    print("【中優先度6】 ブランチング（分岐）の実態")
    print("="*80)
    
    total_nodes_with_children = 0
    nodes_with_multiple_children = 0
    max_children = 0
    branching_examples = []
    
    for conv in data:
        mapping = conv.get('mapping', {})
        for node_id, node in mapping.items():
            children = node.get('children', [])
            if children:
                total_nodes_with_children += 1
                if len(children) > 1:
                    nodes_with_multiple_children += 1
                    if len(children) > max_children:
                        max_children = len(children)
                    
                    if len(branching_examples) < 5:
                        branching_examples.append({
                            'conversation': conv.get('title', 'Untitled'),
                            'node_id': node_id[:8],
                            'children_count': len(children)
                        })
    
    print(f"\n子ノードを持つノード数: {total_nodes_with_children:,}")
    print(f"複数の子を持つノード数: {nodes_with_multiple_children:,}")
    print(f"最大子ノード数: {max_children}")
    
    if nodes_with_multiple_children > 0:
        print(f"\n分岐率: {nodes_with_multiple_children/total_nodes_with_children*100:.2f}%")
        print(f"\n分岐の例:")
        for i, example in enumerate(branching_examples, 1):
            print(f"  例{i}: {example['conversation']} (node={example['node_id']}, 子={example['children_count']})")
    else:
        print("\n分岐は見つかりませんでした（全て1本道）")
    
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
    
    analyze_priority_items(json_file)


if __name__ == "__main__":
    main()