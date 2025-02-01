import json
from pydub import AudioSegment
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


class NewsContentScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Updated source configurations with more specific selectors
        self.sources = {
            'MPR News': {
                'url': 'https://www.mprnews.org',
                'article_link_selector': 'a[href*="/story/"]',
                'priority': 1
            },
            'Star Tribune': {
                'url': 'https://www.startribune.com',
                'article_link_selector': '.article-link, .article-preview a',
                'priority': 1
            },
            'Fox 9': {
                'url': 'https://www.fox9.com/news',
                'article_link_selector': '.article a, .story a',
                'priority': 2
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
                source_config['url'],
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()  # Raise an exception for bad status codes

            soup = BeautifulSoup(response.content, 'html.parser')
            selectors = source_config['article_link_selector'].split(', ')

            for selector in selectors:
                for link in soup.select(selector):
                    href = link.get('href')
                    if href:
                        # Handle relative URLs
                        full_url = urljoin(source_config['url'], href)
                        # Basic filtering for relevant URLs
                        if '/story/' in full_url or '/article/' in full_url or '/news/' in full_url:
                            links.add(full_url)

            return list(links)[:10]  # Limit to top 10 links per source
        except Exception as e:
            st.error(f"Error getting links from {source_name}: {str(e)}")
            return []

    def scrape_article(self, url):
        try:
            article = Article(url)
            article.download()
            article.parse()
            article.nlp()

            # Enhanced content validation
            if not article.title or not article.summary or len(article.summary) < 50:
                return None

            # Remove any unwanted text patterns (customize as needed)
            summary = article.summary
            unwanted_patterns = [
                "Subscribe today", "Support local journalism",
                "Read more:", "Related:", "Advertisement"
            ]
            for pattern in unwanted_patterns:
                summary = summary.replace(pattern, "")

            return {
                'url': url,
                'title': article.title,
                'summary': summary.strip(),
                'date': article.publish_date.strftime('%Y-%m-%d') if article.publish_date else "Unknown",
                'timestamp': datetime.now().isoformat(),
                'text_hash': hash(article.title + summary)
            }
        except Exception as e:
            st.error(f"Error scraping article {url}: {str(e)}")
            return None

    def scrape_news(self, total_articles=5):
        new_articles = []
        seen_urls = set()

        # Group sources by priority
        priority_groups = {}
        for source_name, config in self.sources.items():
            priority = config['priority']
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(source_name)

        # Shuffle sources within each priority group
        for priority in priority_groups:
            random.shuffle(priority_groups[priority])

        # Process sources in priority order
        articles_per_source = total_articles // len(self.sources)
        # At least 1 article per source
        min_articles_per_source = max(1, articles_per_source)

        for priority in sorted(priority_groups.keys()):
            for source_name in priority_groups[priority]:
                if len(new_articles) >= total_articles:
                    break

                with st.spinner(f"Fetching from {source_name}..."):
                    links = self.get_links(source_name)
                    # Randomize articles from each source
                    random.shuffle(links)

                    source_articles = 0
                    for link in links:
                        if link in seen_urls:
                            continue

                        if source_articles >= min_articles_per_source:
                            break

                        if len(new_articles) >= total_articles:
                            break

                        seen_urls.add(link)
                        article_data = self.scrape_article(link)

                        if article_data and not self.is_duplicate(article_data, new_articles):
                            article_data['source'] = source_name
                            new_articles.append(article_data)
                            source_articles += 1

                        time.sleep(0.5)  # Polite delay between requests

        random.shuffle(new_articles)  # Final shuffle for variety
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
    # st.write(f"Date: {article['date']}")
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


class PodcastGenerator:
    def __init__(self, openai_client):
        self.client = openai_client
        self.host_personas = {
            "Sarah": {
                "personality": "warm and engaging lead host, asks insightful questions",
                "voice": "nova",
                "pause_after": 0.5  # seconds
            },
            "Mike": {
                "personality": "enthusiastic co-host with a bit of humor, provides context and analysis",
                "voice": "onyx",
                "pause_after": 0.5  # seconds
            }
        }

    def generate_podcast_script(self, articles):
        # Prepare the news content for the prompt
        news_content = "\n\n".join([
            f"Article from {article['source']}:\nTitle: {article['title']}\nSummary: {article['summary']}"
            for article in articles
        ])

        # Create the prompt for the conversation
        prompt = f"""Create a natural, engaging podcast conversation between two hosts discussing today's Minnesota news. 
        
        Host Personas:
        - Sarah: {self.host_personas['Sarah']['personality']}
        - Mike: {self.host_personas['Mike']['personality']}

        Format the conversation using [Sarah] and [Mike] tags. Include reactions, questions, and natural transitions.
        Keep each speaking segment under 30 seconds for better audio flow.

        Start with a welcome and end with a sign-off.
        Make the discussion feel natural and conversational, not just reading headlines.
        
        Today's News Content:
        {news_content}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{
                    "role": "system",
                    "content": "You are a podcast script writer creating engaging conversations about news."
                },
                    {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Error generating podcast script: {str(e)}")
            return None

    def split_script_into_segments(self, script):
        segments = []
        current_speaker = None
        current_text = []

        for line in script.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Check for speaker tags
            if '[Sarah]' in line:
                if current_speaker:
                    segments.append({
                        'speaker': current_speaker,
                        'text': ' '.join(current_text)
                    })
                current_speaker = 'Sarah'
                current_text = [line.replace('[Sarah]', '').strip()]
            elif '[Mike]' in line:
                if current_speaker:
                    segments.append({
                        'speaker': current_speaker,
                        'text': ' '.join(current_text)
                    })
                current_speaker = 'Mike'
                current_text = [line.replace('[Mike]', '').strip()]
            else:
                current_text.append(line)

        # Add the last segment
        if current_speaker and current_text:
            segments.append({
                'speaker': current_speaker,
                'text': ' '.join(current_text)
            })

        return segments

    def generate_audio_segment(self, text, speaker, index):
        try:
            output_path = f"temp_audio_{index}.mp3"
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=self.host_personas[speaker]['voice'],
                input=text
            )
            response.stream_to_file(output_path)
            return output_path
        except Exception as e:
            st.error(f"Error generating audio segment: {str(e)}")
            return None

    def create_podcast(self, articles):
        # Generate the script
        script = self.generate_podcast_script(articles)
        if not script:
            return None

        # Split into segments
        segments = self.split_script_into_segments(script)

        # Generate audio for each segment
        audio_files = []
        for i, segment in enumerate(segments):
            with st.spinner(f"Generating audio for {segment['speaker']}..."):
                audio_path = self.generate_audio_segment(
                    segment['text'],
                    segment['speaker'],
                    i
                )
                if audio_path:
                    audio_files.append({
                        'path': audio_path,
                        'pause_after': self.host_personas[segment['speaker']]['pause_after']
                    })

        # Combine all audio segments
        if audio_files:
            final_audio = AudioSegment.empty()
            for audio_file in audio_files:
                segment = AudioSegment.from_mp3(audio_file['path'])
                final_audio += segment

                # Add pause between segments
                pause = AudioSegment.silent(
                    duration=int(audio_file['pause_after'] * 1000))
                final_audio += pause

                # Clean up temporary file
                os.remove(audio_file['path'])

            # Save final podcast
            output_path = f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            final_audio.export(output_path, format="mp3")
            return output_path, script

        return None, script


# Set page config for a wider layout and custom theme
st.set_page_config(
    page_title="Minnesota News Hub",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern dark mode styling
st.markdown("""
    <style>
        /* Main container */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* Headers */
        h1 {
            color: #60A5FA;
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            margin-bottom: 1.5rem !important;
            text-align: center;
        }

        h2 {
            color: #93C5FD;
            font-size: 1.8rem !important;
            font-weight: 600 !important;
            margin-top: 2rem !important;
        }

        h3 {
            color: #BFDBFE;
            font-size: 1.3rem !important;
            font-weight: 500 !important;
        }

        /* Cards for articles */
        .article-card {
            background-color: #1F2937;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            border: 1px solid #374151;
        }

        /* Buttons */
        .stButton button {
            background: linear-gradient(45deg, #2563EB, #3B82F6);
            color: white;
            border-radius: 8px;
            padding: 0.75rem 1.75rem;
            font-weight: 500;
            border: none;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        }

        .stButton button:hover {
            background: linear-gradient(45deg, #1E40AF, #2563EB);
            box-shadow: 0 6px 8px rgba(0, 0, 0, 0.3);
            transform: translateY(-2px);
        }

        /* Sidebar styling */
        .css-1d391kg, [data-testid="stSidebar"] {
            background-color: #111827;
            border-right: 1px solid #374151;
        }

        .sidebar-card {
            background-color: #1F2937;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid #374151;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
            margin-bottom: 2rem;
            background-color: #1F2937;
            padding: 0.5rem;
            border-radius: 12px;
        }

        .stTabs [data-baseweb="tab"] {
            color: #9CA3AF;
            font-weight: 500;
        }

        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            color: #60A5FA;
            border-bottom-color: #60A5FA;
        }

        /* Audio player */
        audio {
            width: 100%;
            margin: 1rem 0;
            border-radius: 8px;
            background-color: #374151;
        }

        /* Source badges */
        .source-badge {
            display: inline-block;
            padding: 0.35rem 1rem;
            background: linear-gradient(45deg, #1E40AF, #2563EB);
            color: white;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.75rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }

        /* Language selector */
        .stSelectbox select {
            background-color: #374151;
            color: white;
            border: 1px solid #4B5563;
            border-radius: 8px;
        }

        /* Expander */
        .streamlit-expanderHeader {
            background-color: #1F2937;
            border-radius: 8px;
            border: 1px solid #374151;
        }

        /* Status messages */
        .stSuccess, .stInfo {
            background-color: #1F2937;
            border: 1px solid #374151;
            border-radius: 8px;
            padding: 1rem;
            color: #E5E7EB;
        }

        /* Links */
        a {
            color: #60A5FA;
            text-decoration: none;
            transition: color 0.2s ease;
        }

        a:hover {
            color: #93C5FD;
            text-decoration: none;
        }

        /* Custom sidebar button */
        .sidebar-button {
            background: linear-gradient(45deg, #2563EB, #3B82F6);
            color: white;
            padding: 1rem;
            border-radius: 12px;
            text-align: center;
            margin: 1rem 0;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        }

        .sidebar-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0, 0, 0, 0.3);
        }

        /* Custom progress bars */
        .stProgress > div > div {
            background-color: #2563EB;
        }

        /* Custom metric styling */
        .metric-card {
            background-color: #1F2937;
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid #374151;
            margin-bottom: 1rem;
        }

        .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #60A5FA;
        }
    </style>
""", unsafe_allow_html=True)


def main():
    # Header with logo and title
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <h1>
                <span style='font-size: 3rem'>📰</span>
                MinneDigest: An AI-Powered News Digest App
            </h1>
        """, unsafe_allow_html=True)

    st.markdown("""
        <p style='text-align: center; color: #9CA3AF; margin-bottom: 2rem;'>
            Your personalized gateway to Minnesota news with AI-powered translations and audio
        </p>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'articles' not in st.session_state:
        st.session_state.articles = None

    openai_api_key = os.environ.get("OPENAI_API_KEY")

    # Initialize components
    scraper = NewsContentScraper()
    translator = ArticleTranslator()
    tts = TextToSpeech(openai_api_key)
    podcast_generator = PodcastGenerator(OpenAI(api_key=openai_api_key))

    # Enhanced fetch news button in sidebar
    if st.sidebar.markdown("""
        <div class='sidebar-button'>
            <h4 style='margin: 0; color: white;'>🔄 Refresh News Feed</h4>
            <p style='margin: 0.5rem 0 0 0; font-size: 0.8rem; color: rgba(255,255,255,0.8);'>
                Get the latest stories
            </p>
        </div>
        """, unsafe_allow_html=True):
        with st.spinner("🌟 Gathering the latest stories..."):
            st.session_state.articles = scraper.scrape_news(total_articles=7)

    # Tabs with enhanced styling
    tabs = st.tabs(["📰 News Feed", "🎙️ Daily Podcast"])

    # News Feed Tab
    with tabs[0]:
        if st.session_state.articles:
            for idx, article in enumerate(st.session_state.articles):
                with st.container():
                    # st.markdown("""
                    #     <div class='article-card'>
                    # """, unsafe_allow_html=True)
                    st.markdown(f"""
                        <div class='source-badge'>
                            {article['source']}
                        </div>
                    """, unsafe_allow_html=True)
                    display_article(article, idx, translator, tts)
                    # st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class='article-card' style='text-align: center;'>
                    <h3 style='color: #60A5FA;'>Welcome to MinneDigest News Hub! 🌟</h3>
                    <p style='color: #9CA3AF;'>Click 'Refresh News Feed' in the sidebar to get started</p>
                </div>
            """, unsafe_allow_html=True)

    # Podcast Tab
    with tabs[1]:
        if st.session_state.articles:
            st.markdown("""
                <div class='article-card'>
                    <h2 style='text-align: center; margin-bottom: 2rem; color: #60A5FA;'>
                        🎙️ AI-Generated News Podcast
                    </h2>
                    <p style='text-align: center; color: #9CA3AF;'>
                        Get your personalized news digest in audio format
                    </p>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🎵 Generate Today's Podcast", key="generate_podcast"):
                with st.spinner("Creating your personalized news podcast..."):
                    podcast_path, script = podcast_generator.create_podcast(
                        st.session_state.articles)
                    if podcast_path:
                        st.success("✨ Your podcast is ready!")
                        st.audio(podcast_path)
                        with st.expander("📝 View Podcast Script"):
                            st.markdown(script)
                    else:
                        st.error("Unable to generate podcast")

            # Show article sources in a clean grid
            with st.expander("📚 Today's News Sources"):
                for article in st.session_state.articles:
                    st.markdown(f"""
                        <div class='metric-card'>
                            <strong style='color: #60A5FA;'>{article['source']}</strong>
                            <p style='color: #9CA3AF; margin: 0;'>{article['title']}</p>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class='article-card' style='text-align: center;'>
                    <h3 style='color: #60A5FA;'>Ready to Create Your Podcast? 🎧</h3>
                    <p style='color: #9CA3AF;'>First, refresh the news feed to get the latest stories</p>
                </div>
            """, unsafe_allow_html=True)

    # Enhanced sidebar information
    st.sidebar.markdown("""
        <div class='sidebar-card'>
            <h3 style='margin-top: 0; color: #60A5FA;'>ℹ️ Features</h3>
            <div style='color: #9CA3AF; font-size: 0.9rem;'>
                <div class='metric-card'>
                    <span class='metric-value'>🌐</span>
                    <p>Real-time news updates</p>
                </div>
                <div class='metric-card'>
                    <span class='metric-value'>🗣️</span>
                    <p>Multi-language translations</p>
                </div>
                <div class='metric-card'>
                    <span class='metric-value'>🎧</span>
                    <p>Text-to-speech in various languages</p>
                </div>
                <div class='metric-card'>
                    <span class='metric-value'>🎙️</span>
                    <p>AI-generated news podcasts</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
