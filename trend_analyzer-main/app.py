from flask import Flask, render_template, jsonify, request
from googleapiclient.discovery import build
import google.generativeai as genai
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import isodate  # Add this import for parsing YouTube durations

# Load environment variables
load_dotenv()

# Validate API keys
youtube_api_key = os.getenv('YOUTUBE_API_KEY')
gemini_api_key = os.getenv('GEMINI_API_KEY')

if not youtube_api_key:
    print("Warning: YouTube API key is not set!")
if not gemini_api_key:
    print("Warning: Gemini API key is not set!")

app = Flask(__name__)

# Configure YouTube API
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

# Configure Gemini API
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# Dictionary of countries with their codes
COUNTRIES = {
    'United States': 'US',
    'United Kingdom': 'GB',
    'India': 'IN',
    'Bangladesh': 'BD',
    'Canada': 'CA',
    'Australia': 'AU',
    'Japan': 'JP',
    'South Korea': 'KR',
    'Brazil': 'BR',
    'France': 'FR',
    'Germany': 'DE',
    'Spain': 'ES',
    'Italy': 'IT',
    'Russia': 'RU',
    'Mexico': 'MX',
    'Indonesia': 'ID'
}

# Store chat history (in memory - for demo purposes)
chat_history = {}

def calculate_engagement_score(video):
    """Calculate an engagement score based on multiple metrics"""
    try:
        views = int(video['statistics'].get('viewCount', 0))
        likes = int(video['statistics'].get('likeCount', 0))
        comments = int(video['statistics'].get('commentCount', 0))
        
        # Calculate engagement ratios
        like_ratio = (likes / views) if views > 0 else 0
        comment_ratio = (comments / views) if views > 0 else 0
        
        # Weighted score (can be adjusted)
        engagement_score = (
            0.4 * views +                    # Base views weight
            0.3 * (like_ratio * 10000) +     # Normalized like ratio
            0.3 * (comment_ratio * 10000)    # Normalized comment ratio
        )
        
        return engagement_score
    except (KeyError, ValueError, ZeroDivisionError):
        return 0

