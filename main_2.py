import streamlit as st
import time
from openai import OpenAI
import random
import nltk
from newspaper import Article
from bs4 import BeautifulSoup
import requests
import os
from urllib.parse import urljoin
from datetime import datetime
from deep_translator import GoogleTranslator

# Download required NLTK data
nltk.download('punkt')


class LanguageConfig:
    SUPPORTED_LANGUAGES = {
        'english': {'code': 'en', 'voice_options': ['coral', 'onyx', 'nova', 'sage']},
        'spanish': {'code': 'es', 'voice_options': ['alloy', 'echo', 'fable', 'onyx']},
        'french': {'code': 'fr', 'voice_options': ['alloy', 'echo', 'nova', 'shimmer']},
        'german': {'code': 'de', 'voice_options': ['onyx', 'nova', 'fable', 'echo']},
        'hindi': {'code': 'hi', 'voice_options': ['alloy', 'echo', 'nova']},
        'tamil': {'code': 'ta', 'voice_options': ['alloy', 'echo', 'nova']},
        'russian': {'code': 'ru', 'voice_options': ['alloy', 'echo', 'fable', 'nova']},
        'italian': {'code': 'it', 'voice_options': ['alloy', 'echo', 'shimmer', 'nova']},
        'japanese': {'code': 'ja', 'voice_options': ['alloy', 'echo', 'nova']},
        'chinese-simplified': {'code': 'ny', 'voice_options': ['alloy', 'echo', 'fable']},
        'chinese': {'code': 'zh-CN', 'voice_options': ['alloy', 'echo', 'fable']}

    }


class ArticleTranslator:
    def __init__(self):
        self.translators = {}

    def get_translator(self, target_lang):
        if target_lang not in self.translators:
            self.translators[target_lang] = GoogleTranslator(
                source='en', target=target_lang)
        return self.translators[target_lang]

    def translate_text(self, text, target_lang):
        try:
            if target_lang == 'en':  # Skip translation for English
                return text

            # Split long text into chunks if needed (GoogleTranslator has a limit)
            max_chunk_size = 4500
            if len(text) > max_chunk_size:
                chunks = [text[i:i + max_chunk_size]
                          for i in range(0, len(text), max_chunk_size)]
                translated_chunks = []
                for chunk in chunks:
                    translator = self.get_translator(target_lang)
                    translated_chunks.append(translator.translate(chunk))
                return ' '.join(translated_chunks)
            else:
                translator = self.get_translator(target_lang)
                return translator.translate(text)
        except Exception as e:
            st.error(f"Translation error: {str(e)}")
            return text


# class NewsContentScraper:
#     def __init__(self):
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#         }
#         self.sources = {
#             'MPR News': {
#                 'url': 'https://www.mprnews.org',
#                 'article_link_selector': 'a[href*="/story/"]'
#             },
#             'MinnPost': {
#                 'url': 'https://www.minnpost.com',
#                 'article_link_selector': 'h3.entry-title a'
#             }
#         }

#     def get_links(self, source_name):
#         source_config = self.sources[source_name]
#         links = []
#         try:
#             response = requests.get(source_config['url'], headers=self.headers)
#             soup = BeautifulSoup(response.content, 'html.parser')
#             for link in soup.select(source_config['article_link_selector']):
#                 href = link.get('href')
#                 if href:
#                     full_url = urljoin(source_config['url'], href)
#                     links.append(full_url)
#             return links
#         except Exception as e:
#             st.error(f"Error getting links from {source_name}: {str(e)}")
#             return []

#     def scrape_article(self, url):
#         try:
#             article = Article(url)
#             article.download()
#             article.parse()
#             article.nlp()

#             return {
#                 'url': url,
#                 'title': article.title,
#                 'summary': article.summary,
#                 'date': article.publish_date.strftime('%Y-%m-%d') if article.publish_date else "Unknown",
#                 'timestamp': datetime.now().isoformat()
#             }
#         except Exception as e:
#             st.error(f"Error scraping article {url}: {str(e)}")
#             return None

