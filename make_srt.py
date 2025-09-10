import requests
import soundfile as sf
import tempfile
import os

# 音声APIの設定
config = {
    "voice_api": {
        "text": "",
        "speaker_id": 0,
        "model_id": 0,
        "sdp_ratio": 0.2,
        "noise": 0.6,
        "noisew": 0.8,
        "length": 1,
        "language": "JP",
        "auto_split": "true",
        "split_interval": 0,
        "assist_text_weight": 1.0,
        "style": "Neutral",
        "style_weight": 5.0,
    }
}


def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},000"

def parse_comments(lines):
    comments = []
    title = None
    for line in lines:
        if line.startswith('# '):
            title = line.strip()[2:]
        elif line.startswith('< '):
            comments.append(line.strip()[2:])
        elif line.startswith('>>'):
            comments[-1] += " " + line.strip().split('< ')[-1]
    return title, comments

def text_to_speech_duration(text, config):
    API_URL = "http://127.0.0.1:5000/voice"
    params = config["voice_api"].copy()
    params['text'] = text
    response = requests.get(API_URL, params=params)
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_file.flush()
            # ここで一時ファイルを閉じる
        # soundfileを使用して音声ファイルの長さを取得
        data, samplerate = sf.read(tmp_file.name)
        duration_seconds = len(data) / samplerate
        # ファイル使用後に削除
        os.unlink(tmp_file.name)
        return duration_seconds
    else:
        print(f"Failed to generate speech: HTTP {response.status_code}")
        return 0
    
def generate_srt_content(title, comments, config):
    srt_content = []
    current_time = 1  # 2秒後から字幕開始
    srt_index = 1

    # SEファイルを新規作成または置き換え
    open('SE.txt', 'w').close()

    # スレッドタイトルを出力
    title_duration = text_to_speech_duration(title, config) + 1  # TTSの長さに1秒を追加
    start_time = format_time(current_time)
    end_time = format_time(current_time + title_duration)
    srt_content.append(f"{srt_index}\n{start_time} --> {end_time}\n{title}\n\n")
    write_se_file('title', start_time)  # SEファイルにタイトルの開始時間を記録
    srt_index += 1
    current_time += title_duration

    for comment in comments:
        lines = comment.split(">>")
        main_comment = lines[0].strip()
        
        # 本文コメントを出力
        comment_duration = text_to_speech_duration(main_comment, config) + 1  # TTSの長さに1秒を追加
        start_time = format_time(current_time)
        end_time = format_time(current_time + comment_duration)
        srt_content.append(f"{srt_index}\n{start_time} --> {end_time}\n{main_comment}\n\n")
        write_se_file('comment', start_time)  # SEファイルにコメントの開始時間を記録
        srt_index += 1
        current_time += comment_duration
        
        # 返信コメントを出力
        for reply in lines[1:]:
            reply_duration = text_to_speech_duration(reply.strip(), config) + 1  # TTSの長さに1秒を追加
            start_time = format_time(current_time)
            end_time = format_time(current_time + reply_duration)
            srt_content.append(f"{srt_index}\n{start_time} --> {end_time}\n{reply.strip()}\n\n")
            write_se_file('reply', start_time)  # SEファイルに返信の開始時間を記録
            srt_index += 1
            current_time += reply_duration

    return srt_content

def parse_and_generate_srt(input_file_path):
    with open(input_file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    title, comments = parse_comments(lines)
    # ここでconfig変数をgenerate_srt_content関数に渡します
    srt_content = generate_srt_content(title, comments, config)
    return srt_content

def save_srt_file(srt_content, output_file_path):
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.writelines(srt_content)

def write_se_file(se_type, start_time):
    with open('SE.txt', 'a', encoding='utf-8') as file:
        file.write(f"{start_time} {se_type}\n")

if __name__ == "__main__":
    input_file_path = 'input.txt'  # 入力ファイルのパス
    output_file_path = 'output.srt'  # 出力ファイルのパス
    srt_content = parse_and_generate_srt(input_file_path)
    save_srt_file(srt_content, output_file_path)
    print("SRTファイルが生成されました。")