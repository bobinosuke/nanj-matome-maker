import pysrt
import requests
import tempfile
import os
from testengtokana2 import EnglishToKana, replace_english_to_kana
from pydub import AudioSegment
import numpy as np
import random

def text_to_speech(subs, config):
    import random  # ランダムモジュールをインポート
    API_URL = "http://127.0.0.1:5000/voice"
    audio_files = []
    e2k = EnglishToKana()  # カタカナ変換のためのインスタンスを作成
    model_ids = list(range(1))  # 0から4までのリストを作成
    random.shuffle(model_ids)  # リストをシャッフルしてランダムな順序にする

    for sub in subs:
        original_text = sub.text.replace("AI", "エーアイ")  # AIをエーアイに変換
        # 英語をカタカナに変換するために修正された関数を使用
        kana_text = replace_english_to_kana(original_text, e2k)
        params = config["voice_api"].copy()
        params['text'] = kana_text  # 変換後のテキストを使用
        if not model_ids:  # model_idsが空になったら再度シャッフルしてリセット
            model_ids = list(range(1))
            random.shuffle(model_ids)
        params['model_id'] = model_ids.pop(0)  # リストの先頭からmodel_idを取得し、その要素をリストから削除

        response = requests.get(API_URL, params=params)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(response.content)
                audio_files.append((tmp_file.name, sub.start.ordinal, sub.end.ordinal))
        else:
            print(f"Failed to generate speech for subtitle index {sub.index}: HTTP {response.status_code}")
    return audio_files

def integrate_audio(audio_files):
    # 最後の音声ファイルの終了時間に10秒の余韻を加える
    if audio_files:
        video_duration_in_milliseconds = max(end for _, _, end in audio_files) + 10000  # 10秒をミリ秒に変換して加算
    else:
        video_duration_in_milliseconds = 10000  # 音声ファイルがない場合は10秒の余韻のみ

    combined = AudioSegment.silent(duration=video_duration_in_milliseconds)  # ミリ秒単位

    for file_path, start, end in audio_files:
        audio = AudioSegment.from_file(file_path)
        combined = combined.overlay(audio, position=start)

        os.remove(file_path)  # 一時ファイルを削除

    # BGMは無音化しないため、ここでは何も変更しない
    combined.export("output.wav", format="wav")


def apply_reverb_effect(sound, decay_factors, delay_ms):

    samples = np.array(sound.get_array_of_samples())
    sample_rate = sound.frame_rate
    mixed_samples = samples.astype(np.float64)

    for decay, delay in zip(decay_factors, delay_ms):
        delay_samples = int(delay * sample_rate / 1000)
        delayed_samples = np.zeros_like(mixed_samples)
        delayed_samples[delay_samples:] = mixed_samples[:-delay_samples] * decay
        mixed_samples += delayed_samples

    # クリッピングを防ぐために正規化
    max_val = np.max(np.abs(mixed_samples))
    if max_val > 0:
        mixed_samples = np.clip(mixed_samples / max_val, -1.0, 1.0)

    # np.int16の範囲に合わせてスケーリング
    mixed_samples = mixed_samples * 32767  # np.int16の最大値
    mixed_sound = sound._spawn(mixed_samples.astype(np.int16).tobytes())
    return mixed_sound

def combined_audio(audio_files):
    output_audio = AudioSegment.from_file("output.wav")
    bgm_audio = AudioSegment.from_file("BGM.wav")
    bgm_audio = bgm_audio - 12

    bgm_duration = len(bgm_audio)
    output_duration = len(output_audio)
    looped_bgm = bgm_audio
    while len(looped_bgm) < output_duration:
        looped_bgm += bgm_audio
    looped_bgm = looped_bgm[:output_duration]

    final_audio = output_audio.overlay(looped_bgm)

    if audio_files:
        last_subtitle_start_time = audio_files[-1][1]
        reverb_part = output_audio[last_subtitle_start_time:]
        reverb_part = reverb_part.overlay(reverb_part, position=100, gain_during_overlay=-6)

        # apply_delay_effectの代わりにapply_reverb_effectを使用
        reverb_part_with_reverb = apply_reverb_effect(reverb_part, decay_factors=[0.3, 0.2, 0.15], delay_ms=[45, 75, 105])

        final_narration_with_reverb = output_audio[:last_subtitle_start_time] + reverb_part_with_reverb
        final_audio_with_reverb = final_narration_with_reverb.overlay(looped_bgm)
    else:
        final_audio_with_reverb = final_audio

    final_audio_with_reverb.export("final_output_with_bgm.wav", format="wav")

def insert_se_at_timestamps(se_file_path, audio_file_path, se_folder_path):
    # SE.txtを読み込む
    with open(se_file_path, 'r', encoding='utf-8') as file:
        se_lines = file.readlines()

    # 元のオーディオファイルを読み込む
    main_audio = AudioSegment.from_file(audio_file_path)

    for line in se_lines:
        timestamp, se_type = line.strip().split(' ')
        # タイムスタンプからミリ秒を取り除く
        timestamp = timestamp.split(',')[0]  # "00:00:02,000" -> "00:00:02"
        hours, minutes, seconds = map(int, timestamp.split(':'))
        milliseconds = (hours * 3600 + minutes * 60 + seconds) * 1000

        # SEファイルをランダムに選択
        se_files = [f for f in os.listdir(os.path.join(se_folder_path, se_type)) if f.endswith('.mp3')]
        se_file = random.choice(se_files)
        se_audio = AudioSegment.from_file(os.path.join(se_folder_path, se_type, se_file))

        # SEの音量を50%に調整
        se_audio = se_audio - 10  # 音量を約半分に下げる

        # SEを指定されたタイムスタンプに挿入
        main_audio = main_audio.overlay(se_audio, position=milliseconds)

    # 結果をファイルにエクスポート
    main_audio.export("output_with_se.wav", format="wav")

def main():
    # SRTファイルのパスをoutput.srtに設定
    srt_file_path = "output.srt"

    # SRTファイルから字幕を読み込む
    subs = pysrt.open(srt_file_path)

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

    # 字幕を音声に変換
    audio_files = text_to_speech(subs, config)

    # 音声ファイルを統合し、動画の全長を設定
    integrate_audio(audio_files)

    # BGMを合成し、最後の字幕にエコーをかける
    combined_audio(audio_files)

    # SEを挿入し、最終的な音声ファイルを出力
    insert_se_at_timestamps('SE.txt', 'final_output_with_bgm.wav', 'SE')

if __name__ == "__main__":
    main()