import time
import uuid
from duckduckgo_search import DDGS
import sys
sys.path.insert(0, '/home/keanu/royalhack/podcastfy-generator/podcastfy')
from podcastfy.client import generate_podcast
import requests
import os
import json
import re
import pathlib
import io
import dotenv
import logging
import zipfile
from os.path import basename
from openai import OpenAI
from flask import Flask, g, request, Response, jsonify, send_file

dotenv.load_dotenv()

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
#log = logging.getLogger('werkzeug')
#logging.set(logging.ERROR)

app = Flask(__name__)

@app.before_request
def log_route_start():
    g.start_time = time.time()
    
@app.after_request
def log_route_end(response):
    route = request.endpoint
    logging.info(f"{route} ended after {time.time() - g.pop('start_time', None)}")
    return response


AI_OPENAI_URL = os.getenv("AI_OPENAI_URL")
AI_OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key="")
if AI_OPENAI_URL != "":
    client = OpenAI(base_url = AI_OPENAI_URL, api_key=AI_OPENAI_KEY)

# search_wikipedia takes a search query and returns a URL to the most likely matching Wikipedia article.
def search_wikipedia(search_query):
    # Python 3
    # Choose your language, and search for articles.

    language_code = 'en'
    number_of_results = 1
    headers = {
    # 'Authorization': 'Bearer YOUR_ACCESS_TOKEN',
    'User-Agent': 'Walkie Talkie (wtalkie@keanuc.net)'
    }

    base_url = 'https://api.wikimedia.org/core/v1/wikipedia/'
    endpoint = '/search/page'
    url = base_url + language_code + endpoint
    parameters = {'q': search_query, 'limit': number_of_results}
    response = requests.get(url, headers=headers, params=parameters)

    response = json.loads(response.text)

    page_titles = []
    page_urls = []

    for page in response['pages']:
        page_titles.append(page['title'])
        page_urls.append('https://' + language_code + '.wikipedia.org/wiki/' + page['key'])

    most_relevant_page = get_most_relevant_page(search_query, page_titles)

    logging.info(page_titles)
    logging.info(page_urls)
    logging.info(most_relevant_page)

    relevant_page_index = page_titles.index(most_relevant_page)

    logging.info(relevant_page_index)

    return page_urls[relevant_page_index]

# Function to get the most relevant Wikipedia page title
def get_most_relevant_page(query, titles):
    prompt = f"Here is a list of Wikipedia page titles: {titles}. Which one is the most relevant to the search query?"

    prompt = f"""
    Task:
    Identify the most relevant Wikipedia article title from the given list based on the search query. Your answer should be returned as a single structured string.

    Search Query: "{query}"
    Wikipedia Titles: {titles}

    Evaluation Criteria:

        Exact Match (30%) – Direct or near match with the query.
        Semantic Similarity (30%) – Does the title capture the same concept, even if phrased differently?
        Wikipedia Naming Conventions (20%) – Would Wikipedia typically use this title?
        Contextual Relevance (20%) – Is this the most likely intended topic?

    Instructions:

        Select the Best Match – Pick the title with the highest relevance score.
        Provide a Confidence Score (0-100%) – Estimate how well the selected title fits the query.
        Rank the Top 3 Matches (if applicable) – If multiple titles are strong candidates, list them.
        Handle Ambiguities – If the query is unclear, suggest refinements.

    Output Format (Single String):
    "Best Match: [Title] (Confidence: X%). Alternative Matches: 1. [Title] (X%), 2. [Title] (X%). Ambiguity Notes: [Explanation, if applicable]."

    If no alternative matches or ambiguity exist, omit those sections.
    """

    # Make the request to OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Use the suitable GPT model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        # Log the full response for debugging

        # Extract the result from the response
        result = response.choices[0].message.content
        if result:
            logging.info("Full AI Response: %s", result)
            result = result.strip()

            match = re.search(r'Best Match: ([^\(]+)', result)
            if match:
                final_result = match.group(1).strip()
                return final_result
            else:
                return ""

    except Exception as e:
        # If parsing or any other error occurs, print the error message and the full response
        logging.error("Error while parsing AI response: %s", e)
        logging.error("Full AI Response: %s", response)  # Log the full response for further analysis
        return ""  # Fallback to empty data

@app.route("/generate", methods=["POST"])
async def generate_audio():
    
    place_name = request.form.get('place_name')

    content = request.json
    place_name = content["place"]

    # Search Wikipedia for URL
    wikipedia_search_url = search_wikipedia(place_name)
    if wikipedia_search_url == "":
        return Response(status=400, message="No Wikipedia results found")

    # Search DuckDuckGo
    search_results = DDGS().text(place_name, max_results=5)
    if not search_results:
        return Response(status=400, message="No DuckDuckGo results found")

    # Aggregate URLs
    #+ [result['href'] for result in search_results]

    # Generate podcast
    audio_file, transcript_file = generate_podcast(urls=[wikipedia_search_url], tts_model='elevenlabs')

    base_files = [audio_file, transcript_file]
    zip_file_path = f'./data/{uuid.uuid4().hex}.zip'
    
    # generate random uuid
    #

    #base_path = pathlib.Path('./data/')
    data = io.BytesIO()
    with zipfile.ZipFile(data, mode='w') as z:
        z.write(audio_file)
        z.write(transcript_file)
    data.seek(0)
    return send_file(
        data,
        mimetype='application/zip',
        as_attachment=True,
        download_name='data.zip'
    )

if __name__ == "__main__":
    app.run(port=6869, debug=True)