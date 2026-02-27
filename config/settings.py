from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # LLM providers
    openai_api_key: str = ""
    cerebras_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    cerebras_model: str = "zai-glm-4.7"

    # Data sources
    fred_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""

    # App config
    refresh_interval_minutes: int = 30
    auto_refresh_interval_minutes: int = 60
    max_narratives: int = 50
    narrative_lookback_days: int = 30

    # RSS feeds - financial news
    news_feeds: list[str] = [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.reuters.com/reuters/topNews",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910",
    ]


settings = Settings()
