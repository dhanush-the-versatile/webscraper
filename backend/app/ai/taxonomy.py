"""Curated taxonomies used by the heuristic (no-LLM) fallbacks.

These are intentionally small, high-precision dictionaries — enough to make
requirement parsing and profile extraction useful offline. The LLM path
supersedes them when API keys are configured.
"""

from __future__ import annotations

# skill/tech name -> category
TECH_TAXONOMY: dict[str, str] = {
    # Languages
    "python": "language", "javascript": "language", "typescript": "language",
    "java": "language", "go": "language", "golang": "language", "rust": "language",
    "c++": "language", "c#": "language", "ruby": "language", "php": "language",
    "swift": "language", "kotlin": "language", "scala": "language", "r": "language",
    "sql": "language", "dart": "language", "elixir": "language",
    # Frontend
    "react": "framework", "next.js": "framework", "nextjs": "framework",
    "vue": "framework", "nuxt": "framework", "angular": "framework",
    "svelte": "framework", "tailwind": "framework", "tailwindcss": "framework",
    "redux": "framework", "html": "skill", "css": "skill", "sass": "skill",
    "react native": "framework", "flutter": "framework",
    # Backend
    "fastapi": "framework", "django": "framework", "flask": "framework",
    "node.js": "framework", "nodejs": "framework", "express": "framework",
    "nestjs": "framework", "spring": "framework", "spring boot": "framework",
    "rails": "framework", "laravel": "framework", "graphql": "technology",
    "grpc": "technology", "rest": "technology",
    # Data / AI
    "machine learning": "skill", "deep learning": "skill", "nlp": "skill",
    "computer vision": "skill", "data science": "skill", "data engineering": "skill",
    "pytorch": "framework", "tensorflow": "framework", "scikit-learn": "framework",
    "pandas": "framework", "numpy": "framework", "spark": "technology",
    "airflow": "technology", "dbt": "technology", "kafka": "technology",
    "llm": "skill", "llms": "skill", "genai": "skill", "generative ai": "skill",
    "langchain": "framework", "langgraph": "framework", "rag": "skill",
    "prompt engineering": "skill", "openai": "technology", "anthropic": "technology",
    "hugging face": "technology", "transformers": "framework", "mlops": "skill",
    "kaggle": "technology", "fine-tuning": "skill", "vector databases": "technology",
    # Infra / DevOps
    "docker": "technology", "kubernetes": "technology", "k8s": "technology",
    "terraform": "technology", "ansible": "technology", "aws": "technology",
    "gcp": "technology", "azure": "technology", "ci/cd": "skill",
    "github actions": "technology", "jenkins": "technology", "linux": "technology",
    "devops": "skill", "sre": "skill", "observability": "skill",
    # Databases
    "postgresql": "technology", "postgres": "technology", "mysql": "technology",
    "mongodb": "technology", "redis": "technology", "elasticsearch": "technology",
    "sqlite": "technology", "dynamodb": "technology", "pgvector": "technology",
    # Design
    "figma": "tool", "sketch": "tool", "adobe xd": "tool", "photoshop": "tool",
    "illustrator": "tool", "ui design": "skill", "ux design": "skill",
    "ui/ux": "skill", "design systems": "skill", "prototyping": "skill",
    "user research": "skill", "interaction design": "skill",
    # Mobile / other
    "ios": "technology", "android": "technology", "blockchain": "technology",
    "solidity": "language", "web3": "technology", "security": "skill",
    "penetration testing": "skill", "agile": "skill", "scrum": "skill",
    "microservices": "skill", "distributed systems": "skill",
    "system design": "skill", "celery": "framework", "playwright": "framework",
    "selenium": "framework", "web scraping": "skill", "etl": "skill",
}

JOB_TITLES: list[str] = [
    "software engineer", "software developer", "frontend developer", "front-end developer",
    "backend developer", "back-end developer", "full stack developer", "fullstack developer",
    "full-stack developer", "web developer", "mobile developer", "ios developer",
    "android developer", "react developer", "python developer", "java developer",
    "golang developer", "node developer", "javascript developer", "typescript developer",
    "ai engineer", "ml engineer", "machine learning engineer", "data scientist",
    "data engineer", "data analyst", "mlops engineer", "research scientist",
    "research engineer", "nlp engineer", "computer vision engineer",
    "devops engineer", "site reliability engineer", "platform engineer",
    "cloud engineer", "security engineer", "qa engineer", "test engineer",
    "ui designer", "ux designer", "ui/ux designer", "product designer",
    "graphic designer", "web designer", "interaction designer", "visual designer",
    "engineering manager", "tech lead", "team lead", "cto", "vp of engineering",
    "product manager", "technical product manager", "founder", "co-founder",
    "startup founder", "freelancer", "consultant", "solutions architect",
    "software architect", "blockchain developer", "game developer",
    "embedded engineer", "firmware engineer", "database administrator",
]

