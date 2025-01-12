# generate.py
import argparse
import asyncio
import json
import os
from gtts import gTTS
import breakdown.zh as zh


def create_drawtext_string(text, fontfile, fontsize, x, y):
    """
    Creates a drawtext argument for ffmpeg.
    :param text: the text
    :param fontfile: the font file to use
    :param fontsize: the font size
    :param x: the x position of the text on the image
    :param y: the y position of the text on the image
    :return: the drawtext argument
    """
    # not sure how to sanitize the text properly
    # just prevent the illegal characters
    for c in ":{'":
        if c in text:
            raise Exception(f"Illegal character {c} detected in {text}")

    return (f"drawtext=text='{text}':"
            f"fontfile=assets/fonts/{fontfile}:"
            f"fontcolor=white:"
            f"fontsize={fontsize}:"
            f"x={x}:"
            f"y={y}")


async def create_image(translation_object, language, output_file):
    """
    Create an image from a translation object.
    :param translation_object: has translation and possible romanization/notes
    :param language: the language of the object, to be used in the header
    :param output_file: output file name
    """
    text = []
    fontfile = 'NotoSansCJK-Regular.ttc'
    if language == "hi":
        fontfile = 'NotoSansDevanagari-Regular.ttf'
    # visual for the translation text
    # can also be used for english, which will have no translation object
    if not isinstance(translation_object, dict):
        text.append(create_drawtext_string(translation_object, fontfile, '100', '(w-text_w)/2', '(h-text_h)/2'))
    else:
        text.append(create_drawtext_string(translation_object['translation'], fontfile, '100', '(w-text_w)/2', '(h-text_h)/2'))

        # visual for the language header
        text.append(create_drawtext_string(language, fontfile, '60', '10', '10'))

        # add any subheading visuals. let's create a flag for proper spacing
        previous_subheading = False
        if "romanization" in translation_object:
            text.append(
                create_drawtext_string(translation_object['romanization'], fontfile, '60', '(w-text_w)/2', '(h-text_h)/2 + 120'))
            previous_subheading = True
        if "note" in translation_object:
            text.append(create_drawtext_string(translation_object['note'], fontfile, '60', '(w-text_w)/2',
                                               f'(h-text_h)/2 + {200 if previous_subheading else 120}'))

    drawtext = ', '.join(text)

    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "color=c=black:s=1920x1080:d=5",
        "-vf", drawtext,
        "-t", "5",
        "-frames:v", "1",
        output_file,
        "-y"  # yes option
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    await process.communicate()


async def create_audio(translation_object, language, output_file):
    """
    Create an audio from a translation object.
    :param translation_object: has translation
    :param language: the language of the object, to be used for the tts
    :param output_file: output file name
    """
    await asyncio.to_thread(generate_tts, translation_object, language, output_file)


def generate_tts(translation_object, language, output_file):
    """
    Generates and saves an audio from a translation object.
    Helper method for asynchronous calls.
    :param translation_object: has translation
    :param language: the language of the object, to be used for the tts
    :param output_file: output file name
    """
    if isinstance(translation_object, dict):  # foreign language
        tts = gTTS(text=translation_object['translation'], lang=language)
        tts.save(output_file)
    else:  # english
        tts = gTTS(text=translation_object, lang=language)
        tts.save(output_file)
    if language == "zh-CN":
        # break down all chinese phrases into individual words
        breakdown = zh.process_pinyin_phrase(translation_object['romanization'])
        # we will tts individual words' spellings and tones
        to_tts = ""
        for phrase in breakdown:
            to_tts += f'{phrase["letters"]}, tone {phrase["tone"]}.'
        tts = gTTS(text=to_tts, lang='en')
        tts.save(output_file.replace(".mp3", "-breakdown.mp3"))


async def process_dictionary(file, regenerate):
    """
    Processes the dictionary of translations.

    :param file: the JSON dictionary
    :param regenerate: argument to regenerate files
    """

    '''
    JSON Dictionary Example:
    
    "english_phrase": {
        "foreign_language": [
          {"translation": "你好", "romanization": "Nǐ hǎo"}
        ],
    }
    '''
    async_tasks = []
    '''
    For the cache option,
    if the regenerate flag is true then regenerate.
    Otherwise, check if this translation has already been generated.
    We'll just check if the image has been generated.
    '''

    '''
    File naming explained:
    Dictionary name is the file name without the extension.
    Translations are numbered 1 to n.
    Output image/audio path: out/{dictionary name}/{english phrase}_{foreign language}{number}{file extension}
    English phrases 
    '''

    dictionary_name = os.path.splitext(os.path.basename(file))[0]
    english_phrases = json.load(open(file, "r"))
    for english_phrase in english_phrases:
        # create an image and audio file for the english phrase
        image_path = f'out/{dictionary_name}/images/{english_phrase}.png'
        if regenerate or not os.path.exists(image_path):
            async_tasks.append(create_image(english_phrase, 'en', image_path))
        audio_path = f'out/{dictionary_name}/audios/{english_phrase}.mp3'
        if regenerate or not os.path.exists(audio_path):
            async_tasks.append(create_audio(english_phrase, 'en', audio_path))

        # access the foreign language translations that are available
        foreign_languages = english_phrases[english_phrase]
        for foreign_language in foreign_languages:
            # foreign languages can have multiple translations of an english phrase
            for i in range(len(foreign_languages[foreign_language])):
                translation = foreign_languages[foreign_language][i]
                image_path = f'out/{dictionary_name}/images/{english_phrase}_{foreign_language}{i}.png'
                if regenerate or not os.path.exists(image_path):
                    async_tasks.append(create_image(translation, foreign_language, image_path))
                audio_path = f'out/{dictionary_name}/audios/{english_phrase}_{foreign_language}{i}.mp3'
                if regenerate or not os.path.exists(audio_path):
                    async_tasks.append(create_audio(translation, foreign_language, audio_path))

    await asyncio.gather(*async_tasks)


async def main():
    parser = argparse.ArgumentParser(description="Run ffmpeg commands from JSON.")
    parser.add_argument("file", help="Path to dictionary json.")
    parser.add_argument("--regenerate", action="store_true", help="Regenerate all outputs and ignore cache.")
    args = parser.parse_args()

    await process_dictionary(args.file, args.regenerate)


if __name__ == "__main__":
    asyncio.run(main())
