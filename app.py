import os
import csv
import sys
import json
import pandas as pd
from flask import Flask, render_template, request, send_file, redirect

app = Flask(__name__)

MAPPER = {
    'angry': 0,
    'sad': 1,
    'happy': 2,
    'calm': 3
}


def get_dataset_path():
    """Get the path of the dataset folder"""
    with open('config.json', 'r') as file:
        config = json.load(file)
    dataset_path = config.get('dataset_path', None)
    if dataset_path is None:
        raise Exception("Config file is corrupted")
    if not os.path.exists(dataset_path):
        raise Exception('Folder {dataset_path} does not exist')
    return dataset_path

def get_transcript_path():
    """Get the path of the dataset folder"""
    with open('config.json', 'r') as file:
        config = json.load(file)
    transcript_path = config.get('transcript_path', None)
    if transcript_path is None:
        raise Exception("Config file is corrupted")
    if not os.path.exists(transcript_path):
        raise Exception('File {transcr_path} does not exist')
    return transcript_path


def get_index():
    """Get the index of the current video to start annotation with"""
    if os.path.exists('cache/state.json'):
        with open('cache/state.json', 'r') as file:
            state = json.load(file)
        video_index = state.get('index', None)
        if video_index is None:
            raise Exception("State file is corrupted")
        return video_index
    else:
        with open('cache/state.json', 'w') as file:
            json.dump({"index": 0}, file)
        return 0


def save_index(value):
    with open('cache/state.json', 'w') as file:
        json.dump({"index": value}, file)


# def get_list_videos():
#     dataset_path = get_dataset_path()
#     videos = os.scandir(dataset_path)
#     videos = list(videos)
#     return videos
def get_list_videos(names):
    dataset_path = get_dataset_path()
    videos = [
        {'path': os.path.join(dataset_path, f'{name}.mp4'), 'name': name} 
        for name in names]
    return videos

def get_default_transcription():
    transcription_path = get_transcript_path()
    df = pd.read_csv(transcription_path)
    my_dict = dict(zip(df['name'], df['transcription']))
    return my_dict

def read_df():
    try:
        df = pd.read_csv('cache/transcriptions.csv')
    except FileNotFoundError:
        df = pd.DataFrame(columns=['Name', 'Transcription', 'Comment'])
    return df

# Change
def save_choice(name, transcription, comment):
    # Dataframe
    df = read_df()

    # Check if the name already exists in the data
    mask = df['Name'] == name

    # Update or add the record
    if mask.any():
        df.loc[mask, ['Transcription', 'Comment']] = transcription, comment
    else:
        df = df.append({
            'Name': name, 
            'Transcription': transcription, 
            'Comment': comment}, ignore_index=True)

    # Write the updated data back to the CSV file
    df.to_csv('cache/transcriptions.csv', index=False)

current_video_index = get_index()
default_transcript = get_default_transcription()
videos = get_list_videos(default_transcript.keys())


if current_video_index > len(videos):
    raise Exception('Corrupted state file')

def get_suggested_transcript(name):
    suggested_transcript = default_transcript[name]
    if not isinstance(suggested_transcript, str):
        suggested_transcript = ''
    else:
        suggested_transcript = suggested_transcript.replace(u'\xa0', u' ')
        suggested_transcript = suggested_transcript.replace('  ', ' ')
    return suggested_transcript

def get_transcription_comments(name):
    df = read_df()
    mask = df['Name'] == name

    if name in df['Name'].values:
        transcript = df.loc[mask, 'Transcription'].values[0]
        comment = df.loc[mask, 'Comment'].values[0]
        return transcript, comment
    else:
        transcript = get_suggested_transcript(name)
        return transcript, ''



@app.route('/', methods=['GET', 'POST'])
def index():
    global current_video_index

    print(current_video_index)

    name = videos[current_video_index]['name']
    suggested_transcript = get_suggested_transcript(name)
    correct_transcript, comment = get_transcription_comments(name)

    idx = f'{current_video_index + 1}'
    if current_video_index == len(videos):
        # All videos have been shown, redirect to thank you page
        return redirect('/done')

    if request.method == 'POST':
        correct_transcript = request.form['correct_transcript']
        comments = request.form['comments']

        save_index(current_video_index)

        # Write choices to a CSV file
        save_choice(name, correct_transcript, comments)

        # print(request.args['action'])

        if request.form['navigation'] == 'Next':
            # Move to the next video
            current_video_index = current_video_index + 1
            idx = f'{current_video_index + 1}'
            # Save and go next
        elif request.form['navigation'] == 'Previous':
            # Move to the previous video
            if current_video_index>0:
                current_video_index = current_video_index - 1
                idx = f'{current_video_index + 1}'
            # Save and go to back

        # Done with annotation
        if current_video_index == len(videos):
            # All videos have been shown, redirect to thank you page
            return redirect('/done')
        
    name = videos[current_video_index]['name']
    suggested_transcript = get_suggested_transcript(name)
    correct_transcript, comment = get_transcription_comments(name)

    return render_template(
        'index.html',
        video=videos[current_video_index]['path'],
        video_name=name,
        index=idx,
        suggested_transcript=suggested_transcript,
        correct_transcript=correct_transcript,
        comment=comment)


@app.route('/done')
def done():
    return render_template('done.html')


@app.route('/video/<path:video_path>')
def serve_video(video_path):
    return send_file(video_path, mimetype='video/mp4')


if __name__ == '__main__':
    app.run(debug=True)
