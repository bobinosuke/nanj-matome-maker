from PIL import Image, ImageDraw, ImageFont
import budoux
import os
import random

# BudouXのパーサーを初期化
parser = budoux.load_default_japanese_parser()

# thumbnail_backgroundフォルダ内のpngファイルのリストを取得
background_files = [f for f in os.listdir('thumbnail_background') if f.endswith('.png')]
# ランダムに1つの背景画像を選択
selected_background = random.choice(background_files)
# 選択した背景画像を720pのサイズで開き、RGBAモードに変換
background = Image.open(os.path.join('thumbnail_background', selected_background)).resize((1280, 720)).convert('RGBA')

# 透かし画像を開き、RGBAモードに変換
watermark = Image.open('nanj.png').convert('RGBA')

# 透かし画像のアルファチャンネルを取得し、透明度を調整
alpha = watermark.split()[3]
alpha = alpha.point(lambda p: p * 0.3 if p > 0 else 0)  # 不透明部分の透明度を30%に設定

# 調整したアルファチャンネルを透かし画像に再結合
watermark.putalpha(alpha)

# 背景画像を720pのサイズで開き、RGBAモードに変換
background = Image.open(os.path.join('thumbnail_background', selected_background)).resize((1280, 720)).convert('RGB')

# 透かし画像を背景画像の中央に配置するための座標を計算
x = (background.width - watermark.width) // 2
y = (background.height - watermark.height) // 2

# 透かし画像を背景画像に合成
background.paste(watermark, (x, y), watermark)

draw = ImageDraw.Draw(background)

# テキストを読み込む
with open('input.txt', 'r', encoding='utf-8') as file:
    lines = file.readlines()

# '>>'で始まる最初の行を見つけ、'>>'を除去してトリムする
quote_line = next((line[2:].strip() for line in lines if line.startswith('>>')), None)

# テキストが見つからない場合は処理をスキップ
if quote_line is None:
    raise ValueError("No line starting with '>>' found in input.txt")

# テキストを描画するためのフォントを設定
quote_font_path = r"C:\Users\yuto9\Desktop\test-program1\auto_nanj_matome\GenEiNuGothic-EB_v1.1\GenEiNuGothic-EB.ttf"
quote_font_size = 48 if len(quote_line) <= 5 or len(quote_line) <= 20 else 38
quote_font = ImageFont.truetype(quote_font_path, quote_font_size)

# テキストの幅を取得
quote_text_width = draw.textlength(quote_line, font=quote_font)

# テキストの高さを計算（フォントサイズ * テキストの行数）
quote_text_height = quote_font_size * quote_line.count('\n') + 1  # +1 は最後の行を含めるため

# テキストを画像の右下に配置するための座標を計算
quote_x = background.width - quote_text_width - 60  # 10ピクセルの余白を設定
quote_y = background.height - quote_text_height - 80

# 縁の幅を定義
edge_width = 2  # 縁の幅

line_spacing = quote_font_size // 2
quote_text_height = quote_font_size * (quote_line.count('\n') + 1) + line_spacing * (quote_line.count('\n'))

# 白い背景を描画
padding = 10  # テキスト周りの余白を増やす
background_color = (255, 255, 255)  # 白色
draw.rectangle(
    [quote_x - padding - edge_width, quote_y - padding - edge_width, quote_x + quote_text_width + padding + edge_width, quote_y + quote_text_height + padding + edge_width],
    fill=background_color
)

# 黒い縁を描画
edge_color = (0, 0, 0)  # 黒色
edge_width = 1  # 縁の幅を少し大きくする
draw.rectangle(
    [quote_x - padding - edge_width * 3, quote_y - padding - edge_width * 3, quote_x + quote_text_width + padding + edge_width * 3, quote_y + quote_text_height + padding + edge_width * 3],
    outline=edge_color, width=edge_width
)

# テキストを描画（赤色で右下に描画）
draw.text((quote_x, quote_y), quote_line, fill=(255, 0, 0), font=quote_font)

# テキストを読み込む
with open('input.txt', 'r', encoding='utf-8') as file:
    text = file.read()

# '#'で始まる行だけを抽出して結合し、'#'を除去
text_to_draw = '\n'.join(line[1:].strip() for line in text.split('\n') if line.startswith('#'))

# テキストを描画するためのフォントを設定（一時的なフォントサイズを設定）
font_path = r"C:\Users\yuto9\Desktop\test-program1\auto_nanj_matome\GenEiNuGothic-EB_v1.1\GenEiNuGothic-EB.ttf"
temp_font_size = 80  # 一時的なフォントサイズ
font = ImageFont.truetype(font_path, temp_font_size)

# BudouXを使って改行を入れる部分を修正（空白を挿入しない）
parsed_text = parser.parse(text_to_draw)
# 画面幅に合わせて改行を入れる
max_width = background.width - 40  # 余白を考慮
formatted_text_lines = []
current_line = ""
for word in parsed_text:
    # 現在の行に単語を追加した場合の幅を計算（一時的なフォントサイズを使用）
    if current_line:  # current_lineが空でない場合、単語を追加
        line_with_word = f"{current_line}{word}"
    else:  # current_lineが空の場合、最初の単語として設定
        line_with_word = word
    line_width = draw.textlength(line_with_word, font=font)
    # 画面幅を超える場合は現在の行を確定し、新しい行を開始
    if line_width > max_width and current_line != "":
        formatted_text_lines.append(current_line)
        current_line = word
    else:
        current_line = line_with_word
