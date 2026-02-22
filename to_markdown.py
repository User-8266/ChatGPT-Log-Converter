#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown変換ツール
分割済みJSONをMarkdown形式に変換

【設計思想】
- シンプルさ重視：複雑な処理を避け、理解しやすいコードを目指す
- 安全性重視：エラーが出ても処理を続行せず、明示的に失敗する
- データ保全：元データの情報をできるだけ保持する

【前提条件】
- Python 3.x 環境
- 入力：split_conversations.py で分割された単一スレッドのJSONファイル
- ChatGPTのエクスポート形式（conversations.json）に準拠

【処理の流れ】
1. JSONファイル読み込み
2. mapping からメッセージツリーを構築
3. user/assistant のみを抽出してTurn構造化
4. YAMLフロントマター生成
5. Markdown本文生成
6. ファイル出力

【Turn番号について】
- 内部的には0始まり（Turn 0, Turn 1, Turn 2...）
- Turn 0 はパーソナライズ読み込みなどのUI非表示メッセージ用
- Markdown出力時はTurn 0をスキップし、Turn 01から開始
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


def format_timestamp(unix_time: Optional[float]) -> str:
    """
    Unixタイムスタンプを YYYY-MM-DDTHH:MM 形式に変換
    
    【Unixタイムスタンプとは】
    1970年1月1日0時0分0秒（UTC）からの経過秒数
    例：1740795968.038276 → 2025-03-01T11:26
    
    【なぜ秒以下を切り捨てるか】
    - Markdownでの可読性向上
    - 秒単位の精度は通常不要
    
    Args:
        unix_time: Unixタイムスタンプ（秒）、Noneの場合もある
    
    Returns:
        フォーマット済み文字列、Noneの場合は空文字列
    """
    if unix_time is None:
        return ""
    
    # Unixタイムスタンプをdatetimeオブジェクトに変換
    dt = datetime.fromtimestamp(unix_time)
    # YYYY-MM-DDTHH:MM 形式の文字列に整形（秒以下は切り捨て）
    return dt.strftime("%Y-%m-%dT%H:%M")


def adjust_headings(text: str) -> str:
    """
    メッセージ内の見出しレベルを1つ下げる（# を1つ追加）
    
    【なぜこの処理が必要か】
    ChatGPTの応答内で使われる見出し（#, ##, ###）を
    Markdownファイル全体の構造に合わせるため。
    
    【処理の具体例】
    元のメッセージ：
      ## 大見出し
      ### 小見出し
    
    変換後：
      ### 大見出し  （# を1つ追加）
      #### 小見出し  （# を1つ追加）
    
    【Markdownファイル全体の構造】
    # スレッドタイトル        ← ファイル全体の見出し
    ## Turn 01                ← Turn見出し
    ### User/ChatGPT          ← 発言者見出し
    #### メッセージ内の見出し  ← ここで調整が必要
    
    Args:
        text: 元のテキスト
    
    Returns:
        見出しレベルを調整したテキスト
    """
    if not text:
        return text
    
    # テキストを行ごとに分割
    lines = text.split('\n')
    result = []
    
    for line in lines:
        # 行の先頭空白を除いた部分を取得
        stripped = line.lstrip()
        
        # # で始まる行かチェック（Markdown見出し）
        if stripped.startswith('#'):
            # # の連続数を数える
            heading_level = 0
            for char in stripped:
                if char == '#':
                    heading_level += 1
                else:
                    break  # # 以外の文字が出たら終了
            
            # # の後の文字列（見出しテキスト部分）を取得
            rest_of_line = stripped[heading_level:]
            
            # # を1つ追加して新しい見出しを作成
            adjusted_line = '#' * (heading_level + 1) + rest_of_line
            
            # 元の行の先頭空白（インデント）を保持
            indent = line[:len(line) - len(stripped)]
            result.append(indent + adjusted_line)
        else:
            # 見出しでない行はそのまま
            result.append(line)
    
    # 行を再結合して返す
    return '\n'.join(result)


