import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops
import pysrt
import budoux
import subprocess
import os
import random
from pathlib import Path
import atexit
import tempfile

def wrap_text(text, max_width, font, draw, font_size):
    # BudouXのデフォルトの日本語パーサーをロード
    parser = budoux.load_default_japanese_parser()
    
    # テキストをフレーズに分割
    phrases = parser.parse(text)
    
    wrapped_text = ""
    current_line = ""
    for phrase in phrases:
        # 現在の行にフレーズを追加した場合の長さを計算
        test_line = current_line + phrase if current_line else phrase
        text_length = draw.textlength(test_line, font=font)
        
        # テキストの長さが最大幅を超える場合、現在の行を折り返し、新しい行を開始
        if text_length > max_width and current_line:
            wrapped_text += current_line + '\n'
            current_line = phrase
        else:
            current_line = test_line
    
    # 最後の行を追加
    wrapped_text += current_line
    
    return wrapped_text

def load_emotion_data(emo_file_path):
    emotion_data = []
    with open(emo_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(': ')
            timestamps = parts[0].split(' --> ')
            emotion = parts[1]
            emotion_data.append((timestamps, emotion))
    return emotion_data

def timestamp_to_seconds(timestamp):
    """タイムスタンプ（'HH:MM:SS'形式）を秒数に変換する"""
    hours, minutes, seconds = map(int, timestamp.split(':'))
    return hours * 3600 + minutes * 60 + seconds

# 一時ファイルを削除する関数
def cleanup_temp_file(path):
    path.unlink(missing_ok=True)

def preprocess_image(image_path):
    # 画像を読み込む
    image = Image.open(image_path).convert("RGBA")
    
    # 画像を300x300にリサイズ
    image = image.resize((300, 300), Image.Resampling.LANCZOS)
    
    # 円形のマスクを作成
    mask = Image.new('L', (300, 300), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, 300, 300), fill=255)
    
    # マスクを適用して画像を円形に切り抜く
    alpha = image.split()[3]
    alpha = ImageChops.multiply(alpha, mask)
    image.putalpha(alpha)
    
    # 白い背景画像を作成
    background = Image.new('RGBA', (300, 300), (255, 255, 255, 255))
    background.putalpha(mask)
    
    # 背景画像に円形に切り抜いた画像を配置
    background.paste(image, (0, 0), alpha)

    # 画像を左右反転
    background = background.transpose(Image.FLIP_LEFT_RIGHT)
    
    # 処理後の画像を一時ファイルに保存し、そのパスを返す
    # dir引数を省略してシステムの一時ファイルディレクトリを使用
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.temp.png')
    background.save(temp_file.name)
    
    # 一時ファイルのパスを返す前に、一時ファイルを削除する処理を追加
    temp_path = Path(temp_file.name)
    temp_file.close()  # tempfileを閉じる

    # 終了時に一時ファイルを削除するように登録
    atexit.register(cleanup_temp_file, temp_path)

    return temp_path

def map_emotions_to_images(emotion_data):
    emotion_image_map = {}
    used_images = {}  # 各感情に対して使用された画像を追跡する辞書

    for timestamps, emotion in emotion_data:
        key = f"{timestamps[0]}-{timestamps[1]}-{emotion}"
        emo_images_path = Path('emoimages') / emotion
        images = list(emo_images_path.glob('*.png'))

        if emotion not in used_images:
            used_images[emotion] = []

        # まだ使用されていない画像のみを選択肢とする
        available_images = [img for img in images if img not in used_images[emotion]]
        if not available_images:  # 使用可能な画像がない場合、リセット
            available_images = images

        if available_images:
            image_path = random.choice(available_images)
            used_images[emotion].append(image_path)  # 使用した画像を記録
            processed_image_path = preprocess_image(image_path)
            emotion_image_map[key] = processed_image_path

    return emotion_image_map

def overlay_emotion_image(img_pil, image_path, video_size):
    try:
        emo_image = Image.open(image_path).convert("RGBA")
        # 画像のサイズを調整
        emo_image = emo_image.resize((250, 250))  # 画像サイズは適宜調整してください
        img_w, _ = emo_image.size
        bg_w, _ = video_size
        # 画像をビデオの右上に配置
        offset = (bg_w - img_w - 10, 10)  # 右端から10ピクセルの余白を設定
        # 背景画像にオーバーレイ画像を合成
        img_pil.paste(emo_image, offset, emo_image)
    except Exception as e:
        print(f"画像のオーバーレイ中にエラーが発生しました: {e}")

    return img_pil

