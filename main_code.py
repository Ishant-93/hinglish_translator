import json
import os
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env

api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)

# Select the Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')

# Hardcoded input and output file paths
INPUT_FILE = 'input.json'
OUTPUT_FILE = 'output.json'

def process_entire_json(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Found {len(data)} entries to translate.")

    # Format all texts as a single prompt for Gemini
    texts_to_translate = [item["text"] for item in data]
    texts_with_indices = [f"[{i+1}] {text}" for i, text in enumerate(texts_to_translate)]

    # Using triple quotes with regular string, then format it to avoid f-string backslash issues
    prompt = """
    Translate the following English texts to natural, conversational Hinglish (Hindi-English mix).

    Guidelines:
    1. Keep translations natural sounding, not robotic or literal
    2. important : Convert numbers or numerical values to words in 'hindi' words.
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

    # Format the prompt after definition to avoid f-string backslash issues
    prompt = prompt.format('\n\n'.join(texts_with_indices))

    # Get translation from Gemini
    print("Sending request to Gemini API...")
    start_time = time.time()
    response = model.generate_content(prompt)
    translated_text = response.text.strip()
    end_time = time.time()

    print(f"Got response from API in {end_time - start_time:.2f} seconds.")

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

    # Verify we got all translations
    if len(translations) != len(data):
        print(f"Warning: Expected {len(data)} translations but got {len(translations)}.")

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

    # Write output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully processed translations and saved to {output_file}")
    return output_data

def create_sample_input():
    """
    Create a sample input file with hardcoded entries
    """
    sample_texts = [
        "Nothing, you just have to go to DubFlix.in, take a video of yours, upload it, and that's it.",
        "Choose the target language.",
        "Or just submit the way and in two to three minutes you get your dubbed videos.",
        "It costs only $6 and Rs.50 for a 5 minute video.",
    ]

    sample_data = [{"text": text} for text in sample_texts]

    with open(INPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)

    print(f"Created sample input file with {len(sample_texts)} entries.")
    return INPUT_FILE

def main():
    """
    Main function to run the translator
    """
    print("DubFlix English to Hinglish Translator (Batch Processing)")
    print("------------------------------------------------------")

    # Check if input file exists or create it
    if not os.path.exists(INPUT_FILE):
        print(f"Input file {INPUT_FILE} not found. Creating sample file...")
        create_sample_input()
    else:
        print(f"Using existing input file: {INPUT_FILE}")

    print(f"\nProcessing {INPUT_FILE} to {OUTPUT_FILE}...")

    try:
        # Check if API key is set
        if not api_key:
            print("Error: Google API key not found.")
            return

        start_time = time.time()
        process_entire_json(INPUT_FILE, OUTPUT_FILE)
        end_time = time.time()

        print(f"\nProcessing completed in {end_time - start_time:.2f} seconds.")

    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    main()