def extract_message_content(message: Dict) -> Optional[str]:
    """
    messageからテキストコンテンツを抽出
    
    【この関数の役割】
    ChatGPTのメッセージデータから、実際に表示すべきテキストを取り出す。
    ただし、UI上で非表示のメッセージ（パーソナライズ設定など）は除外する。
    
    【返り値の意味】
    - 文字列：表示すべき内容がある
    - None：このメッセージはスキップすべき（UI非表示、空メッセージなど）
    
    【content_typeとは】
    ChatGPTのメッセージには種類（content_type）がある：
    - "text"：通常のテキストメッセージ
    - "code"：コードブロック
    - "multimodal_text"：画像付きメッセージ
    - "user_editable_context"：パーソナライズ設定（UI非表示）
    - "model_editable_context"：モデル用設定（UI非表示）
    など、全12種類が確認されている
    
    【ホワイトリスト方式を採用する理由】
    - 安全性：未知のタイプは自動的に除外される
    - 保守性：新しいタイプが追加された時に警告で気づける
    - 明示性：「何を許可するか」が明確
    
    Args:
        message: メッセージオブジェクト（JSONから取得）
    
    Returns:
        テキストコンテンツ（スキップすべき場合はNone）
    """
    # 【ステップ1】許可するcontent_typeを定義（ホワイトリスト方式）
    ALLOWED_CONTENT_TYPES = {
        'text',            # 通常のテキストメッセージ
        'code',            # コードブロック
        'multimodal_text', # 画像付きメッセージ
        'reasoning_recap', # 推論の要約（Claude等のAIモデル用）
        'thoughts',        # 思考プロセス（Claude等のAIモデル用）
    }
    
    # 静かにスキップする（INFO出力しない）content_type
    SILENT_SKIP_TYPES = {
        'user_editable_context',  # パーソナライズ設定（UI非表示）
        'app_pairing_content',    # アプリペアリング情報（UI非表示）
    }
    
    # 静かにスキップするcontent_type（INFOメッセージを出さない）
    SILENT_SKIP_TYPES = {
        'user_editable_context',  # パーソナライズ設定（UI非表示）
        'app_pairing_content',    # アプリペアリング情報（UI非表示）
    }
    
    # メッセージの content 部分を取得
    content = message.get('content', {})
    
    # 【ステップ2】content_typeチェック
    content_type = content.get('content_type')
    
    # 静かにスキップするタイプの場合、メッセージなしでスキップ
    if content_type and content_type in SILENT_SKIP_TYPES:
        return None  # 静かにスキップ
    
    # ALLOWED_CONTENT_TYPES以外は警告してスキップ
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        # 未知のタイプや除外すべきタイプは警告して除外
        # この警告により、新しいタイプが追加された時に気づける
        print(f"INFO: content_type '{content_type}' をスキップしました")
        return None  # スキップシグナル
    
    # 【ステップ3】parts からテキストを取得（優先）
    # ChatGPTのメッセージは通常 "parts" という配列に格納されている
    parts = content.get('parts')
    if parts is not None:  # parts が存在する場合
        # parts がリスト型でない場合はスキップ
        if not isinstance(parts, list):
            return None
        
        # parts が空配列の場合はスキップ
        # 例：パーソナライズ読み込み時の空メッセージ
        if len(parts) == 0:
            return None
        
        # parts の中から最初の文字列要素を探す
        # 画像付きメッセージの場合、parts[0]が画像オブジェクト、parts[1]がテキストになることがある
        for part in parts:
            # 文字列で、空白を除いて中身がある場合
            if isinstance(part, str) and part.strip():
                return part.strip()  # 前後の空白を除いて返す
        
        # すべての要素が文字列でない、または空文字列の場合はスキップ
        return None
    
    # 【ステップ4】text からテキストを取得（フォールバック）
    # parts がない場合、text フィールドを確認
    text = content.get('text')
    if text and isinstance(text, str) and text.strip():
        return text.strip()
    
    # 【ステップ5】どちらも取得できない場合
    # parts も text も存在しない、または空の場合は空文字列を返す
    # （この場合は「メッセージはあるが内容が空」と判断）
    return ""