# 最後の行を追加
if current_line:
    formatted_text_lines.append(current_line)
formatted_text = '\n'.join(formatted_text_lines)

# formatted_textが定義された後に、文字数に応じてフォントサイズを再設定
font_size = 112 if len(formatted_text) <= 20 else 80
font = ImageFont.truetype(font_path, font_size)

# 各行のテキストの幅を測定し、最も長いものを選択
text_width = max(draw.textlength(line, font=font) for line in formatted_text.split('\n'))

# テキストの高さを計算（フォントサイズ * テキストの行数）
text_height = font_size * (formatted_text.count('\n') + 1)  # +1 は最後の行を含めるため

# テキストを画像の中央に配置
text_x = (background.width - text_width) / 2
text_y = (background.height - text_height) / 2

# テキスト画像を作成
text_image = Image.new('RGBA', (int(text_width + 12), int(text_height + 12)), (255, 255, 255, 0))  # 縁の分だけサイズを大きくする
text_draw = ImageDraw.Draw(text_image)

# 影の色、縁の色、オフセットを設定
shadow_color = (0, 0, 0, 255)  # 半透明の黒
edge_color = (0, 0, 0, 255)  # 不透明の黒
shadow_offset = (4, 4)  # 影のオフセットをさらに大きくする
# 縁のオフセットをさらに増やして太くする
edge_offsets = [
    (-3, -3), (-3, 3), (3, -3), (3, 3),
    (-3, 0), (3, 0), (0, -3), (0, 3),
    (-3, -1), (-3, 1), (3, -1), (3, 1),
    (-1, -3), (-1, 3), (1, -3), (1, 3),
    (-2, -2), (-2, 2), (2, -2), (2, 2),
    (-2, -1), (-2, 1), (2, -1), (2, 1),
    (-1, -2), (-1, 2), (1, -2), (1, 2),
    (-2, 0), (2, 0), (0, -2), (0, 2)
]

# 縁を描画（テキスト画像上に）
for offset in edge_offsets:
    text_draw.multiline_text((offset[0] + 4, offset[1] + 4), formatted_text, fill=edge_color, font=font, align="center")

# 影を描画（テキスト画像上に）
text_draw.multiline_text((shadow_offset[0] + 4, shadow_offset[1] + 4), formatted_text, fill=shadow_color, font=font, align="center")

# 本来のテキストを描画（白色で中央に描画、テキスト画像上に）
text_draw.multiline_text((4, 4), formatted_text, fill=(255, 255, 255), font=font, align="center")

# テキスト画像の縦横比を保ちつつ、背景画像の90%の幅、80%の高さに収まるようにサイズを調整
target_width = int(background.width * 0.95)
target_height = int(background.height * 0.8)

# テキスト画像の縦横比を計算
aspect_ratio = text_width / text_height

# 目標のサイズに対してテキスト画像の縦横比を保ちつつ、どちらかが収まるようにサイズを調整
if target_width / target_height > aspect_ratio:
    # 背景の高さに合わせて幅を調整
    new_height = target_height
    new_width = int(aspect_ratio * new_height)
else:
    # 背景の幅に合わせて高さを調整
    new_width = target_width
    new_height = int(new_width / aspect_ratio)

# テキスト画像を新しいサイズにリサイズ
text_image = text_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

# 新しいサイズで中央に配置するための座標を計算
new_x = (background.width - new_width) // 2
new_y = (background.height - new_height) // 2

# 背景画像にテキスト画像を合成
background.paste(text_image, (new_x, new_y), text_image)

# 「※ AIなんJ民」テキストに縁とシャドウを追加して画面左上に表示するためのコードを修正

# テキスト設定
ai_text = "AIなんJ民たちの反応集"
ai_font_path = r"C:\Users\yuto9\Desktop\test-program1\auto_nanj_matome\GenEiNuGothic-EB_v1.1\GenEiNuGothic-EB.ttf"
ai_font_size = 52  # フォントサイズ
ai_font = ImageFont.truetype(ai_font_path, ai_font_size)

# テキストの幅を取得
ai_text_width = draw.textlength(ai_text, font=ai_font)
# テキストの高さを計算（フォントサイズ * テキストの行数）
ai_text_height = ai_font_size * ai_text.count('\n') + ai_font_size  # +1 は最後の行を含めるため

# テキストを画像の左上に配置するための座標を計算
ai_x = 20  # 左端から20ピクセルの余白を設定
ai_y = 20  # 上端から20ピクセルの余白を設定

# シャドウのオフセット
shadow_offset = 2

# シャドウを描画（黒色で左上に描画）
draw.text((ai_x + shadow_offset, ai_y + shadow_offset), ai_text, fill=(0, 0, 0), font=ai_font)

# 縁を描画するためのオフセットリスト
edge_offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)]

# 縁を描画（黒色で左上に描画）
for offset in edge_offsets:
    draw.text((ai_x + offset[0], ai_y + offset[1]), ai_text, fill=(0, 0, 0), font=ai_font)

# 本来のテキストを描画（白色で左上に描画）
draw.text((ai_x, ai_y), ai_text, fill=(255, 255, 255), font=ai_font)


# 画像を保存
background.save('youtube_thumbnail.png', format='PNG')