def create_video_from_srt(srt_path, output_path, audio_path, video_size=(1280, 720), bg_video_path='background.mp4'):
    subs = pysrt.open(srt_path)
    fps = 24  # Assuming 24 FPS for the video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, video_size)
    font_path = r"C:\Users\yuto9\Desktop\test-program1\auto_nanj_matome\GenEiNuGothic-EB_v1.1\GenEiNuGothic-EB.ttf"
    font_size = 96
    font = ImageFont.truetype(font_path, font_size)

    bg_cap = cv2.VideoCapture(bg_video_path)
    bg_frame_count = int(bg_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    bg_fps = bg_cap.get(cv2.CAP_PROP_FPS)
    frame_duration = 1.0 / bg_fps

    last_subtitle_end_time = subs[-1].end.ordinal / 1000.0 if subs else 0
    current_time = 0
    video_duration_with_extra_time = last_subtitle_end_time + 10  # Add 10 seconds of background video at the end

    # EMO_pysrt.txtから感情データを読み込む
    emotion_data = load_emotion_data('EMO_pysrt.txt')
    emotion_image_map = map_emotions_to_images(emotion_data)

    while current_time <= video_duration_with_extra_time:
        bg_cap.set(cv2.CAP_PROP_POS_FRAMES, int((current_time / frame_duration) % bg_frame_count))
        ret, bg_frame = bg_cap.read()
        if not ret:
            break  # In case reading the background frame fails, exit the loop

        img_pil = Image.fromarray(cv2.cvtColor(bg_frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(img_pil, "RGBA")
        
        # 常時表示するテキストとそのフォントサイズを設定
        constant_text = "AIなんJ民の反応集"
        constant_font_size = 40
        constant_font = ImageFont.truetype(font_path, constant_font_size)

        # 常時表示するテキストを左上に描画（黒い縁をつける）
        shadow_offset = [(1,1), (-1,-1), (1,-1), (-1,1)]  # 影のオフセット
        for offset in shadow_offset:
            draw.text((10 + offset[0], 10 + offset[1]), constant_text, font=constant_font, fill=(0, 0, 0))
        draw.text((10, 10), constant_text, font=constant_font, fill=(255, 255, 255))

        # 現在の時間に対応する感情に基づいて画像をオーバーレイ
        current_emotion = None
        for timestamps, emotion in emotion_data:
            start_time = timestamp_to_seconds(timestamps[0])
            end_time = timestamp_to_seconds(timestamps[1])
            if start_time <= current_time <= end_time:
                current_emotion = emotion
                break

        if current_emotion:
            # タイムスタンプと感情をキーにして画像パスを取得
            key = f"{timestamps[0]}-{timestamps[1]}-{current_emotion}"
            image_path = emotion_image_map.get(key)
            if image_path:
                img_pil = overlay_emotion_image(img_pil, image_path, video_size)

        for sub in subs:
            if sub.start.ordinal / 1000 <= current_time <= sub.end.ordinal / 1000:
                wrapped_text = wrap_text(sub.text, video_size[0] - 40, font, draw, font_size)
                text_lines = wrapped_text.split('\n')
                text_width = max(draw.textlength(line, font=font) for line in text_lines)
                text_height = font_size * len(text_lines)
                x = (video_size[0] - text_width) / 2
                y = (video_size[1] - text_height) / 2

                padding = 10  # テキスト周りの余白を追加

                # 背景窓のサイズと位置を計算
                window_x = int(x - padding)
                window_y = int(y - padding)
                window_width = int(text_width + padding * 2)
                window_height = int(text_height + padding * 2)

                # 背景窓用の画像を作成（半透明の黒）
                window_image = Image.new('RGBA', (window_width, window_height), (0, 0, 0, 128))

                # 元の画像の該当部分を切り出す
                bg_section = img_pil.crop((window_x, window_y, window_x + window_width, window_y + window_height))

                # 背景窓を元の画像の該当部分にブレンド
                blended_section = Image.alpha_composite(bg_section, window_image)

                # ブレンドした背景窓を元の画像に貼り付ける
                img_pil.paste(blended_section, (window_x, window_y), blended_section)

                # テキストを描画
                draw = ImageDraw.Draw(img_pil)
                draw.text((x, y), wrapped_text, font=font, fill=(255, 255, 255))

        # PIL画像をRGBA形式のNumPy配列に変換
        img_array = np.array(img_pil)

        # アルファチャンネルを取得
        alpha_channel = img_array[:, :, 3] / 255.0
        alpha_channel = np.stack([alpha_channel, alpha_channel, alpha_channel], axis=-1)

        # RGBチャンネルのみを取得し、BGR形式に変換
        img_bgr = cv2.cvtColor(img_array[:, :, :3], cv2.COLOR_RGB2BGR)

        # 背景フレームとアルファブレンディングを行う
        blended_frame = (img_bgr * alpha_channel + bg_frame * (1 - alpha_channel)).astype(np.uint8)

        # アルファブレンディングを行った画像をビデオに書き込む
        out.write(blended_frame)

        current_time += 1/fps

    bg_cap.release()
    out.release()

    final_output_path = 'output_with_audio.mp4'
    if os.path.exists(final_output_path):
        os.remove(final_output_path)

    cmd = f'ffmpeg -i {output_path} -i {audio_path} -c:v copy -c:a aac -strict experimental {final_output_path}'
    subprocess.call(cmd, shell=True)

if __name__ == "__main__":
    srt_path = 'output.srt'
    output_path = 'video_from_srt.mp4'
    audio_path = 'output_with_se.wav'
    create_video_from_srt(srt_path, output_path, audio_path, bg_video_path='background.mp4')