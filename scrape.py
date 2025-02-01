import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from newspaper import Article
import time


class MinnesotaNewsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.news_sources = {
            'MPR News': 'https://www.mprnews.org',
            'Star Tribune': 'https://www.startribune.com',
            'MinnPost': 'https://www.minnpost.com'
        }

    def scrape_article(self, url):
        try:
            article = Article(url)
            article.download()
            article.parse()

            return {
                'title': article.title,
                'text': article.text,
                'publish_date': article.publish_date,
                'authors': article.authors,
                'url': url,
                'timestamp': datetime.now()
            }
        except Exception as e:
            print(f"Error scraping article {url}: {str(e)}")
            return None

    def scrape_mpr_news(self):
        articles = []
        try:
            response = requests.get(
                self.news_sources['MPR News'], headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article links - adjust selector based on actual HTML structure
            article_links = soup.select('a[href*="/story/"]')

            for link in article_links[:10]:  # Limit to 10 articles for testing
                article_url = self.news_sources['MPR News'] + link['href']
                article_data = self.scrape_article(article_url)
                if article_data:
                    article_data['source'] = 'MPR News'
                    articles.append(article_data)
                time.sleep(1)  # Respect the website by adding delay

        except Exception as e:
            print(f"Error scraping MPR News: {str(e)}")

        return articles

    def save_to_csv(self, articles, filename='minnesota_news.csv'):
        df = pd.DataFrame(articles)
        df.to_csv(filename, index=False)
        print(f"Saved {len(articles)} articles to {filename}")


# Usage example
if __name__ == "__main__":
    scraper = MinnesotaNewsScraper()

    # Scrape MPR News
    mpr_articles = scraper.scrape_mpr_news()

    # Save results
    scraper.save_to_csv(mpr_articles)