def build_turns(mapping: Dict) -> List[Dict]:
    """
    mappingからTurn構造を構築
    
    【mappingとは】
    ChatGPTの会話データは「ツリー構造」で保存されている。
    mapping は「ノードID → ノード情報」の辞書。
    
    【ツリー構造の例】
    root (親なし)
      └─ system メッセージ
          └─ user メッセージ1
              ├─ assistant 応答A（分岐1）
              │   └─ user メッセージ2A
              └─ assistant 応答B（分岐2）
                  └─ user メッセージ2B
    
    【この関数がやること】
    1. ツリーを辿って、user/assistant メッセージのみを抽出
    2. user → assistant の組をTurnとして整理
    3. 分岐がある場合は同じTurn内に複数のassistantを格納
    
    【Turn番号について】
    - 0始まり（Turn 0, Turn 1, Turn 2...）
    - Turn 0 はUI非表示メッセージ用（後でスキップされる）
    
    Args:
        mapping: 会話のmappingデータ（ノードID → ノード情報の辞書）
    
    Returns:
        Turn構造のリスト
        各Turnは以下の形式：
        {
            'turn_number': 0,  # Turn番号
            'user': {...},     # userメッセージデータ
            'assistants': [...]  # assistantメッセージデータのリスト（分岐対応）
        }
    """
    # 【ステップ1】ルートノード（親を持たないノード）を見つける
    # ツリー構造の開始点を特定
    root_id = None
    for node_id, node in mapping.items():
        parent = node.get('parent')
        if parent is None:  # 親がない = ルートノード
            root_id = node_id
            break
    
    # ルートが見つからない場合は空リストを返す
    if root_id is None:
        return []
    
    # 【ステップ2】ツリーを辿ってメッセージを収集
    # user と assistant のメッセージのみを抽出する
    messages = []
    
    def traverse(node_id: str):
        """
        ツリーを再帰的に辿る内部関数
        
        【再帰処理とは】
        自分自身を呼び出すことで、ツリー構造を深さ優先で探索する。
        
        【処理の流れ】
        1. 現在のノードを取得
        2. メッセージがあればチェック
        3. 子ノードに対して同じ処理を繰り返す
        
        Args:
            node_id: 現在処理中のノードID
        """
        # 現在のノードを取得
        node = mapping.get(node_id)
        if not node:
            return  # ノードが存在しない場合は終了
        
        # ノード内のメッセージを取得
        message = node.get('message')
        if message:
            # メッセージの送信者（role）を取得
            role = message.get('author', {}).get('role')
            
            # user と assistant のみを対象にする
            # system や tool は無視（UI上で非表示のため）
            if role in ['user', 'assistant']:
                # メッセージの内容を抽出してチェック
                # None が返ってきた場合はスキップ対象（空メッセージなど）
                content_check = extract_message_content(message)
                
                if content_check is not None:
                    # 有効なメッセージとしてリストに追加
                    messages.append({
                        'node_id': node_id,
                        'role': role,
                        'message': message,
                        'children': node.get('children', [])
                    })
        
        # 【再帰呼び出し】子ノードを辿る
        # 子ノードが複数ある場合は分岐している
        children = node.get('children', [])
        for child_id in children:
            traverse(child_id)  # 再帰的に子ノードを処理
    
    # ルートノードから探索開始
    traverse(root_id)
    
    # 【ステップ3】収集したメッセージをTurnに整理
    # user → assistant の組み合わせを1Turnとする
    turns = []
    i = 0  # 現在処理中のメッセージのインデックス
    
    while i < len(messages):
        msg = messages[i]
        
        if msg['role'] == 'user':
            # userメッセージを見つけたら、新しいTurnを作成
            turn = {
                'turn_number': len(turns),  # Turn番号（0始まり）
                'user': msg,                # userメッセージデータ
                'assistants': []            # assistantメッセージのリスト（分岐対応）
            }
            
            # 【次のメッセージがassistantかチェック】
            # user の直後に assistant が複数ある場合は分岐している
            # 例：
            #   Turn 5: user 質問
            #   Turn 5: assistant 応答A（分岐1）
            #   Turn 5: assistant 応答B（分岐2）
            #   Turn 6: user 次の質問
            j = i + 1
            while j < len(messages) and messages[j]['role'] == 'assistant':
                # assistant メッセージをTurnに追加
                turn['assistants'].append(messages[j])
                j += 1
            
            # Turnをリストに追加
            turns.append(turn)
            
            # 次のuserメッセージへ進む
            i = j
        else:
            # assistant が先に来る場合（稀だが存在する）
            # この場合はスキップして次へ
            i += 1
    
    return turns


