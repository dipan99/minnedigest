import streamlit as st
import json
import time
from pathlib import Path
from openai import OpenAI
import random
import nltk
from newspaper import Article
from bs4 import BeautifulSoup
import requests
import os
from urllib.parse import urljoin
from datetime import datetime

# Download required NLTK data
nltk.download('punkt')


class NewsContentScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.sources = {
            'MPR News': {
                'url': 'https://www.mprnews.org',
                'article_link_selector': 'a[href*="/story/"]'
            },
            'MinnPost': {
                'url': 'https://www.minnpost.com',
                'article_link_selector': 'h3.entry-title a'
            }
        }

    def get_links(self, source_name):
        source_config = self.sources[source_name]
        links = []
        try:
            response = requests.get(source_config['url'], headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            for link in soup.select(source_config['article_link_selector']):
                href = link.get('href')
                if href:
                    full_url = urljoin(source_config['url'], href)
                    links.append(full_url)
            return links
        except Exception as e:
            st.error(f"Error getting links from {source_name}: {str(e)}")
            return []

    def scrape_article(self, url):
        try:
            article = Article(url)
            article.download()
            article.parse()
            article.nlp()

            return {
                'url': url,
                'title': article.title,
                'summary': article.summary,
                'date': article.publish_date.strftime('%Y-%m-%d') if article.publish_date else "Unknown"
            }
        except Exception as e:
            st.error(f"Error scraping article {url}: {str(e)}")
            return None

    def scrape_news(self, total_articles=5):
        all_articles = []
        for source_name in self.sources:
            with st.spinner(f"Scraping {source_name}..."):
                links = self.get_links(source_name)
                for link in links:
                    if len(all_articles) >= total_articles:
                        break
                    article_data = self.scrape_article(link)
                    if article_data:
                        article_data['source'] = source_name
                        all_articles.append(article_data)
                    time.sleep(1)
                if len(all_articles) >= total_articles:
                    break
        return all_articles


class TextToSpeech:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.voices = ["coral", "onyx", "nova", "sage"]

    def generate_audio(self, text, output_path):
        try:
            chosen_voice = random.choice(self.voices)
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=chosen_voice,
                input=text
            )
            response.stream_to_file(output_path)
            return True
        except Exception as e:
            st.error(f"Error generating audio: {str(e)}")
            return False


def main():
    st.title("Minnesota News Digest")
    st.write("Get the latest Minnesota news with AI-generated audio summaries!")

    # Sidebar for configuration
    st.sidebar.header("Configuration")
    # openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    num_articles = st.sidebar.slider("Number of articles to fetch", 1, 10, 5)

    # if not openai_api_key:
    #     st.warning(
    #         "Please enter your OpenAI API key in the sidebar to enable text-to-speech.")
    #     return

    # Initialize components
    scraper = NewsContentScraper()
    tts = TextToSpeech(openai_api_key)

    # Fetch news button
    if st.button("Fetch Latest News"):
        # Scrape news articles
        articles = scraper.scrape_news(total_articles=num_articles)

        # Display articles and generate audio
        for idx, article in enumerate(articles):
            st.subheader(f"{article['source']}: {article['title']}")
            st.write(f"Date: {article['date']}")
            st.write(f"URL: {article['url']}")

            with st.expander("Read Summary"):
                st.write(article['summary'])

            # Generate and play audio
            audio_file = f"article_{idx}.mp3"
            with st.spinner("Generating audio..."):
                if tts.generate_audio(article['summary'], audio_file):
                    st.audio(audio_file)
                else:
                    st.error("Failed to generate audio for this article")

            st.divider()


if __name__ == "__main__":
    main()
