from transformers import AutoTokenizer, AutoModelForSequenceClassification, LukeConfig
import torch
import pysrt
import datetime

# モデルとトークナイザーの準備
tokenizer = AutoTokenizer.from_pretrained("Mizuiro-sakura/luke-japanese-large-sentiment-analysis-wrime")
config = LukeConfig.from_pretrained('Mizuiro-sakura/luke-japanese-large-sentiment-analysis-wrime', output_hidden_states=True)    
model = AutoModelForSequenceClassification.from_pretrained('Mizuiro-sakura/luke-japanese-large-sentiment-analysis-wrime', config=config)

def analyze_emotion(text):
    max_seq_length = 512
    token = tokenizer(text, truncation=True, max_length=max_seq_length, padding="max_length")
    output = model(torch.tensor(token['input_ids']).unsqueeze(0), torch.tensor(token['attention_mask']).unsqueeze(0))
    max_index = torch.argmax(torch.tensor(output.logits))
    emotions = ['joy', 'sadness', 'anticipation', 'surprise', 'anger', 'fear', 'disgust', 'trust']
    return emotions[max_index]

def convert_timestamp(ts):
    return datetime.timedelta(hours=ts.hour, minutes=ts.minute, seconds=ts.second, microseconds=ts.microsecond)

def process_srt_pysrt(file_path):
    subtitles = pysrt.open(file_path, encoding='utf-8')
    with open('EMO_pysrt.txt', 'w', encoding='utf-8') as emo_file:
        for index, subtitle in enumerate(subtitles):
            if index == 0:  # 最初の字幕をスキップ
                continue
            emotion = analyze_emotion(subtitle.text)
            start_ts = subtitle.start.to_time()  # pysrtではdatetime.timeオブジェクトが返される
            end_ts = subtitle.end.to_time()
            emo_file.write(f"{start_ts} --> {end_ts}: {emotion}\n")

# SRTファイルのパス
srt_file_path = 'output.srt'
process_srt_pysrt(srt_file_path)
