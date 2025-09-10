import cv2
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
    parser = budoux.load_default_japanese_parser()
    phrases = parser.parse(text)
    wrapped_text = ""
    current_line = ""
    for phrase in phrases:
        test_line = current_line + phrase if current_line else phrase
        text_length = draw.textlength(test_line, font=font)
        if text_length > max_width and current_line:
            wrapped_text += current_line + '\n'
            current_line = phrase
        else:
            current_line = test_line
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
    hours, minutes, seconds = map(int, timestamp.split(':'))
    return hours * 3600 + minutes * 60 + seconds

def cleanup_temp_file(path):
    path.unlink(missing_ok=True)

def preprocess_image(image_path):
    image = Image.open(image_path).convert("RGBA")
    image = image.resize((300, 300), Image.Resampling.LANCZOS)
    mask = Image.new('L', (300, 300), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, 300, 300), fill=255)
    alpha = image.split()[3]
    alpha = ImageChops.multiply(alpha, mask)
    image.putalpha(alpha)
    background = Image.new('RGBA', (300, 300), (255, 255, 255, 255))
    background.putalpha(mask)
    background.paste(image, (0, 0), alpha)
    background = background.transpose(Image.FLIP_LEFT_RIGHT)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.temp.png')
    background.save(temp_file.name)
    temp_path = Path(temp_file.name)
    temp_file.close()
    atexit.register(cleanup_temp_file, temp_path)
    return temp_path

def map_emotions_to_images(emotion_data):
    emotion_image_map = {}
    used_images = {}
    for timestamps, emotion in emotion_data:
        key = f"{timestamps[0]}-{timestamps[1]}-{emotion}"
        emo_images_path = Path('emoimages') / emotion
        images = list(emo_images_path.glob('*.png'))
        if emotion not in used_images:
            used_images[emotion] = []
        available_images = [img for img in images if img not in used_images[emotion]]
        if not available_images:
            available_images = images
        if available_images:
            image_path = random.choice(available_images)
            used_images[emotion].append(image_path)
            processed_image_path = preprocess_image(image_path)
            emotion_image_map[key] = processed_image_path
    return emotion_image_map

def overlay_emotion_image(img_pil, image_path, video_size):
    try:
        emo_image = Image.open(image_path).convert("RGBA")
        emo_image = emo_image.resize((250, 250))
        img_w, _ = emo_image.size
        bg_w, _ = video_size
        offset = (bg_w - img_w - 10, 10)
        img_pil.paste(emo_image, offset, emo_image)
    except Exception as e:
        print(f"画像のオーバーレイ中にエラーが発生しました: {e}")
    return img_pil

def create_video_from_srt(srt_path, output_path, audio_path, video_size=(1280, 720), bg_video_path='background.mp4'):
    subs = pysrt.open(srt_path)
    fps = 24
    font_path = r"C:\Users\yuto9\Desktop\test-program1\auto_nanj_matome\GenEiNuGothic-EB_v1.1\GenEiNuGothic-EB.ttf"
    font_size = 96
    font = ImageFont.truetype(font_path, font_size)
    bg_cap = cv2.VideoCapture(bg_video_path)
    bg_frame_count = int(bg_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    bg_fps = bg_cap.get(cv2.CAP_PROP_FPS)
    frame_duration = 1.0 / bg_fps

    last_subtitle_end_time = subs[-1].end.ordinal / 1000.0 if subs else 0
    current_time = 0
    video_duration_with_extra_time = last_subtitle_end_time + 10

    emotion_data = load_emotion_data('EMO_pysrt.txt')
    emotion_image_map = map_emotions_to_images(emotion_data)

    # 一時ディレクトリを作成してフレームを保存
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        frame_number = 0

        while current_time <= video_duration_with_extra_time:
            bg_cap.set(cv2.CAP_PROP_POS_FRAMES, int((current_time / frame_duration) % bg_frame_count))
            ret, bg_frame = bg_cap.read()
            if not ret:
                break

            img_pil = Image.fromarray(cv2.cvtColor(bg_frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
            draw = ImageDraw.Draw(img_pil, "RGBA")

            constant_text = "AIなんJ民の反応集"
            constant_font_size = 52
            constant_font = ImageFont.truetype(font_path, constant_font_size)
            shadow_offset = [(1,1), (-1,-1), (1,-1), (-1,1)]
            for offset in shadow_offset:
                draw.text((10 + offset[0], 10 + offset[1]), constant_text, font=constant_font, fill=(0, 0, 0))
            draw.text((10, 10), constant_text, font=constant_font, fill=(255, 255, 255))

            current_emotion = None
            for timestamps, emotion in emotion_data:
                start_time = timestamp_to_seconds(timestamps[0])
                end_time = timestamp_to_seconds(timestamps[1])
                if start_time <= current_time <= end_time:
                    current_emotion = emotion
                    break

            if current_emotion:
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

                    padding = 10

                    window_x = int(x - padding)
                    window_y = int(y - padding)
                    window_width = int(text_width + padding * 2)
                    window_height = int(text_height + padding * 2)

                    window_image = Image.new('RGBA', (window_width, window_height), (0, 0, 0, 128))
                    bg_section = img_pil.crop((window_x, window_y, window_x + window_width, window_y + window_height))
                    blended_section = Image.alpha_composite(bg_section, window_image)
                    img_pil.paste(blended_section, (window_x, window_y), blended_section)

                    draw = ImageDraw.Draw(img_pil)
                    draw.text((x, y), wrapped_text, font=font, fill=(255, 255, 255))

            frame_path = temp_dir_path / f"frame_{frame_number:05d}.png"
            img_pil.save(frame_path)
            frame_number += 1
            current_time += 1/fps

        bg_cap.release()

        # FFmpegを使用してNVENCで動画をエンコード
        ffmpeg_cmd = [
            "ffmpeg",
            "-hwaccel", "cuda",
            "-r", str(fps),
            "-f", "image2",
            "-s", f"{video_size[0]}x{video_size[1]}",
            "-i", str(temp_dir_path / "frame_%05d.png"),
            "-c:v", "h264_nvenc",
            "-pix_fmt", "yuv420p",
            "-y",  # 同名ファイルが存在する場合は上書きする
            output_path
        ]
        subprocess.run(ffmpeg_cmd, check=True)

    # エンコードされた動画にオーディオをマージ
    final_output_path = 'output_with_audio.mp4'
    if os.path.exists(final_output_path):
        os.remove(final_output_path)
    ffmpeg_merge_cmd = [
        "ffmpeg",
        "-i", output_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-strict", "experimental",
        "-y",  # 同名ファイルが存在する場合は上書きする
        final_output_path
    ]
    subprocess.run(ffmpeg_merge_cmd, check=True)

if __name__ == "__main__":
    srt_path = 'output.srt'
    output_path = 'video_from_srt.mp4'
    audio_path = 'output_with_se.wav'
    create_video_from_srt(srt_path, output_path, audio_path, bg_video_path='background.mp4')