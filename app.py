import streamlit as st
import subprocess
import json
import os
import tempfile
import requests

# dark theme
st.set_page_config(
    page_title="C2LL",
    page_icon="🉐",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# custom CSS
st.markdown("""
<style>
    .stApp {
        background-color: #121212;
        color: #FFFFFF;
    }
    /* Hide Streamlit header and toolbar */
    header[data-testid="stHeader"] {
        display: none;
    }
    .stDeployButton {
        display: none;
    }
    #MainMenu {
        visibility: hidden;
    }
    footer {
        visibility: hidden;
    }
    .title {
        font-size: 36px;
        font-weight: bold;
        margin-bottom: 30px;
        text-align: center;
    }
    .success {
        background-color: #2e7d32;
        padding: 15px;
        border-radius: 5px;
    }
    .warning {
        background-color: #ff9800;
        padding: 15px;
        border-radius: 5px;
        color: black;
    }
</style>
""", unsafe_allow_html=True)

# title and description
st.markdown("<div class='title'>C2LL</div>", unsafe_allow_html=True)

# initialize session state for dictionary before tabs
if 'dictionary' not in st.session_state:
    st.session_state.dictionary = {}

# create tabs
tab1, tab2 = st.tabs(["Slideshow Generator", "Local Translator"])

with tab1:
    st.markdown("Upload your translation dictionary JSON file to generate the slideshow.")

    # file uploader
    uploaded_file = st.file_uploader("Choose a JSON file", type="json")

    # checkbox for regeneration option
    regenerate = st.checkbox("Regenerate all outputs (ignore cache)")

    # display sample JSON format
    with st.expander("View sample JSON format"):
        sample_json = """{
    "hello": {
        "zh-CN": [
            {"translation": "你好", "romanization": "Nǐ hǎo"}
        ],
        "hi": [
            {"translation": "नमस्ते", "romanization": "namaste"}
        ]
    },
    "thank you": {
        "zh-CN": [
            {"translation": "谢谢", "romanization": "Xièxiè"}
        ]
    }
}"""
        st.code(sample_json, language="json")

    # process the file when clicked
    if st.button("Generate Slideshow"):
        if uploaded_file is not None:
            try:
                # create a temporary file to save the uploaded content
                with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
                    temp_path = temp_file.name
                    # Write the uploaded content to the temporary file
                    temp_file.write(uploaded_file.getvalue())

                # validate JSON content
                try:
                    with open(temp_path, 'r') as f:
                        json_data = json.load(f)

                    # check if the JSON has the expected structure
                    if not isinstance(json_data, dict) or len(json_data) == 0:
                        st.markdown("<div class='warning'>Invalid JSON structure. Please check the sample format.</div>", unsafe_allow_html=True)
                        os.unlink(temp_path)
                    else:
                        # show progress
                        progress_placeholder = st.empty()
                        progress_bar = st.progress(0)

                        # update progress
                        progress_placeholder.text("Creating output directories...")
                        progress_bar.progress(10)

                        # get the dictionary name from the uploaded file
                        dictionary_name = os.path.splitext(uploaded_file.name)[0]

                        # create directories
                        image_dir = f'out/{dictionary_name}/images'
                        audio_dir = f'out/{dictionary_name}/audios'
                        os.makedirs(image_dir, exist_ok=True)
                        os.makedirs(audio_dir, exist_ok=True)

                        # update progress
                        progress_placeholder.text("Generating translations...")
                        progress_bar.progress(30)

                        # run the generate.py script using direct function call
                        import asyncio
                        from generate import process_dictionary

                        try:
                            asyncio.run(process_dictionary(temp_path, regenerate, dictionary_name))
                            generate_success = True
                            generate_error = None
                        except Exception as e:
                            generate_success = False
                            generate_error = str(e)

                        if not generate_success:
                            st.error(f"Error in generate.py:\n\n{generate_error}")
                            os.unlink(temp_path)
                        else:
                            # update progress
                            progress_placeholder.text("Creating timecodes and audio files...")
                            progress_bar.progress(60)

                            # run slider.py functions
                            from slider import generate_timecodes_and_audio
                            generate_timecodes_and_audio(temp_path, dictionary_name)

                            # update progress
                            progress_placeholder.text("Creating final video...")
                            progress_bar.progress(80)

                            # run the slider shell script
                            video_file = f'out/{dictionary_name}/{dictionary_name}.mp4'
                            timecodes_file = f'{dictionary_name}-timecodes.txt'
                            audio_file = f'{dictionary_name}-audio.mp3'

                            # debug: verify files exist
                            if not os.path.exists(timecodes_file):
                                st.error(f"Timecodes file not found: {timecodes_file}")
                            if not os.path.exists(audio_file):
                                st.error(f"Audio file not found: {audio_file}")

                            slider_cmd = [
                                'sh',
                                'slider.sh',
                                '-i', timecodes_file,
                                '-a', audio_file,
                                '-o', video_file
                            ]

                            slider_process = subprocess.Popen(
                                slider_cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )

                            slider_stdout, slider_stderr = slider_process.communicate()

                            if slider_process.returncode != 0:
                                error_msg = f"Error in slider script:\n\nReturn code: {slider_process.returncode}\n\n"
                                if slider_stderr:
                                    error_msg += f"STDERR:\n{slider_stderr}\n\n"
                                if slider_stdout:
                                    error_msg += f"STDOUT:\n{slider_stdout}"
                                st.error(error_msg)
                            else:
                                # complete progress
                                progress_bar.progress(100)
                                progress_placeholder.text("Process completed successfully!")

                                # success message
                                st.markdown(f"<div class='success'>Video generated successfully: {video_file}</div>", unsafe_allow_html=True)

                                # display video if file exists
                                if os.path.exists(video_file):
                                    st.video(video_file)

                                    with open(video_file, "rb") as file:
                                        btn = st.download_button(
                                            label="Download Video",
                                            data=file,
                                            file_name=f"{dictionary_name}.mp4",
                                            mime="video/mp4"
                                        )

                            # remove temporary file
                            os.unlink(temp_path)

                except json.JSONDecodeError:
                    st.markdown("<div class='warning'>Invalid JSON file. Please upload a properly formatted JSON file.</div>", unsafe_allow_html=True)
                    os.unlink(temp_path)

            except Exception as e:
                st.error(f"An error occurred: {e}")
        else:
            st.markdown("<div class='warning'>Please upload a JSON file first.</div>", unsafe_allow_html=True)

with tab2:
    st.markdown("Local dictionary management and translation using Ollama LLM")

    # dictionary file management
    st.subheader("Dictionary File")

    # set default save path
    if 'dict_save_path' not in st.session_state:
        st.session_state.dict_save_path = "dictionaries/dictionary.json"

    # browse and upload file
    uploaded_dict = st.file_uploader("Browse and load dictionary", type="json", key="dict_browse")
    if uploaded_dict is not None:
        # only load if this is a new file (check by tracking loaded filename)
        if 'loaded_file_name' not in st.session_state or st.session_state.loaded_file_name != uploaded_dict.name:
            try:
                st.session_state.dictionary = json.load(uploaded_dict)
                # update save path to the uploaded filename
                st.session_state.dict_save_path = f"dictionaries/{uploaded_dict.name}"
                st.session_state.loaded_file_name = uploaded_dict.name
                st.success(f"Loaded {len(st.session_state.dictionary)} terms from {uploaded_dict.name}")
            except json.JSONDecodeError:
                st.error("Invalid JSON file")
            except Exception as e:
                st.error(f"Error loading file: {e}")

    # or use direct path
    st.markdown("**Or load from path:**")
    col1, col2 = st.columns([3, 1])
    with col1:
        save_path = st.text_input("File path", value=st.session_state.dict_save_path, key="save_path_input")
        st.session_state.dict_save_path = save_path
    with col2:
        st.write("")  # spacer
        st.write("")  # spacer
        if st.button("Load Path"):
            if os.path.exists(save_path):
                try:
                    with open(save_path, 'r', encoding='utf-8') as f:
                        st.session_state.dictionary = json.load(f)
                    st.success(f"Loaded {len(st.session_state.dictionary)} terms from {save_path}")
                except json.JSONDecodeError:
                    st.error("Invalid JSON file")
                except Exception as e:
                    st.error(f"Error loading file: {e}")
            else:
                st.warning(f"File not found: {save_path}")

    st.divider()

    # add new term
    st.subheader("Add New Term")
    col1, col2 = st.columns(2)
    with col1:
        new_term = st.text_input("English term")
    with col2:
        target_lang = st.selectbox("Target language", ["zh-CN", "vi", "hi", "ja", "ko"])

    if st.button("Translate"):
        if new_term:
            with st.spinner("Translating..."):
                try:
                    url = "http://localhost:11434/api/generate"

                    # languages that need romanization
                    needs_romanization = ["zh-CN", "hi", "ja", "ko"]

                    # language names for better prompts
                    lang_names = {
                        "zh-CN": "Chinese",
                        "vi": "Vietnamese",
                        "hi": "Hindi",
                        "ja": "Japanese",
                        "ko": "Korean"
                    }
                    lang_name = lang_names.get(target_lang, target_lang)

                    if target_lang in needs_romanization:
                        prompt = f"Translate the English word \"{new_term}\" into {lang_name} language. Provide the translation and romanization in this exact format: translation|romanization. Example: 你好|Nǐ hǎo. Give ONLY this format, no explanations, no notes, no additional text."
                    else:
                        # for languages without romanization (vi)
                        prompt = f"Translate the English word \"{new_term}\" into {lang_name} language. Give ONLY the {lang_name} translation, no explanations, no notes, no punctuation, no additional text whatsoever."

                    response = requests.post(url, json={
                        "model": "llama3.2:1b",
                        "prompt": prompt,
                        "stream": False
                    }, timeout=30)

                    if response.status_code == 200:
                        result = response.json()["response"].strip()

                        # parse the result
                        if target_lang in needs_romanization and "|" in result:
                            translation, romanization = result.split("|", 1)
                            translation = translation.strip()
                            romanization = romanization.strip()
                        else:
                            translation = result
                            romanization = None

                        # add to dictionary
                        if new_term not in st.session_state.dictionary:
                            st.session_state.dictionary[new_term] = {}

                        if target_lang not in st.session_state.dictionary[new_term]:
                            st.session_state.dictionary[new_term][target_lang] = []

                        entry = {"translation": translation}
                        if romanization:
                            entry["romanization"] = romanization

                        st.session_state.dictionary[new_term][target_lang].append(entry)

                        # store success message
                        if romanization:
                            st.session_state.last_added = f"{new_term} -> {translation} ({romanization})"
                        else:
                            st.session_state.last_added = f"{new_term} -> {translation}"

                        st.rerun()
                    else:
                        st.error("Ollama server not responding. Make sure it's running with 'ollama serve'")
                except requests.exceptions.Timeout:
                    st.error("Translation timeout. The model might be loading, try again.")
                except Exception as e:
                    st.error(f"Translation error: {e}")
        else:
            st.warning("Please enter a term to translate")

    # show last added message
    if 'last_added' in st.session_state and st.session_state.last_added:
        st.success(f"Added: {st.session_state.last_added}")
        st.session_state.last_added = None

    st.divider()

    # manual entry
    with st.expander("Or add manually"):
        col1, col2 = st.columns(2)
        with col1:
            manual_term = st.text_input("English term", key="manual_term")
        with col2:
            manual_lang = st.selectbox("Language", ["zh-CN", "vi", "hi", "ja", "ko"], key="manual_lang")

        col1, col2, col3 = st.columns(3)
        with col1:
            manual_translation = st.text_input("Translation")
        with col2:
            manual_romanization = st.text_input("Romanization (optional)")
        with col3:
            manual_note = st.text_input("Note (optional)")

        if st.button("Add Manually"):
            if manual_term and manual_translation:
                if manual_term not in st.session_state.dictionary:
                    st.session_state.dictionary[manual_term] = {}

                if manual_lang not in st.session_state.dictionary[manual_term]:
                    st.session_state.dictionary[manual_term][manual_lang] = []

                entry = {"translation": manual_translation}
                if manual_romanization:
                    entry["romanization"] = manual_romanization
                if manual_note:
                    entry["note"] = manual_note

                st.session_state.dictionary[manual_term][manual_lang].append(entry)

                # store success message
                st.session_state.last_added = f"{manual_term} -> {manual_translation} (manual)"

                st.rerun()
            else:
                st.warning("Please provide at least term and translation")

    st.divider()

    # display and manage current dictionary
    st.subheader("Current Dictionary")

    if st.session_state.dictionary:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"Total terms: {len(st.session_state.dictionary)}")
        with col2:
            if st.button("Save to File"):
                try:
                    # create directory if it doesn't exist
                    os.makedirs(os.path.dirname(st.session_state.dict_save_path), exist_ok=True)

                    with open(st.session_state.dict_save_path, 'w', encoding='utf-8') as f:
                        json.dump(st.session_state.dictionary, f, indent=2, ensure_ascii=False)
                    st.success(f"Saved to {st.session_state.dict_save_path}")
                except Exception as e:
                    st.error(f"Error saving: {e}")

        for term, translations in st.session_state.dictionary.items():
            with st.expander(f"{term}"):
                for lang, entries in translations.items():
                    st.write(f"**{lang}:**")
                    for idx, entry in enumerate(entries):
                        romanization = entry.get('romanization', '')

                        # build display string
                        display_parts = [entry['translation']]
                        if romanization:
                            display_parts.append(f"({romanization})")

                        st.write(f"  - {' '.join(display_parts)}")

                        # editable note field with remove button
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            current_note = entry.get('note', '')
                            new_note = st.text_input(
                                "Note",
                                value=current_note,
                                key=f"note_{term}_{lang}_{idx}",
                                placeholder="Add note (e.g., formal, informal, slang)"
                            )
                            # update note if changed
                            if new_note != current_note:
                                if new_note:
                                    st.session_state.dictionary[term][lang][idx]['note'] = new_note
                                elif 'note' in st.session_state.dictionary[term][lang][idx]:
                                    del st.session_state.dictionary[term][lang][idx]['note']
                        with col2:
                            st.write("")  # spacer
                            st.write("")  # spacer
                            if st.button("Remove", key=f"remove_{term}_{lang}_{idx}"):
                                st.session_state.dictionary[term][lang].pop(idx)
                                if not st.session_state.dictionary[term][lang]:
                                    del st.session_state.dictionary[term][lang]
                                if not st.session_state.dictionary[term]:
                                    del st.session_state.dictionary[term]
                                st.success(f"Removed {term}")
                                st.rerun()

        if st.button("Clear All"):
            if st.session_state.dictionary:
                st.session_state.dictionary = {}
                st.success("Dictionary cleared!")
                st.rerun()
            else:
                st.info("Dictionary is already empty")
    else:
        st.info("No terms in dictionary. Add some terms above!")