def get_trending_videos(region_code='US'):
    try:
        print(f"Fetching trending videos for region: {region_code}")
        if not youtube_api_key:
            print("Error: YouTube API key is not set")
            return []
        
        print("Step 1: Fetching video IDs...")
        # First get popular videos from the region with multiple pages
        video_ids = []
        next_page_token = None
        
        # Fetch multiple pages to get more videos
        for page in range(3):  # Fetch 3 pages of results
            print(f"Fetching page {page + 1} of video IDs...")
            request = youtube.search().list(
                part='id',
                type='video',
                regionCode=region_code,
                order='viewCount',  # Sort by view count
                maxResults=50,  # Maximum allowed per request
                pageToken=next_page_token,
                fields='nextPageToken,items(id(videoId))'
            )
            search_response = request.execute()
            
            # Collect video IDs
            new_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            video_ids.extend(new_ids)
            print(f"Found {len(new_ids)} video IDs on page {page + 1}")
            
            # Get next page token
            next_page_token = search_response.get('nextPageToken')
            if not next_page_token:
                break
        
        print(f"Total video IDs collected: {len(video_ids)}")
        
        if not video_ids:
            print("No videos found in the region")
            return []
        
        print("Step 2: Fetching video details...")
        # Process videos in batches of 50 (API limit)
        all_videos = []
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i + 50]
            print(f"Processing batch of {len(batch_ids)} videos...")
            
            videos_request = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(batch_ids)
            )
            videos_response = videos_request.execute()
            
            for item in videos_response['items']:
                try:
                    view_count = int(item['statistics'].get('viewCount', 0))
                    duration_seconds = parse_duration(item['contentDetails']['duration'])
                    
                    print(f"Video {item['id']}: Views={view_count}, Duration={duration_seconds}s")
                    
                    # Only include videos with significant views and longer than 5 minutes
                    if view_count > 10000 and duration_seconds >= 300:
                        video = {
                            'title': item['snippet']['title'],
                            'description': item['snippet']['description'],
                            'thumbnail': item['snippet']['thumbnails']['high']['url'],
                            'views': view_count,
                            'likes': item['statistics'].get('likeCount', '0'),
                            'comments': item['statistics'].get('commentCount', '0'),
                            'video_id': item['id'],
                            'country': region_code,
                            'published_at': item['snippet']['publishedAt'],
                            'duration': duration_seconds,
                            'duration_formatted': str(timedelta(seconds=duration_seconds)).split('.')[0],
                            'engagement_score': calculate_engagement_score(item)
                        }
                        all_videos.append(video)
                        print(f"Added video: {item['snippet']['title']}")
                    else:
                        print(f"Filtered out video: Views={view_count}, Duration={duration_seconds}s")
                except (KeyError, ValueError) as e:
                    print(f"Error processing video {item.get('id')}: {str(e)}")
                    continue
        
        # Sort by engagement score to get truly trending videos
        all_videos.sort(key=lambda x: x['engagement_score'], reverse=True)
        videos = all_videos[:10]  # Keep top 10
        
        print(f"Final result: {len(videos)} videos processed successfully")
        return videos
    except Exception as e:
        print(f"Error fetching trending videos: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return []

def get_content_suggestions(video_title, video_description, country_code):
    try:
        if not gemini_api_key:
            print("Error: Gemini API key is not set")
            return "Error: Gemini API key is not configured"
            
        prompt = f"""Based on this YouTube video trending in {country_code}:
        Title: {video_title}
        Description: {video_description}
        
        Please suggest 3-5 related content ideas that would be particularly appealing to viewers in {country_code}.
        Consider local trends, cultural context, and regional preferences.
        Format the suggestions as a list of engaging titles with brief descriptions."""
        
        response = model.generate_content(prompt)
        if response and hasattr(response, 'text'):
            return response.text
        else:
            print("Error: Invalid response from Gemini API")
            return "Error: Invalid response from Gemini API"
    except Exception as e:
        print(f"Error generating content suggestions: {str(e)}")
        return f"Error generating suggestions: {str(e)}"

def parse_duration(duration):
    """Convert YouTube duration (ISO 8601) to seconds"""
    try:
        return int(isodate.parse_duration(duration).total_seconds())
    except (ValueError, AttributeError):
        return 0

def get_country_trends_analysis(country_code, videos):
    """Generate analysis of trending videos for a country"""
    try:
        # Create a summary of the videos
        video_summary = "\n".join([
            f"- {video['title']} ({video['views']} views, {video['likes']} likes)"
            for video in videos
        ])
        
        prompt = f"""Analyze the trending videos in {country_code} and provide insights about:
        1. Common themes or topics
        2. Content types that are performing well
        3. Engagement patterns
        4. Potential opportunities for content creators
        
        Trending Videos:
        {video_summary}
        
        Please provide a concise analysis focusing on the most significant trends and patterns."""
        
        response = model.generate_content(prompt)
        return response.text if response and hasattr(response, 'text') else "Unable to analyze trends."
    except Exception as e:
        print(f"Error analyzing trends: {str(e)}")
        return "Error analyzing trends. Please try again."

@app.route('/')
def index():
    selected_country = request.args.get('country', 'US')
    videos = get_trending_videos(selected_country)
    return render_template('index.html', videos=videos, countries=COUNTRIES, selected_country=selected_country)

@app.route('/suggestions/<video_id>')
def get_suggestions(video_id):
    try:
        country_code = request.args.get('country', 'US')
        if not youtube_api_key:
            return jsonify({'error': 'YouTube API key is not configured'}), 500
            
        # Get video details
        video_request = youtube.videos().list(
            part='snippet',
            id=video_id
        )
        video_response = video_request.execute()
        
        if not video_response.get('items'):
            return jsonify({'error': 'Video not found'}), 404
            
        video = video_response['items'][0]
        suggestions = get_content_suggestions(
            video['snippet']['title'],
            video['snippet']['description'],
            country_code
        )
        
        if suggestions.startswith('Error:'):
            return jsonify({'error': suggestions}), 500
            
        return jsonify({'suggestions': suggestions})
    except Exception as e:
        print(f"Error in get_suggestions route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat/<country_code>', methods=['POST'])
def chat(country_code):
    try:
        print(f"Received chat request for country: {country_code}")
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            print("Error: No message provided in request")
            return jsonify({'error': 'No message provided'}), 400
        
        print(f"Processing message: {user_message}")
        
        if not gemini_api_key:
            print("Error: Gemini API key is not configured")
            return jsonify({'error': 'Gemini API key is not configured'}), 500
            
        # Get current trending videos for context
        print("Fetching trending videos for context...")
        videos = get_trending_videos(country_code)
        
        if not videos:
            print("Warning: No trending videos found for context")
        
        # Generate context from trending videos
        print("Generating trend analysis...")
        context = get_country_trends_analysis(country_code, videos)
        
        # Create chat prompt
        prompt = f"""Based on the current trending videos in {country_code}:
        
        Context about current trends:
        {context}
        
        User question: {user_message}
        
        Please provide a helpful response focusing on YouTube trends and content creation opportunities in {country_code}."""
        
        print("Sending request to Gemini API...")
        response = model.generate_content(prompt)
        
        if response and hasattr(response, 'text'):
            print("Successfully generated response")
            return jsonify({'response': response.text})
        else:
            print("Error: Invalid response from Gemini API")
            return jsonify({'error': 'Unable to generate response'}), 500
            
    except Exception as e:
        print(f"Error in chat route: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 