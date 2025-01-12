import json
from pydub import AudioSegment
import datetime
import os


def format_time(ms):
    s = ms // 1000
    formatted_time = str(datetime.timedelta(seconds=s))
    hours, minutes, seconds = formatted_time.split(":")
    # Ensure HH:MM:SS format
    formatted_time = f"{hours.zfill(2)}:{minutes.zfill(2)}:{seconds.zfill(2)}"
    return formatted_time


def generate_timecodes_and_audio(dictionary):
    dictionary_name = os.path.splitext(os.path.basename(dictionary))[0]

    combined_audio = AudioSegment.empty()
    combined_timecodes = ""
    cumulative_time_ms = 0
    two_seconds_silence = AudioSegment.silent(duration=2000)

    english_phrases = json.load(open(dictionary, "r"))
    for english_phrase in english_phrases:
        # append the image and audio file for the english phrase
        image_path = f'out/{dictionary_name}/images/{english_phrase}.png'
        audio_path = f'out/{dictionary_name}/audios/{english_phrase}.mp3'

        # create the visual here
        timestamp = format_time(cumulative_time_ms)
        combined_timecodes += f'{timestamp}\t{image_path}\n'

        # then, concatenate the audio
        audio = AudioSegment.from_file(audio_path)
        combined_audio += audio + two_seconds_silence
        # update the cumulative time
        cumulative_time_ms += len(audio) + 2000

        # since timecodes (visual portion) are only in seconds,
        # we want to create silence until the next whole second
        # this ensures the next visual starts at a whole integer,
        # and audios will align properly
        nearest_second_ms = ((cumulative_time_ms // 1000) + 1) * 1000
        silence_needed_ms = nearest_second_ms - cumulative_time_ms

        trailing_silence = AudioSegment.silent(duration=silence_needed_ms)

        combined_audio += trailing_silence
        cumulative_time_ms += silence_needed_ms

        # now, access the foreign languages that have been translated
        foreign_languages = english_phrases[english_phrase]
        for foreign_language in foreign_languages:
            # foreign languages can have multiple translations of an english phrase
            for i in range(len(foreign_languages[foreign_language])):
                image_path = f'out/{dictionary_name}/images/{english_phrase}_{foreign_language}{i}.png'
                audio_path = f'out/{dictionary_name}/audios/{english_phrase}_{foreign_language}{i}.mp3'

                # create the visual here
                timestamp = format_time(cumulative_time_ms)
                combined_timecodes += f'{timestamp}\t{image_path}\n'

                # then, concatenate the audio
                # repeat the audio once
                for i in range(2):
                    audio = AudioSegment.from_file(audio_path)
                    combined_audio += audio + two_seconds_silence
                    # update the cumulative time
                    cumulative_time_ms += len(audio) + 2000
                    # concatenate additional audio for breaking down words, and also update cumulative time
                if foreign_language == 'zh-CN':
                    breakdown = AudioSegment.from_file(audio_path.replace(".mp3", "-breakdown.mp3"))
                    combined_audio += breakdown + two_seconds_silence
                    cumulative_time_ms += len(breakdown) + 2000

                # round this silence as well
                nearest_second_ms = ((cumulative_time_ms // 1000) + 1) * 1000
                silence_needed_ms = nearest_second_ms - cumulative_time_ms

                trailing_silence = AudioSegment.silent(duration=silence_needed_ms)

                combined_audio += trailing_silence
                cumulative_time_ms += silence_needed_ms

    combined_audio.export(f'{dictionary_name}-audio.mp3', format="mp3")
    with open(f'{dictionary_name}-timecodes.txt', 'w') as timecodes_file:
        timecodes_file.write(combined_timecodes)