SENIORITY_KEYWORDS: dict[str, str] = {
    "intern": "intern", "internship": "intern", "trainee": "intern",
    "junior": "junior", "entry level": "junior", "entry-level": "junior", "graduate": "junior",
    "mid level": "mid", "mid-level": "mid", "intermediate": "mid",
    "senior": "senior", "sr.": "senior", "sr ": "senior", "experienced": "senior",
    "lead": "lead", "staff": "lead",
    "principal": "principal", "expert": "principal",
    "head of": "executive", "director": "executive", "vp": "executive",
    "chief": "executive", "cto": "executive", "founder": "executive",
}

COUNTRIES: dict[str, list[str]] = {
    # canonical -> aliases/major cities (for weak location inference)
    "germany": ["berlin", "munich", "hamburg", "cologne", "frankfurt", "stuttgart"],
    "united states": ["usa", "us", "new york", "san francisco", "seattle", "austin",
                      "boston", "los angeles", "chicago", "nyc", "bay area"],
    "united kingdom": ["uk", "london", "manchester", "edinburgh", "cambridge", "bristol"],
    "india": ["bangalore", "bengaluru", "mumbai", "delhi", "hyderabad", "pune", "chennai"],
    "canada": ["toronto", "vancouver", "montreal", "ottawa"],
    "france": ["paris", "lyon", "toulouse"],
    "netherlands": ["amsterdam", "rotterdam", "utrecht", "eindhoven"],
    "spain": ["madrid", "barcelona", "valencia"],
    "portugal": ["lisbon", "porto"],
    "poland": ["warsaw", "krakow", "wroclaw"],
    "sweden": ["stockholm", "gothenburg"],
    "switzerland": ["zurich", "geneva", "lausanne"],
    "austria": ["vienna"],
    "ireland": ["dublin"],
    "australia": ["sydney", "melbourne", "brisbane"],
    "singapore": ["singapore"],
    "japan": ["tokyo", "osaka"],
    "brazil": ["sao paulo", "rio de janeiro"],
    "mexico": ["mexico city", "guadalajara"],
    "argentina": ["buenos aires"],
    "italy": ["milan", "rome", "turin"],
    "belgium": ["brussels", "antwerp", "ghent"],
    "denmark": ["copenhagen"],
    "norway": ["oslo"],
    "finland": ["helsinki"],
    "czech republic": ["prague", "brno"],
    "romania": ["bucharest", "cluj"],
    "ukraine": ["kyiv", "kiev", "lviv"],
    "israel": ["tel aviv", "jerusalem"],
    "united arab emirates": ["dubai", "abu dhabi", "uae"],
    "nigeria": ["lagos", "abuja"],
    "kenya": ["nairobi"],
    "south africa": ["cape town", "johannesburg"],
    "china": ["beijing", "shanghai", "shenzhen"],
    "south korea": ["seoul"],
    "indonesia": ["jakarta"],
    "vietnam": ["hanoi", "ho chi minh"],
    "philippines": ["manila"],
    "turkey": ["istanbul", "ankara"],
    "estonia": ["tallinn"],
    "greece": ["athens"],
    "new zealand": ["auckland", "wellington"],
}

INDUSTRIES: list[str] = [
    "fintech", "healthtech", "healthcare", "edtech", "e-commerce", "ecommerce",
    "saas", "gaming", "cybersecurity", "biotech", "insurtech", "proptech",
    "logistics", "automotive", "aerospace", "retail", "banking", "insurance",
    "telecom", "media", "advertising", "travel", "hospitality", "energy",
    "climate", "agritech", "legaltech", "hr tech", "martech", "web3", "crypto",
    "ai", "artificial intelligence", "healthcare ai", "robotics", "iot",
    "manufacturing", "consulting", "government", "nonprofit", "education",
]

EMPLOYMENT_TYPES: dict[str, str] = {
    "freelance": "freelance", "freelancer": "freelance", "freelancers": "freelance",
    "contract": "contract", "contractor": "contract", "contractors": "contract",
    "full time": "full-time", "full-time": "full-time", "fulltime": "full-time",
    "part time": "part-time", "part-time": "part-time",
    "consultant": "contract", "consulting": "contract",
}

# Common English words that must never be treated as a skill/title token.
STOPWORDS: set[str] = {
    "find", "me", "a", "an", "the", "with", "in", "for", "of", "and", "or",
    "need", "needed", "looking", "look", "want", "wanted", "hire", "hiring",
    "seeking", "developer", "developers", "engineer", "engineers", "experience",
    "experienced", "years", "year", "who", "based", "located", "specializing",
    "specialized", "at", "on", "to", "from", "expert", "experts", "top",
    "great", "good", "strong", "some", "people", "person", "candidates",
    "profiles", "talent",
}
