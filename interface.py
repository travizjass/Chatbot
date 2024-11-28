import os
import base64
from flask import Flask, request, render_template, send_file
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Get the OpenAI API key from the environment variable
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the .env file")

client = OpenAI(api_key=api_key)

def process_audio(audio_file, prompt):
    # Save the uploaded file temporarily
    temp_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_audio.mp3')
    audio_file.save(temp_audio_path)

    # Read the audio file and convert it to a base64 encoded string
    with open(temp_audio_path, 'rb') as f:
        wav_data = f.read()
    encoded_string = base64.b64encode(wav_data).decode('utf-8')

    # Call the OpenAI API
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-audio-preview",
            modalities=["text", "audio"],
            audio={"voice": "alloy", "format": "mp3"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": encoded_string,
                                "format": "mp3"
                            }
                        }
                    ]
                },
            ]
        )
    except Exception as e:
        os.remove(temp_audio_path)
        return None, str(e)

    # Decode the audio data and save it to a file
    wav_bytes = base64.b64decode(completion.choices[0].message.audio.data)
    output_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'output_audio.wav')
    with open(output_audio_path, 'wb') as f:
        f.write(wav_bytes)

    # Remove the temporary audio file
    os.remove(temp_audio_path)

    return output_audio_path, None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get the uploaded file and prompt
        audio_file = request.files.get('audio')
        prompt = request.form.get('prompt')

        if not audio_file or not prompt:
            return "Both audio file and prompt are required.", 400

        output_audio_path, error = process_audio(audio_file, prompt)

        if error:
            return f"Error: {error}", 500

        # Return the generated audio file
        return send_file(output_audio_path, as_attachment=True, download_name='output_audio.wav')

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)