#     def scrape_news(self, total_articles=5):
#         new_articles = []
#         for source_name in self.sources:
#             with st.spinner(f"Scraping {source_name}..."):
#                 links = self.get_links(source_name)
#                 for link in links:
#                     if len(new_articles) >= total_articles:
#                         break
#                     article_data = self.scrape_article(link)
#                     if article_data:
#                         article_data['source'] = source_name
#                         new_articles.append(article_data)
#                     time.sleep(1)
#                 if len(new_articles) >= total_articles:
#                     break
#         return new_articles[:total_articles]

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
            },
            'Star Tribune': {
                'url': 'https://www.startribune.com',
                'article_link_selector': 'a.article-link'
            },
            'KSTP': {
                'url': 'https://kstp.com/news',
                'article_link_selector': 'h3.article-title a'
            },
            'Fox 9': {
                'url': 'https://www.fox9.com/news',
                'article_link_selector': 'article.story a'
            }
        }

    def is_duplicate(self, new_article, existing_articles):
        """
        Check if an article is a duplicate based on title similarity or URL
        """
        if not new_article:
            return True

        # Create sets for duplicate checking
        existing_urls = {article['url'] for article in existing_articles}
        existing_titles = {article['title'].lower()
                           for article in existing_articles}

        # Direct URL match
        if new_article['url'] in existing_urls:
            return True

        # Title similarity check using fuzzy matching
        from difflib import SequenceMatcher

        def similar(a, b, threshold=0.85):
            return SequenceMatcher(None, a, b).ratio() > threshold

        new_title = new_article['title'].lower()
        for existing_title in existing_titles:
            if similar(new_title, existing_title):
                return True

        return False

    def get_links(self, source_name):
        source_config = self.sources[source_name]
        links = set()  # Using a set to avoid duplicate URLs
        try:
            response = requests.get(
                source_config['url'], headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            for link in soup.select(source_config['article_link_selector']):
                href = link.get('href')
                if href:
                    # Handle relative URLs
                    full_url = urljoin(source_config['url'], href)
                    links.add(full_url)
            return list(links)
        except Exception as e:
            st.error(f"Error getting links from {source_name}: {str(e)}")
            return []

    def scrape_article(self, url):
        try:
            article = Article(url)
            article.download()
            article.parse()
            article.nlp()

            # Basic content validation
            if not article.title or not article.summary or len(article.summary) < 50:
                return None

            return {
                'url': url,
                'title': article.title,
                'summary': article.summary,
                'date': article.publish_date.strftime('%Y-%m-%d') if article.publish_date else "Unknown",
                'timestamp': datetime.now().isoformat(),
                # Added for duplicate detection
                'text_hash': hash(article.title + article.summary)
            }
        except Exception as e:
            st.error(f"Error scraping article {url}: {str(e)}")
            return None

    def scrape_news(self, total_articles=5):
        new_articles = []
        seen_urls = set()

        for source_name in self.sources:
            if len(new_articles) >= total_articles:
                break

            with st.spinner(f"Scraping {source_name}..."):
                links = self.get_links(source_name)
                # Randomize to get different articles each time
                random.shuffle(links)

                for link in links:
                    if link in seen_urls:
                        continue

                    seen_urls.add(link)
                    article_data = self.scrape_article(link)

                    if article_data and not self.is_duplicate(article_data, new_articles):
                        article_data['source'] = source_name
                        new_articles.append(article_data)

                    if len(new_articles) >= total_articles:
                        break

                    time.sleep(1)  # Polite delay between requests

        return new_articles[:total_articles]


class TextToSpeech:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.language_config = LanguageConfig

    def generate_audio(self, text, output_path, language):
        try:
            voice_options = self.language_config.SUPPORTED_LANGUAGES[language]['voice_options']
            chosen_voice = random.choice(voice_options)

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


def display_article(article, idx, translator, tts):
    st.subheader(f"{article['source']}: {article['title']}")
    st.write(f"Date: {article['date']}")
    st.write(f"URL: {article['url']}")

    # Language selection for this article
    languages = list(LanguageConfig.SUPPORTED_LANGUAGES.keys())
    col1, col2 = st.columns([3, 1])

    with col2:
        selected_language = st.selectbox(
            "Select Language",
            languages,
            key=f"lang_select_{idx}",
            index=languages.index('english')
        )

    # Get translations based on selected language
    lang_code = LanguageConfig.SUPPORTED_LANGUAGES[selected_language]['code']

    if selected_language != 'english':
        translated_title = translator.translate_text(
            article['title'], lang_code)
        translated_summary = translator.translate_text(
            article['summary'], lang_code)
    else:
        translated_title = article['title']
        translated_summary = article['summary']

    with col1:
        st.write("Summary:")
        st.write(translated_summary)
        if selected_language != 'english':
            with st.expander("Show Original English"):
                st.write(article['summary'])

    # Generate and play audio
    audio_key = f"audio_{idx}_{selected_language}"
    if audio_key not in st.session_state:
        st.session_state[audio_key] = None

    if st.button("Generate Audio", key=f"audio_btn_{idx}"):
        with st.spinner("Generating audio..."):
            audio_file = f"article_{selected_language}_{idx}.mp3"
            if tts.generate_audio(translated_summary, audio_file, selected_language):
                st.session_state[audio_key] = audio_file
                st.rerun()

    if st.session_state[audio_key]:
        st.audio(st.session_state[audio_key])

    st.divider()


def main():
    st.title("Multilingual Minnesota News Digest")
    st.write(
        "Get the latest Minnesota news with AI-generated audio summaries in multiple languages!")

    # Initialize session state for articles if not exists
    if 'articles' not in st.session_state:
        st.session_state.articles = None

    # Sidebar for configuration
    st.sidebar.header("Configuration")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    num_articles = 5

    # Initialize components
    scraper = NewsContentScraper()
    translator = ArticleTranslator()
    tts = TextToSpeech(openai_api_key)

    # Fetch news button
    if st.button("Fetch Latest News"):
        st.session_state.articles = scraper.scrape_news(
            total_articles=num_articles)

    # Display articles if they exist in session state
    if st.session_state.articles:
        for idx, article in enumerate(st.session_state.articles):
            display_article(article, idx, translator, tts)


if __name__ == "__main__":
    main()
