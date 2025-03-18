# YouTube Trending Videos & Content Suggestions

This Flask application fetches trending YouTube videos and uses Google's Gemini AI to generate content suggestions based on the video topics.

## Features

- Display current trending YouTube videos
- Show video thumbnails, titles, and view counts
- Generate AI-powered content suggestions for each video
- Modern, responsive UI using Tailwind CSS

## Prerequisites

- Python 3.7 or higher
- YouTube Data API key
- Google Gemini API key

## Setup

1. Clone this repository
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add your API keys:
   ```
   YOUTUBE_API_KEY=your_youtube_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

4. To get a YouTube API key:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the YouTube Data API v3
   - Create credentials (API key)

5. To get a Gemini API key:
   - Go to the [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create an API key

## Running the Application

1. Start the Flask server:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

1. The homepage displays current trending YouTube videos
2. Click "Get Content Suggestions" on any video to generate AI-powered content ideas
3. The suggestions will appear below the video card

## Note

Make sure to keep your API keys secure and never commit them to version control. 