def generate_markdown(json_path: str, output_path: Optional[str] = None) -> str:
    """
    JSONからMarkdownを生成
    
    【この関数の全体的な流れ】
    1. JSONファイルを読み込む
    2. 基本情報（タイトル、日時）を取得
    3. Turn構造を構築
    4. YAMLフロントマターを生成
    5. ヘッダー部を生成
    6. 各Turnの本文を生成
    7. Markdownファイルとして出力
    
    Args:
        json_path: 入力JSONファイルパス（相対/絶対パス対応）
        output_path: 出力先パス（Noneの場合は入力ファイル名.mdに自動変換）
    
    Returns:
        出力ファイルパス（文字列）
    """
    # 【ステップ1】JSON読み込み
    input_file = Path(json_path)
    
    # ファイルの存在確認
    if not input_file.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {json_path}")
    
    # JSONファイルを開いて読み込む
    # encoding='utf-8' で日本語などのマルチバイト文字に対応
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)  # JSONをPythonの辞書型に変換
    
    # 【ステップ2】基本情報取得
    # スレッドのタイトルを取得（なければ "Untitled"）
    title = data.get('title', 'Untitled')
    # スレッド作成日時（Unixタイムスタンプ）
    create_time = data.get('create_time')
    # スレッド最終更新日時（Unixタイムスタンプ）
    update_time = data.get('update_time')
    
    # 【ステップ3】Turn構造構築
    # mapping（ツリー構造データ）を取得
    mapping = data.get('mapping', {})
    # build_turns() を呼び出してTurnリストを作成
    turns = build_turns(mapping)
    
    # Turnが1つも作成されなかった場合
    # （メッセージが全てスキップされた、または存在しない）
    if not turns:
        print(f"警告: {input_file.name} - メッセージが見つかりません")
        return ""  # 空文字列を返して処理終了
    
    # 【ステップ4】最初と最後のメッセージ日時を取得
    # 会話期間を計算するために必要
    
    # first_message_time は data['create_time'] を使用
    # 理由：最初のuserメッセージのcreate_timeがNullの場合があるため
    first_message_time = data.get('create_time')
    
    # last_message_time は実際の最後のメッセージから取得
    last_message_time = None
    
    # Turnリストを逆順（最後から）で辿る
    for turn in reversed(turns):
        # assistant応答がある場合、その最後の応答の日時を取得
        if turn['assistants']:
            last_message_time = turn['assistants'][-1]['message'].get('create_time')
            break  # 見つかったらループ終了
        else:
            # assistant応答がない場合、userメッセージの日時を使用
            last_message_time = turn['user']['message'].get('create_time')
            break
    
    # 【ステップ5】会話期間（日数）計算
    duration_days = 0  # デフォルトは0日
    if first_message_time and last_message_time:
        # 秒単位の差を計算
        duration_seconds = last_message_time - first_message_time
        # 秒を日に変換（86400秒 = 1日）
        duration_days = int(duration_seconds / 86400)
    
    # 【ステップ6】YAMLフロントマター生成
    # YAMLフロントマターとは：Markdownファイルの先頭に書くメタデータ
    # --- で囲まれた部分がYAML形式で記述される
    # Obsidianなどのツールで活用できる
    
    # turn-count は Turn 0 を除いた実質的なターン数
    # Turn 0 はUI非表示メッセージなので、カウントから除外
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
    
    # 【ステップ7】ヘッダー部生成
    # Markdownファイルの冒頭に表示される情報
    # スレッドタイトル、会話期間、ターン数を見やすく表示
    header = f"""
# {title}

**会話期間**: {format_timestamp(first_message_time)} 〜 {format_timestamp(last_message_time)} ({duration_days}日間)
**ターン数**: {actual_turn_count}
"""
    
    # 【ステップ8】本文生成
    # 各Turnをループして、Markdown形式のテキストを生成
    body_parts = []  # 各Turnのテキストを格納するリスト
    
    for turn in turns:
        # Turn 0 で内容が空の場合のみスキップ
        # （パーソナライズ読み込みなどのUI非表示メッセージ用）
        if turn['turn_number'] == 0:
            # userメッセージの内容をチェック
            user_msg = turn['user']['message']
            user_content = extract_message_content(user_msg)
            # 内容が空（None）の場合はスキップ
            if user_content is None:
                continue
        
        # Turn見出しを生成（例：# Turn 01）
        # 02d は「2桁のゼロパディング」を意味する（01, 02, 03...）
        # Turn 0 の場合は Turn 00 と表示される
        turn_text = f"\n# Turn {turn['turn_number']:02d}\n"
        
        # 【User部分の生成】
        user_msg = turn['user']['message']
        
        # メッセージ本文を抽出
        user_content = extract_message_content(user_msg)
        # None が返ってきた場合は空文字列に変換
        # （通常ここには来ないが、安全のため）
        if user_content is None:
            user_content = ""
        
        # 見出しレベルを調整（# を1つ追加）
        user_content = adjust_headings(user_content)
        
        # タイムスタンプを取得・整形
        user_timestamp = format_timestamp(user_msg.get('create_time'))
        
        # Userセクションのテキストを組み立て
        # フォーマット：
        # ## User
        # 
        # メッセージ本文
        # 
        # ---
        # 
        # **送信日時:** YYYY-MM-DDTHH:MM
        # 
        # ---
        turn_text += f"\n## User\n\n{user_content}\n\n---\n\n**送信日時:** {user_timestamp}\n\n---\n"
        
        # 【ChatGPT（Assistant）部分の生成】
        # turn['assistants'] は分岐対応のためリスト形式
        # 通常は1つだが、分岐がある場合は複数の応答が入る
        if turn['assistants']:
            # 各assistant応答をループ
            # 分岐がある場合、同じTurn内に複数の ## ChatGPT が並ぶ
            for assistant_msg_data in turn['assistants']:
                assistant_msg = assistant_msg_data['message']
                
                # メッセージ本文を抽出
                assistant_content = extract_message_content(assistant_msg)
                # None が返ってきた場合は空文字列に変換
                if assistant_content is None:
                    assistant_content = ""
                
                # 見出しレベルを調整（# を1つ追加）
                assistant_content = adjust_headings(assistant_content)
                
                # タイムスタンプを取得・整形
                assistant_timestamp = format_timestamp(assistant_msg.get('create_time'))
                
                # metadata から model_slug を取得
                # model_slug：使用されたモデル名（例：gpt-4o, gpt-4-5）
                metadata = assistant_msg.get('metadata', {})
                model_slug = metadata.get('model_slug', '')
                
                # ChatGPTセクションのテキストを組み立て
                # フォーマット：
                # ## ChatGPT
                # 
                # メッセージ本文
                # 
                # ---
                # 
                # **Model:** gpt-4o
                # **送信日時:** YYYY-MM-DDTHH:MM
                # 
                # ---
                turn_text += f"\n## ChatGPT\n\n{assistant_content}\n\n---\n"
                
                # 本文がある場合のみ、Model と 送信日時 を表示
                # 空応答の場合は --- が連続する（視覚的に「空」を表現）
                if assistant_content:
                    turn_text += f"\n**Model:** {model_slug}\n**送信日時:** {assistant_timestamp}\n"
                
                turn_text += "\n---\n"
        else:
            # Assistant発言なし
            # ネットワークエラーなどで応答が生成されなかった場合
            # フォーマット：
            # ## ChatGPT
            # 
            # ---
            # 
            # ---
            # （連続する --- で「空」を表現）
            turn_text += f"\n## ChatGPT\n\n---\n\n---\n"
        
        # このTurnのテキストをリストに追加
        body_parts.append(turn_text)
    
    # 【ステップ9】全体を結合
    # YAMLフロントマター + ヘッダー + 本文（各Turn）を結合
    markdown = yaml_front + header + "\n".join(body_parts)
    
    # 【ステップ10】出力先決定
    if output_path is None:
        # 出力先が指定されていない場合
        # 入力ファイルと同じ名前で拡張子を .md に変換
        # 例：input.json → input.md
        output_file = input_file.with_suffix('.md')
    else:
        # 出力先が指定されている場合、そのパスを使用
        output_file = Path(output_path)
    
    # 【ステップ11】ファイル出力
    # encoding='utf-8' で日本語などのマルチバイト文字に対応
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    # 出力ファイルのパスを文字列で返す
    return str(output_file)


