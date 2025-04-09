import json
import re
import time
import os
import streamlit as st
import google.generativeai as genai
import pandas as pd
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env

api_key = os.getenv("API_KEY")

# Set page configuration with wider layout
st.set_page_config(
    page_title="DubFlix Hinglish Translator",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS for better spacing and alignment
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1rem;
    }
    div.stButton > button {
        width: 100%;
    }
    .st-emotion-cache-16idsys p {
        font-size: 1.05rem;
    }
    .comparison-header {
        text-align: center;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Centered title with emoji and subtitle
st.markdown("<h1 style='text-align: center;'>🔄 DubFlix</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; margin-bottom: 2rem;'>English to Hinglish Translator</h3>", unsafe_allow_html=True)

# Simplified sidebar with just stats
with st.sidebar:
    st.markdown("### 📊 Stats")
    if 'translation_time' in st.session_state:
        st.metric("Last Translation Time", f"{st.session_state.translation_time:.2f}s")
    
    st.markdown("---")
    st.caption("DubFlix © 2025")

# Configure the Gemini API
@st.cache_resource
def get_model():
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash')

def process_json(data):
    model = get_model()
    
    # Format all texts as a single prompt for Gemini
    texts_to_translate = [item["text"] for item in data]
    texts_with_indices = [f"[{i+1}] {text}" for i, text in enumerate(texts_to_translate)]
    
    prompt = """
    Translate the following English texts to natural, conversational Hinglish (Hindi-English mix).
    
    Guidelines:
    1. Keep translations natural sounding, not robotic or literal
    2. Convert numbers or numerical values or currencies to words in 'hindi'. 
    3. Maintain English words that are commonly used in Hinglish conversation
    4. Consider context between sentences for a natural flow
    5. The output should feel like a casual conversation between Indians
    
    For each text below, provide the Hinglish translation. Maintain the numbering format exactly as [1], [2], etc.
    
    {0}
    
    Return ONLY the translated texts with their corresponding numbers in this exact format:
    [1] <Hinglish translation>
    [2] <Hinglish translation>
    ...
    
    Do not include any explanations, only the numbered translations.
    """
    
    prompt = prompt.format('\n\n'.join(texts_with_indices))
    
    with st.spinner("🔄 Translating with Gemini AI..."):
        progress_bar = st.progress(0)
        start_time = time.time()
        response = model.generate_content(prompt)
        translated_text = response.text.strip()
        end_time = time.time()
        translation_time = end_time - start_time
        st.session_state.translation_time = translation_time
        progress_bar.progress(100)
    
    st.success(f"✅ Translation completed in {translation_time:.2f} seconds!")
    
    # Parse the response to extract individual translations
    lines = translated_text.split('\n')
    translations = []
    current_index = None
    current_text = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts a new translation
        index_match = re.match(r'^\[(\d+)\](.*)', line)
        if index_match:
            # If we have a previous translation, save it
            if current_index is not None:
                translations.append((current_index, current_text.strip()))
            
            # Start a new translation
            current_index = int(index_match.group(1))
            current_text = index_match.group(2).strip()
        else:
            # Continue the current translation
            current_text += " " + line
    
    # Add the last translation
    if current_index is not None:
        translations.append((current_index, current_text.strip()))
    
    # Sort translations by index
    translations.sort(key=lambda x: x[0])
    
    # Create output data
    output_data = []
    for idx, trans_text in translations:
        if 1 <= idx <= len(data):
            output_data.append({"text": trans_text})
    
    # If we're missing any translations, fill with placeholders
    if len(output_data) < len(data):
        for i in range(len(output_data), len(data)):
            output_data.append({"text": f"[Translation missing for: {data[i]['text']}]"})
    
    return output_data

# Create tabs with better styling
tabs = st.tabs(["🔄 Translate", "📊 Results", "ℹ️ About"])

with tabs[0]:
    st.markdown("### Upload your content")
    
    # File uploader with clearer instructions
    upload_col1, upload_col2 = st.columns([3, 1])
    
    with upload_col1:
        uploaded_file = st.file_uploader(
            "Upload JSON file containing English texts", 
            type=["json"],
            help="JSON should contain an array of objects with 'text' property"
        )
    
    with upload_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if uploaded_file:
            if st.button("🚀 Translate", type="primary", use_container_width=True):
                try:
                    input_data = json.load(uploaded_file)
                    st.session_state.input_data = input_data
                    
                    with st.spinner("Processing..."):
                        output_data = process_json(input_data)
                        st.session_state.output_data = output_data
                        st.session_state.tab_index = 1  # Switch to results tab
                        st.rerun()
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Display input data preview if file is uploaded
    if uploaded_file:
        try:
            if 'input_data' not in st.session_state:
                st.session_state.input_data = json.load(uploaded_file)
            
            st.markdown("### 📝 Preview Input Data")
            
            # Create a more visually appealing dataframe
            input_df = pd.DataFrame([{"Index": i+1, "English Text": item["text"]} 
                                   for i, item in enumerate(st.session_state.input_data)])
            
            st.dataframe(
                input_df,
                use_container_width=True,
                height=400,
                column_config={
                    "Index": st.column_config.NumberColumn(
                        "№",
                        width="small",
                    ),
                    "English Text": st.column_config.TextColumn(
                        "English Text",
                        width="large",
                    )
                }
            )
        except Exception as e:
            st.error(f"Invalid JSON format: {str(e)}")
    else:
        # Sample JSON when no file is uploaded
        st.markdown("### Sample JSON Format")
        sample = [
            {"text": "Hello, how are you doing today?"}, 
            {"text": "What's your name? I'm John."},
            {"text": "The price is $50 for this product."}
        ]
        st.code(json.dumps(sample, indent=2))

with tabs[1]:
    if 'output_data' in st.session_state and st.session_state.output_data:
        st.markdown("### 🎯 Translation Results")
        
        # Display side-by-side comparison
        if 'input_data' in st.session_state:
            comparison_data = []
            for i, (inp, out) in enumerate(zip(st.session_state.input_data, st.session_state.output_data)):
                comparison_data.append({
                    "№": i+1,
                    "English": inp["text"],
                    "Hinglish": out["text"]
                })
            
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(
                comparison_df, 
                use_container_width=True, 
                height=400,
                column_config={
                    "№": st.column_config.NumberColumn(
                        "№",
                        width="small",
                    ),
                    "English": st.column_config.TextColumn(
                        "English Original",
                        width="medium",
                    ),
                    "Hinglish": st.column_config.TextColumn(
                        "Hinglish Translation",
                        width="medium",
                    )
                }
            )
            
            # Download buttons in columns for better alignment
            dl_col1, dl_col2 = st.columns(2)
            
            with dl_col1:
                output_json = json.dumps(st.session_state.output_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="💾 Download Translated JSON",
                    data=output_json,
                    file_name="hinglish_output.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with dl_col2:
                # Export as CSV option
                csv_data = comparison_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📊 Export as CSV",
                    data=csv_data,
                    file_name="hinglish_translations.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    else:
        st.info("👈 Upload a file and translate it first to see results here")

with tabs[2]:
    st.markdown("### About DubFlix Hinglish Translator")
    
    about_col1, about_col2 = st.columns([2, 1])
    
    with about_col1:
        st.markdown("""
        This application uses Google's Gemini AI model to translate English text to natural-sounding Hinglish 
        (a mix of Hindi and English commonly spoken in India).
        
        #### Why Hinglish?
        Hinglish is widely spoken across India and provides a more natural and relatable experience for Indian audiences 
        compared to pure Hindi or English.
        
        #### Translation Features:
        - Natural and conversational translations
        - Maintains appropriate mix of Hindi and English words
        - Converts numbers and currencies to Hindi words
        - Preserves context between sentences
        """)
    
    with about_col2:
        st.markdown("""
        #### How to use:
        1. Upload a JSON file with texts
        2. Click the "Translate" button
        3. Download results in JSON or CSV format
        
        #### Input Format:
        ```json
        [
          {"text": "Text to translate"},
          {"text": "Another text"}
        ]
        ```
        
        #### Output Format:
        ```json
        [
          {"text": "Translated text"},
          {"text": "Another translation"}
        ]
        ```
        """)