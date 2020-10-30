import srt
import time
import os
from google.cloud import speech
from google.cloud import storage
os.environ ["GOOGLE_APPLICATION_CREDENTIALS"] = "stoked-edition-293116-95e244eb4204.json"

from flask import Flask, request, render_template
import os
app = Flask(__name__)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

import argparse
parser = argparse.ArgumentParser()
parser.add_argument(
    "--storage_uri",
    type=str,
    default="gs://spin-5339",
)
parser.add_argument(
    "--upload_uri",
    type=str,
    default="en.wav",
)

parser.add_argument(
    "--language_code",
    type=str,
    default="en-US",
)
parser.add_argument(
    "--sample_rate_hertz",
    type=int,
    default=16000,
)
parser.add_argument(
    "--out_file",
    type=str,
    default="en",
)
parser.add_argument(
    "--max_chars",
    type=int,
    default=40,
)

args = parser.parse_args()

filename = ""
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        target =os.path.join(APP_ROOT, 'audioFile')
        if not os.path.isdir(target):
            os.mkdir(target)
        for file in request.files.getlist("file"):
            print(file)
            filename = file.filename
            destination = "\\".join([target,filename])
            file.save(destination)
        location = "audioFile/"+filename
        upload_file(args,location,filename)
        subs = long_running_recognize(args)
        diction ={"key":"SpeechToText", "Translated":srt.compose(subs)}
        return diction
        write_srt(args, subs)
        write_txt(args, subs)
    return "<!doctype html><title>Upload new File</title><h1>Upload new File</h1><form method=post enctype=multipart/form-data><input type=file name=file><input type=submit value=Upload></form>"

def long_running_recognize(args):
    
    client = speech.SpeechClient()
    encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
    config = {
        "enable_word_time_offsets": True,
        "enable_automatic_punctuation": True,
        "sample_rate_hertz": args.sample_rate_hertz,
        "language_code": args.language_code,
        "encoding": encoding,
    }
    strs = args.storage_uri+"/audioFile/"+args.upload_uri
    print("Transcribing {} ...".format(strs))
    audio = {"uri": strs}

    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result()
    subs = []

    for result in response.results:
        # First alternative is the most probable result
        subs = break_sentences(args, subs, result.alternatives[0])

    print("Transcribing finished")
    return subs


def break_sentences(args, subs, alternative):
    firstword = True
    charcount = 0
    idx = len(subs) + 1
    content = ""

    for w in alternative.words:
        if firstword:
            start_hhmmss = time.strftime('%H:%M:%S', time.gmtime(
                w.start_time.seconds))
            try:
                start_ms = int(w.start_time.nanos / 1000000)
            except AttributeError:
                start_ms = int(100000000 / 1000000)

            start = start_hhmmss + "," + str(start_ms)

        charcount += len(w.word)
        content += " " + w.word.strip()

        if ("." in w.word or "!" in w.word or "?" in w.word or
                charcount > args.max_chars or
                ("," in w.word and not firstword)):
            end_hhmmss = time.strftime('%H:%M:%S', time.gmtime(
                w.end_time.seconds))
            try:
                end_ms = int(w.end_time.nanos / 1000000)
            except AttributeError:
                end_ms = int(100000000 / 1000000)

            end = end_hhmmss + "," + str(end_ms)
            subs.append(srt.Subtitle(index=idx,
                        start=srt.srt_timestamp_to_timedelta(start),
                        end=srt.srt_timestamp_to_timedelta(end),
                        content=srt.make_legal_content(content)))
            firstword = True
            idx += 1
            content = ""
            charcount = 0
        else:
            firstword = False
    return subs

def upload_file(args,location,filename):
	storage_client = storage.Client.from_service_account_json("stoked-edition-293116-95e244eb4204.json")
	bucket = storage_client.bucket("spin-5339")
	filenameBuc = "%s/%s" % ('audioFile',filename)
	print(filenameBuc)
	blob = bucket.blob(filenameBuc)
	blob.upload_from_filename(location)
	print("uploaded")

def write_srt(args, subs):
    srt_file = args.out_file + ".srt"
    print("Writing {} subtitles to: {}".format(args.language_code, srt_file))
    f = open(srt_file, 'w')
    f.writelines(srt.compose(subs))
    f.close()
    return 

def write_txt(args, subs):
    txt_file = args.out_file + ".txt"
    print("Writing text to: {}".format(txt_file))
    f = open(txt_file, 'w')
    for s in subs:
        f.write(s.content.strip() + "\n")
    f.close()
    return

if __name__ == "__main__":
    app.run(debug=True)
