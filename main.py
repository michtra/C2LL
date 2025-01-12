# main.py
import argparse
import subprocess
import os

from slider import generate_timecodes_and_audio


def run_generate(file, regenerate):
    """
    Forward the arguments to generate.py and run it.
    """
    cmd = ["python", "generate.py", file]
    if regenerate:
        cmd.append("--regenerate")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(result.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Driver file to generate images/audio files and then calls the slider script.")
    parser.add_argument("file", help="Path to dictionary json.")
    parser.add_argument("--regenerate", action="store_true", help="Regenerate all outputs and ignore cache.")
    args = parser.parse_args()

    dictionary_name = os.path.splitext(os.path.basename(args.file))[0]
    # make the image and audio cache directories if they don't exist
    image_dir = f'out/{dictionary_name}/images'
    audio_dir = f'out/{dictionary_name}/audios'

    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    # now run generate.py
    run_generate(args.file, args.regenerate)

    # generate timecodes and audio files using slider.py
    generate_timecodes_and_audio(args.file)

    # run the slider shell script
    dictionary_name = os.path.splitext(os.path.basename(args.file))[0]
    slider = [
        'sh',
        'slider.sh',
        '-i', f'{dictionary_name}-timecodes.txt',
        '-a', f'{dictionary_name}-audio.mp3',
        '-o', f'{dictionary_name}.mp4'
    ]
    subprocess.run(slider)


if __name__ == "__main__":
    main()
