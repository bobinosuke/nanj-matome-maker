import subprocess
import os
import sys  # sys モジュールをインポート

def run_make_srt():
    subprocess.run([sys.executable, 'make_srt.py'], check=True)

def run_make_emo_analysis():
    subprocess.run([sys.executable, 'make_emo_analysis.py'], check=True)

def run_make_audio():
    # sys.executable を使用して現在の Python インタープリタのパスを取得
    subprocess.run([sys.executable, 'make_audio.py'], check=True)

def run_make_movie_text():
    subprocess.run([sys.executable, 'make_movie_text.py'], check=True)

def run_make_thumbnail():
    subprocess.run([sys.executable, 'make_thumbnail.py'], check=True)

def set_thumbnail_to_video(thumbnail_path, video_path, output_path):
    subprocess.run(['ffmpeg', '-i', video_path, '-i', thumbnail_path, '-map', '0', '-map', '1', '-c', 'copy', '-disposition:v:1', 'attached_pic', '-y', output_path], check=True)

def cleanup_files(keep_files, generated_files):
    for filename in os.listdir('.'):
        if filename not in keep_files and filename in generated_files:
            os.remove(filename)

def get_video_title_from_input():
    with open('input.txt', 'r', encoding='utf-8') as file:
        for line in file:
            if line.startswith('#'):
                title = line.strip()[1:].strip()
                title = title.replace('、', '').replace(' ', '_').replace(',', '').replace('|', '_').replace('/', '_').replace('\\', '_')
                return f"{title}.mp4"
    return "default_video_title.mp4"

if __name__ == "__main__":
    generated_files_after_srt = ['output.srt', 'SE.txt']
    generated_files_after_audio = ['output.wav', 'final_output_with_bgm.wav', 'output_with_se.wav']
    generated_files_after_movie_text = ['video_from_srt.mp4', 'output_with_audio.mp4']

    run_make_srt()
    run_make_emo_analysis()

    run_make_audio()

    run_make_movie_text()

    # サムネイル生成を実行
    run_make_thumbnail()

    # タイトルを取得して最終出力ファイル名を設定
    final_video_title = get_video_title_from_input()

    # サムネイルを動画に設定し、最終出力を生成
    set_thumbnail_to_video('youtube_thumbnail.png', 'output_with_audio.mp4', final_video_title)