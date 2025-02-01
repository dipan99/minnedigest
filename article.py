import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from newspaper import Article
from urllib.parse import urljoin
import nltk
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
        """Scrape article links from a source."""
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
            print(f"Error getting links from {source_name}: {str(e)}")
            return []

    def scrape_article(self, url):
        """Scrape article summary, title, and date."""
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
            print(f"Error scraping article {url}: {str(e)}")
            return None

    def scrape_news(self, total_articles=5):
        """Scrape a total of `total_articles` from all sources."""
        all_articles = []

        for source_name in self.sources:
            print(f"\nScraping {source_name}...")
            links = self.get_links(source_name)

            for link in links:
                if len(all_articles) >= total_articles:
                    break
                article_data = self.scrape_article(link)
                if article_data:
                    all_articles.append(article_data)
                time.sleep(1)  # Respectful delay

            if len(all_articles) >= total_articles:
                break

        # Save to JSON
        with open('minnesota_news_summary.json', 'w') as f:
            json.dump(all_articles, f, indent=4)

        print(
            f"\nSaved {len(all_articles)} articles to minnesota_news_summary.json")
        return all_articles


# Usage example
if __name__ == "__main__":
    scraper = NewsContentScraper()
    scraped_articles = scraper.scrape_news()
