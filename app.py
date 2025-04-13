import streamlit as st
import subprocess
import json
import os
import tempfile

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
    .stButton button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        padding: 10px 24px;
        border: none;
    }
    .stButton button:hover {
        background-color: #45a049;
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
                    
                    # get the dictionary name
                    dictionary_name = os.path.splitext(os.path.basename(temp_path))[0]
                    
                    # create directories
                    image_dir = f'out/{dictionary_name}/images'
                    audio_dir = f'out/{dictionary_name}/audios'
                    os.makedirs(image_dir, exist_ok=True)
                    os.makedirs(audio_dir, exist_ok=True)
                    
                    # update progress
                    progress_placeholder.text("Generating translations...")
                    progress_bar.progress(30)
                    
                    # run the generate.py script
                    cmd = ["python", "generate.py", temp_path]
                    if regenerate:
                        cmd.append("--regenerate")
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    stdout, stderr = process.communicate()
                    
                    if process.returncode != 0:
                        st.markdown(f"<div class='warning'>Error: {stderr}</div>", unsafe_allow_html=True)
                        os.unlink(temp_path)
                    else:
                        # update progress
                        progress_placeholder.text("Creating timecodes and audio files...")
                        progress_bar.progress(60)
                        
                        # run slider.py functions
                        from slider import generate_timecodes_and_audio
                        generate_timecodes_and_audio(temp_path)
                        
                        # update progress
                        progress_placeholder.text("Creating final video...")
                        progress_bar.progress(80)
                        
                        # run the slider shell script
                        slider_cmd = [
                            'sh',
                            'slider.sh',
                            '-i', f'{dictionary_name}-timecodes.txt',
                            '-a', f'{dictionary_name}-audio.mp3',
                            '-o', f'{dictionary_name}.mp4'
                        ]
                        
                        slider_process = subprocess.Popen(
                            slider_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        
                        slider_stdout, slider_stderr = slider_process.communicate()
                        
                        if slider_process.returncode != 0:
                            st.markdown(f"<div class='warning'>Error in slider script: {slider_stderr}</div>", unsafe_allow_html=True)
                        else:
                            # complete progress
                            progress_bar.progress(100)
                            progress_placeholder.text("Process completed successfully!")
                            
                            # success message
                            st.markdown(f"<div class='success'>✅ Video generated successfully: {dictionary_name}.mp4</div>", unsafe_allow_html=True)
                            
                            # provide download link if file exists
                            video_file = f"{dictionary_name}.mp4"
                            if os.path.exists(video_file):
                                with open(video_file, "rb") as file:
                                    btn = st.download_button(
                                        label="Download Video",
                                        data=file,
                                        file_name=video_file,
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