def main():
    """
    メイン関数
    
    【この関数の役割】
    コマンドライン引数を処理して、generate_markdown() を呼び出す
    
    【使い方】
    python3 to_markdown.py <input.json> [output.md]
    
    例：
    python3 to_markdown.py raw/2024/01/2024-01-15-会話.json
    python3 to_markdown.py raw/2024/01/2024-01-15-会話.json output.md
    """
    # コマンドライン引数の数をチェック
    # sys.argv[0] はスクリプト名自体なので、最低でも2つ必要
    # sys.argv[1] が入力ファイルパス
    if len(sys.argv) < 2:
        # 引数が足りない場合、使い方を表示して終了
        print("使い方: python3 to_markdown.py <input.json> [output.md]")
        print("\n例:")
        print("  python3 to_markdown.py raw/2024/01/2024-01-15-会話.json")
        print("  python3 to_markdown.py raw/2024/01/2024-01-15-会話.json output.md")
        sys.exit(1)  # エラーコード1で終了
    
    # コマンドライン引数から入力ファイルパスを取得
    json_path = sys.argv[1]
    
    # 出力ファイルパスの取得（オプション）
    # 引数が3つ以上ある場合は sys.argv[2] を使用、なければ None
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        # Markdown生成を実行
        result = generate_markdown(json_path, output_path)
        # 成功したら出力先を表示
        print(f"変換完了: {result}")
    except Exception as e:
        # エラーが発生した場合、エラーメッセージを表示して終了
        print(f"エラー: {e}")
        sys.exit(1)


# このスクリプトが直接実行された場合のみ main() を呼び出す
# 他のスクリプトから import された場合は実行されない
if __name__ == "__main__":
    main()
