import urllib.request
import urllib.parse
import json
import os
import sys
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import csv

# Configure standard encoding for outputs
sys.stdout.reconfigure(encoding='utf-8')

# Target path for output
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
CACHE_FILE = os.path.join(OUTPUT_DIR, "requirements_cache.json")

# Persistent cache for system requirements and translations
def load_requirements_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_requirements_cache(cache):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar cache: {e}", file=sys.stderr)

# Helper to fetch HTML/content, routing through ScraperAPI if SCRAPERAPI_KEY is available
def fetch_html(url, timeout=15):
    scraper_key = os.getenv("SCRAPERAPI_KEY")
    final_url = url
    if scraper_key:
        encoded_url = urllib.parse.quote(url)
        final_url = f"http://api.scraperapi.com?api_key={scraper_key}&url={encoded_url}"
        print(f"ScraperAPI: Roteando requisição para {url}")
        
    req = urllib.request.Request(
        final_url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception as e:
        print(f"Erro ao acessar {url} via ScraperAPI/direto: {e}", file=sys.stderr)
        if scraper_key:
            print(f"Tentando acesso direto alternativo para {url}...", file=sys.stderr)
            try:
                req_direct = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                )
                with urllib.request.urlopen(req_direct, timeout=timeout) as response:
                    return response.read()
            except Exception as ex:
                print(f"Acesso direto também falhou para {url}: {ex}", file=sys.stderr)
        raise e

# Load environment variables from .env file if it exists
def load_env_file():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    paths = [
        os.path.join(script_dir, ".env"),
        os.path.join(os.getcwd(), ".env")
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            parts = line.split("=", 1)
                            key = parts[0].strip()
                            value = parts[1].strip().strip('"').strip("'")
                            os.environ[key] = value
                print(f"Carregadas variáveis de ambiente de: {p}")
                return
            except Exception as e:
                print(f"Erro ao ler arquivo .env: {e}", file=sys.stderr)

TRANSLATION_CACHE = {}

def translate_to_pt(text):
    if not text:
        return ""
    text = text.strip()
    if not any(c.isalpha() for c in text):
        return text
        
    if text in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[text]
        
    encoded_text = urllib.parse.quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=pt-BR&dt=t&q={encoded_text}"
    
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode('utf-8'))
            translated_parts = []
            for part in res[0]:
                if part[0]:
                    translated_parts.append(part[0])
            translated = "".join(translated_parts)
            TRANSLATION_CACHE[text] = translated
            return translated
    except Exception as e:
        print(f"Erro no Google Translate: {e}. Tentando MyMemory...", file=sys.stderr)
        try:
            url_mymemory = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair=en|pt-BR"
            req_mm = urllib.request.Request(url_mymemory, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_mm, timeout=10) as response:
                res = json.loads(response.read().decode('utf-8'))
                translated = res.get('matches', [{}])[0].get('translation', text)
                TRANSLATION_CACHE[text] = translated
                return translated
        except Exception:
            pass
        return text

def is_text_english(text):
    text_lower = text.lower()
    en_words = [' the ', ' and ', ' of ', ' with ', ' for ', ' is ', ' on ', ' that ']
    pt_words = [' o ', ' a ', ' e ', ' com ', ' para ', ' é ', ' no ', ' na ', ' que ']
    en_count = sum(text_lower.count(w) for w in en_words)
    pt_count = sum(text_lower.count(w) for w in pt_words)
    return en_count > pt_count

def resolve_redirect(url):
    print(f"Resolvendo redirecionamento para: {url}...")
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
        method='HEAD'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.geturl()
    except Exception:
        try:
            req_get = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req_get, timeout=10) as response:
                return response.geturl()
        except Exception as ex:
            print(f"Erro ao resolver redirecionamento: {ex}", file=sys.stderr)
            return url

def get_steam_requirements(app_id):
    print(f"Buscando requisitos do Steam para o App ID: {app_id}...")
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=portuguese"
    try:
        html = fetch_html(url, timeout=10)
        data = json.loads(html.decode('utf-8'))
        app_data = data.get(str(app_id), {})
        if app_data.get('success'):
            pc_req = app_data.get('data', {}).get('pc_requirements', {})
            minimum_html = ""
            if isinstance(pc_req, dict):
                minimum_html = pc_req.get('minimum', '')
            if minimum_html:
                soup = BeautifulSoup(minimum_html, 'html.parser')
                clean_text = soup.get_text('\n')
                lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
                return "\n".join(lines)
    except Exception as e:
        print(f"Erro ao buscar requisitos do Steam para {app_id}: {e}", file=sys.stderr)
    return None

def search_serper(query):
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return []
    
    print(f"Buscando no Serper (Google) por: '{query}'...")
    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    data = json.dumps({"q": query, "num": 10}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    links = []
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            organic = res_data.get('organic', [])
            for item in organic:
                title = item.get('title')
                link = item.get('link')
                if title and link:
                    links.append({'title': title.strip(), 'url': link, 'source': 'Serper (Google)'})
    except Exception as e:
        print(f"Erro ao buscar no Serper: {e}", file=sys.stderr)
        
    return links

def enrich_game_requirements_and_translation(game, req_cache):
    # 1. Translation
    if game.get('platform') not in ['Epic Games', 'Amazon Luna']:
        game['title'] = translate_to_pt(game['title'])
        game['description'] = translate_to_pt(game['description'])
    else:
        desc = game.get('description', '')
        if desc and is_text_english(desc):
            game['description'] = translate_to_pt(desc)
            
    # 2. Resolve Steam App ID and Requirements
    url = game.get('url', '')
    resolved_url = url
    
    # Check cache first for resolved URL
    if url in req_cache and 'resolved_url' in req_cache[url]:
        resolved_url = req_cache[url]['resolved_url']
    elif 'gamerpower.com/open/' in url:
        resolved_url = resolve_redirect(url)
        req_cache[url] = req_cache.get(url, {})
        req_cache[url]['resolved_url'] = resolved_url
        
    # Check if resolved URL is Steam
    app_id = None
    steam_match = re.search(r'store\.steampowered\.com/app/(\d+)', resolved_url)
    if steam_match:
        app_id = steam_match.group(1)
        
    if app_id:
        reqs = None
        if url in req_cache and 'requirements' in req_cache[url]:
            reqs = req_cache[url]['requirements']
        elif app_id in req_cache:
            reqs = req_cache[app_id]
        else:
            reqs = get_steam_requirements(app_id)
            req_cache[url] = req_cache.get(url, {})
            req_cache[url]['requirements'] = reqs
            req_cache[app_id] = reqs
            
        if reqs:
            game['requirements'] = reqs

# Google search scraping
def search_google(query):
    print(f"Buscando no Google por: '{query}'...")
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded_query}&num=10"
    links = []
    
    try:
        html = fetch_html(url, timeout=15)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Select <a> containing <h3> (modern desktop layout)
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href', '')
            h3 = a_tag.find('h3')
            if h3 and href.startswith('http') and not any(x in href for x in ['google.com', 'youtube.com']):
                title = h3.get_text()
                if title:
                    links.append({'title': title.strip(), 'url': href, 'source': 'Google'})
                    
        # Select /url?q= (simple desktop/mobile layout fallback)
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href', '')
            if href.startswith('/url?q='):
                actual_url = href.split('/url?q=')[1].split('&')[0]
                actual_url = urllib.parse.unquote(actual_url)
                if actual_url.startswith('http') and not any(x in actual_url for x in ['google.com', 'youtube.com', 'gstatic.com']):
                    h3 = a_tag.find('h3')
                    title = h3.get_text() if h3 else a_tag.get_text()
                    if title and len(title.strip()) > 3:
                        links.append({'title': title.strip(), 'url': actual_url, 'source': 'Google'})
                        
    except Exception as e:
        print(f"Erro ao buscar no Google: {e}", file=sys.stderr)
        
    return links

def search_bing(query):
    print(f"Buscando no Bing por: '{query}'...")
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.bing.com/search?q={encoded_query}"
    links = []
    
    try:
        html = fetch_html(url, timeout=15)
        soup = BeautifulSoup(html, 'html.parser')
        
        for li in soup.find_all('li', class_='b_algo'):
            h2 = li.find('h2')
            if h2:
                a_tag = h2.find('a')
                if a_tag and a_tag.get('href'):
                    href = a_tag['href']
                    title = a_tag.get_text()
                    if href.startswith('http') and not any(x in href for x in ['bing.com', 'microsoft.com', 'msn.com']):
                        links.append({'title': title.strip(), 'url': href, 'source': 'Bing'})
                        
    except Exception as e:
        print(f"Erro ao buscar no Bing: {e}", file=sys.stderr)
        
    return links

def search_ddg(query):
    print(f"Buscando no DuckDuckGo (Bing/Web) por: '{query}'...")
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    links = []
    
    try:
        html = fetch_html(url, timeout=15)
        soup = BeautifulSoup(html, 'html.parser')
        
        for result_div in soup.find_all('div', class_='result__body'):
            link_elem = result_div.find('a', class_='result__link')
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                
                if '/l/?' in href:
                    parsed = urllib.parse.urlparse(href)
                    params = urllib.parse.parse_qs(parsed.query)
                    if 'uddg' in params:
                        href = params['uddg'][0]
                        
                if 'duckduckgo.com' in href or 'bing.com/aclick' in href:
                    continue
                    
                title = link_elem.get_text().strip()
                links.append({'title': title, 'url': href, 'source': 'Google/Bing'})
    except Exception as e:
        print(f"Erro ao buscar no DuckDuckGo: {e}", file=sys.stderr)
        
    return links

def search_yahoo(query):
    print(f"Buscando no Yahoo (Bing/Web) por: '{query}'...")
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://search.yahoo.com/search?q={encoded_query}"
    links = []
    
    def clean_yahoo_url(raw_url):
        if 'RU=' in raw_url:
            try:
                part = raw_url.split('RU=')[1].split('/')[0]
                return urllib.parse.unquote(part)
            except Exception:
                pass
        return raw_url
        
    try:
        html = fetch_html(url, timeout=15)
        soup = BeautifulSoup(html, 'html.parser')
        
        for h3 in soup.find_all('h3'):
            classes = h3.get('class', [])
            if classes and 'title' in classes:
                a_tag = h3.find_parent('a')
                if not a_tag:
                    a_tag = h3.find('a')
                    
                if a_tag and a_tag.get('href'):
                    raw_href = a_tag['href']
                    clean_href = clean_yahoo_url(raw_href)
                    title = h3.get_text().strip()
                    links.append({'title': title, 'url': clean_href, 'source': 'Google/Bing'})
    except Exception as e:
        print(f"Erro ao buscar no Yahoo: {e}", file=sys.stderr)
        
    return links

# Load indexed links history
def load_history():
    history_file = os.path.join(OUTPUT_DIR, "games.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"search_links": []}

# Save indexed links history
def save_history(history):
    history_file = os.path.join(OUTPUT_DIR, "games.json")
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar histórico de jogos: {e}", file=sys.stderr)

# Run indexing web search
def index_web_search():
    queries = [
        "\"jogos gratis\" PC site:steampowered.com OR site:epicgames.com OR site:gog.com",
        "site:store.steampowered.com/app/ \"100% off\" OR \"free to keep\"",
        "jogos gratis pc hoje"
    ]
    
    # Load env variables (including SERPER_API_KEY)
    load_env_file()
    
    all_links = []
    for q in queries:
        # Try Serper first if key is present
        serper_links = search_serper(q)
        if serper_links:
            all_links.extend(serper_links)
            
        # Also run scrapers as fallback/supplement
        all_links.extend(search_google(q))
        all_links.extend(search_bing(q))
        all_links.extend(search_ddg(q))
        all_links.extend(search_yahoo(q))
        
    unique_links = {}
    today_str = datetime.now().strftime("%d/%m/%Y")
    
    for item in all_links:
        url = item['url']
        if "?" in url:
            url = url.split("?")[0]
        url = url.strip().rstrip('/')
            
        domain = urllib.parse.urlparse(url).netloc.lower()
        if any(x in domain for x in ['google', 'bing', 'microsoft', 'youtube', 'facebook', 'twitter', 'instagram', 'github', 'wikipedia', 'duckduckgo', 'yahoo']):
            continue
            
        title = item['title'].replace(" - Google Search", "").replace(" - Bing", "").strip()
        if len(title) < 5 or title.lower() in ["shopping", "imagens", "vídeos", "notícias"]:
            continue
            
        if url not in unique_links:
            unique_links[url] = {
                'title': title,
                'url': url,
                'source': item['source'],
                'discovered_at': today_str
            }
            
    return list(unique_links.values())

# Update indexed history and return the list
def update_search_history(new_links):
    history = load_history()
    existing_links = history.get('search_links', [])
    existing_urls = {item['url']: item for item in existing_links}
    
    added_count = 0
    for link in new_links:
        url = link['url']
        if url not in existing_urls:
            existing_links.insert(0, link)
            added_count += 1
            
    existing_links = existing_links[:50]
    history['search_links'] = existing_links
    history['last_update'] = datetime.now().isoformat()
    
    save_history(history)
    print(f"Indexação Web: Adicionados {added_count} novos links. Total no índice: {len(existing_links)}.")
    return existing_links


# HTTP Request helper with User-Agent
def fetch_url_json(url):
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching URL {url}: {e}", file=sys.stderr)
        return None

# Helper to extract correct store slug from Epic Games product elements
def extract_epic_slug(el):
    # 1. Try to get pageSlug from catalogNs mappings (usually the most accurate)
    mappings = el.get('catalogNs', {}).get('mappings', [])
    if mappings:
        for m in mappings:
            page_slug = m.get('pageSlug')
            if page_slug:
                return page_slug
                
    # 2. Try productSlug
    prod_slug = el.get('productSlug')
    if prod_slug:
        if prod_slug.endswith('/home'):
            prod_slug = prod_slug[:-5]
        return prod_slug
        
    # 3. Try urlSlug (if it is not a 32-character hexadecimal hash)
    url_slug = el.get('urlSlug')
    if url_slug:
        if re.match(r'^[a-fA-F0-9]{32}$', url_slug):
            pass
        else:
            if url_slug.endswith('/home'):
                url_slug = url_slug[:-5]
            return url_slug
            
    return None

# Fetch from Amazon Prime Gaming Claims (via Reddit RSS & local JSON)
def get_luna_games():
    print("Fetching Amazon Prime Gaming claimable games...")
    games = []
    
    # 1. Load from local prime_games.json if exists (for manual additions/overrides)
    local_file = os.path.join(OUTPUT_DIR, "prime_games.json")
    if os.path.exists(local_file):
        try:
            with open(local_file, "r", encoding="utf-8") as f:
                manual_games = json.load(f)
                if isinstance(manual_games, list):
                    print(f"Loaded {len(manual_games)} manual Prime Gaming games from local file.")
                    games.extend(manual_games)
        except Exception as e:
            print(f"Erro ao ler prime_games.json: {e}", file=sys.stderr)
            
    # 2. Fetch from Reddit RSS feed (r/FreeGameFindings)
    url = "https://www.reddit.com/r/FreeGameFindings/search.rss?q=complimentary+with+Amazon+Prime&restrict_sr=on&sort=new&t=all"
    req = urllib.request.Request(url, headers={'User-Agent': 'FreeGamesMonitorBot/1.0'})
    reddit_count = 0
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            xml_data = r.read()
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('.//atom:entry', ns)
        
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # Track seen titles to avoid duplicates within Reddit or manual list
        seen_titles = {g['title'].lower() for g in games}
        
        for entry in entries:
            title = entry.find('atom:title', ns).text
            updated_str = entry.find('atom:updated', ns).text
            try:
                # First 10 chars is YYYY-MM-DD
                updated_date = datetime.strptime(updated_str[:10], "%Y-%m-%d")
            except Exception:
                updated_date = now
                
            if updated_date < thirty_days_ago:
                continue
                
            # Parse games from the title
            clean_title = re.sub(r'^\[PSA\]\s*', '', title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\s+(is|are)\s+complimentary\s+with\s+Amazon\s+Prime.*$', '', clean_title, flags=re.IGNORECASE)
            matches = re.findall(r'([^,]+?)\s*\(([^)]+)\)', clean_title)
            
            for name, platform in matches:
                name = name.strip()
                if name.lower().startswith('and '):
                    name = name[4:].strip()
                platform = platform.strip()
                
                # Normalize platform names
                p_lower = platform.lower()
                if 'gog' in p_lower:
                    plat_display = 'Prime Gaming (GOG)'
                elif 'epic' in p_lower or 'egs' in p_lower:
                    plat_display = 'Prime Gaming (Epic)'
                elif 'amazon' in p_lower:
                    plat_display = 'Prime Gaming (Amazon)'
                elif 'legacy' in p_lower:
                    plat_display = 'Prime Gaming (Legacy)'
                else:
                    plat_display = f'Prime Gaming ({platform})'
                    
                title_lower = name.lower()
                if title_lower not in seen_titles:
                    seen_titles.add(title_lower)
                    games.append({
                        'title': name,
                        'description': "Jogo disponível para resgate no Prime Gaming. IMPORTANTE: É imprescindível ser assinante do Amazon Prime para resgatar e jogar.",
                        'image': 'https://images.unsplash.com/photo-1612287230202-1bf1d85d1bdf?q=80&w=600&auto=format&fit=crop',
                        'url': 'https://luna.amazon.com/claims/home',
                        'original_price': 'Incluído no Prime',
                        'platform': plat_display,
                        'end_date': 'Verifique no site',
                        'type': 'Jogo'
                    })
                    reddit_count += 1
        print(f"Parsed {reddit_count} claimable Prime Gaming games from Reddit.")
    except Exception as e:
        print(f"Erro ao buscar resgates do Prime no Reddit: {e}", file=sys.stderr)
        
    return games

# Fetch from Epic Games Store
def get_epic_games():
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=pt-BR&country=BR&allowCountries=BR"
    data = fetch_url_json(url)
    if not data:
        return [], []
    
    current_free = []
    upcoming_free = []
    
    try:
        elements = data['data']['Catalog']['searchStore']['elements']
        for el in elements:
            title = el.get('title')
            # Check if there is any promotions object
            promotions = el.get('promotions')
            if not promotions:
                continue
                
            # Find image
            image_url = None
            key_images = el.get('keyImages', [])
            for img in key_images:
                if img.get('type') in ['Thumbnail', 'DieselStoreFrontWide', 'OfferImageWide']:
                    image_url = img.get('url')
                    break
            if not image_url and key_images:
                image_url = key_images[0].get('url')
            
            # Construct product URL
            slug = extract_epic_slug(el)
            product_url = f"https://store.epicgames.com/pt-BR/p/{slug}" if slug else "https://store.epicgames.com/pt-BR/free-games"
            
            original_price = "Grátis"
            price_info = el.get('price', {}).get('totalPrice', {})
            if price_info:
                fmt_original = price_info.get('fmtPrice', {}).get('originalPrice')
                if fmt_original and fmt_original != "0":
                    original_price = fmt_original

            # Verify promotional offers
            promo_offers = promotions.get('promotionalOffers', [])
            upcoming_offers = promotions.get('upcomingPromotionalOffers', [])
            
            # Helper to check if discount is 100% (free)
            def is_free_offer(offer):
                discount_setting = offer.get('discountSetting', {})
                # Some are PERCENTAGE 0 (meaning 100% off, paying 0) or discountValue 0
                return discount_setting.get('discountType') == 'PERCENTAGE' and discount_setting.get('discountPercentage') == 0

            # Process active promotions
            is_active = False
            for promo in promo_offers:
                for offer in promo.get('promotionalOffers', []):
                    if is_free_offer(offer):
                        start_str = offer.get('startDate')
                        end_str = offer.get('endDate')
                        # Parse dates (UTC)
                        start_date = datetime.strptime(start_str[:19], "%Y-%m-%dT%H:%M:%S")
                        end_date = datetime.strptime(end_str[:19], "%Y-%m-%dT%H:%M:%S")
                        now = datetime.utcnow()
                        
                        if start_date <= now <= end_date:
                            is_active = True
                            current_free.append({
                                'title': title,
                                'description': el.get('description', 'Sem descrição disponível.'),
                                'image': image_url,
                                'url': product_url,
                                'original_price': original_price,
                                'platform': 'Epic Games',
                                'end_date': end_date.strftime("%d/%m/%Y às %H:%M (UTC)"),
                                'type': 'Jogo'
                            })
                            break
                if is_active:
                    break
            
            # Process upcoming promotions if not already active
            if not is_active:
                for promo in upcoming_offers:
                    for offer in promo.get('promotionalOffers', []):
                        if is_free_offer(offer):
                            start_str = offer.get('startDate')
                            end_str = offer.get('endDate')
                            start_date = datetime.strptime(start_str[:19], "%Y-%m-%dT%H:%M:%S")
                            end_date = datetime.strptime(end_str[:19], "%Y-%m-%dT%H:%M:%S")
                            
                            upcoming_free.append({
                                'title': title,
                                'description': el.get('description', 'Sem descrição disponível.'),
                                'image': image_url,
                                'url': product_url,
                                'original_price': original_price,
                                'platform': 'Epic Games',
                                'start_date': start_date.strftime("%d/%m/%Y às %H:%M (UTC)"),
                                'end_date': end_date.strftime("%d/%m/%Y às %H:%M (UTC)"),
                                'type': 'Jogo'
                            })
                            break
    except Exception as e:
        print(f"Error parsing Epic Games JSON: {e}", file=sys.stderr)
        
    return current_free, upcoming_free

# Fetch from GamerPower API
def get_gamerpower_giveaways(existing_titles):
    url = "https://www.gamerpower.com/api/giveaways?platform=pc"
    data = fetch_url_json(url)
    if not data:
        return []
    
    giveaways = []
    try:
        for item in data:
            title = item.get('title')
            # Clean title for duplicate matching
            clean_title = title.lower().replace("giveaway", "").replace("free", "").strip()
            
            # Skip if already found in Epic Games to avoid duplicates
            is_dup = False
            for existing in existing_titles:
                if existing.lower() in clean_title or clean_title in existing.lower():
                    is_dup = True
                    break
            if is_dup:
                continue
                
            platform = item.get('platforms', 'PC')
            # Map platform names to cleaner tags
            if 'epic' in platform.lower():
                platform_tag = 'Epic Games'
            elif 'steam' in platform.lower():
                platform_tag = 'Steam'
            elif 'gog' in platform.lower():
                platform_tag = 'GOG'
            elif 'itch' in platform.lower():
                platform_tag = 'Itch.io'
            elif 'ubisoft' in platform.lower() or 'uplay' in platform.lower():
                platform_tag = 'Ubisoft'
            else:
                platform_tag = platform
                
            worth = item.get('worth', 'N/A')
            giveaway_type = 'Jogo'
            if item.get('type') != 'Game':
                giveaway_type = 'DLC / Extra'
                
            end_date = item.get('end_date')
            if not end_date or end_date == 'N/A':
                end_date = "Enquanto durarem os estoques"
            
            giveaways.append({
                'title': title,
                'description': item.get('description', 'Sem descrição disponível.'),
                'image': item.get('image') or item.get('thumbnail'),
                'url': item.get('open_giveaway_url'),
                'original_price': worth,
                'platform': platform_tag,
                'end_date': end_date,
                'type': giveaway_type
            })
    except Exception as e:
        print(f"Error parsing GamerPower JSON: {e}", file=sys.stderr)
        
    return giveaways

# Generate static HTML file
def generate_html(current_games, upcoming_games, web_search_links):
    now_str = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor de Jogos Grátis</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <!-- FontAwesome for Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    
    <style>
        :root {{
            --bg-color: #0f111a;
            --card-bg: rgba(30, 33, 50, 0.4);
            --border-color: rgba(255, 255, 255, 0.08);
            --accent-primary: #7c4dff;
            --accent-secondary: #00e5ff;
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            
            --steam-gradient: linear-gradient(135deg, #171a21 0%, #1b2838 100%);
            --epic-gradient: linear-gradient(135deg, #2a2a2a 0%, #121212 100%);
            --gog-gradient: linear-gradient(135deg, #2b0c3d 0%, #1c0628 100%);
            --itch-gradient: linear-gradient(135deg, #ff2449 0%, #b8001f 100%);
            --generic-gradient: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            min-height: 100vh;
            background-image: 
                radial-gradient(at 0% 0%, rgba(124, 77, 255, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(0, 229, 255, 0.1) 0px, transparent 50%);
            background-attachment: fixed;
            padding: 2rem 1rem;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 3rem;
            position: relative;
        }}

        h1 {{
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(to right, var(--text-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -0.05em;
        }}

        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
            margin-bottom: 1.5rem;
        }}

        .last-update {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(255, 255, 255, 0.05);
            padding: 0.5rem 1rem;
            border-radius: 50px;
            font-size: 0.85rem;
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
            backdrop-filter: blur(10px);
        }}

        .last-update i {{
            color: var(--accent-secondary);
        }}

        /* Control Panel */
        .controls {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            background: rgba(255, 255, 255, 0.02);
            padding: 1rem;
            border-radius: 16px;
            border: 1px solid var(--border-color);
            backdrop-filter: blur(10px);
            margin-bottom: 2.5rem;
        }}

        .filter-buttons {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}

        .filter-btn {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.5rem 1.2rem;
            border-radius: 8px;
            cursor: pointer;
            font-family: inherit;
            font-weight: 600;
            font-size: 0.9rem;
            transition: all 0.2s ease;
        }}

        .filter-btn:hover {{
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-1px);
        }}

        .filter-btn.active {{
            background: var(--accent-primary);
            border-color: var(--accent-primary);
            box-shadow: 0 0 15px rgba(124, 77, 255, 0.4);
        }}

        .search-box {{
            position: relative;
            min-width: 280px;
        }}

        .search-box i {{
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}

        .search-input {{
            width: 100%;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.6rem 1rem 0.6rem 2.5rem;
            border-radius: 8px;
            font-family: inherit;
            font-size: 0.95rem;
            outline: none;
            transition: all 0.2s ease;
        }}

        .type-select {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.55rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            font-family: inherit;
            font-weight: 600;
            font-size: 0.9rem;
            outline: none;
            transition: all 0.2s ease;
            -webkit-appearance: none;
            -moz-appearance: none;
            appearance: none;
            background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
            background-repeat: no-repeat;
            background-position: right 0.8rem center;
            background-size: 1em;
            padding-right: 2.2rem;
        }}

        .type-select:focus {{
            border-color: var(--accent-secondary);
            background-color: rgba(255, 255, 255, 0.08);
            box-shadow: 0 0 10px rgba(0, 229, 255, 0.15);
        }}

        .type-select option {{
            background: #1e2132;
            color: var(--text-primary);
        }}

        /* Sections */
        .section-title {{
            font-size: 1.8rem;
            font-weight: 800;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .section-title i {{
            color: var(--accent-primary);
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 2rem;
            margin-bottom: 4rem;
        }}

        /* Game Card */
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            backdrop-filter: blur(12px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
        }}

        .card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: transparent;
            transition: background 0.3s;
        }}

        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 25px rgba(0, 0, 0, 0.4);
            border-color: rgba(255, 255, 255, 0.15);
        }}

        .card:hover::before {{
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
        }}

        .image-container {{
            position: relative;
            width: 100%;
            height: 180px;
            background: #161925;
            overflow: hidden;
        }}

        .image-container img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.5s ease;
        }}

        .card:hover .image-container img {{
            transform: scale(1.05);
        }}

        .platform-badge {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            color: #fff;
        }}

        .platform-badge.steam {{ background: var(--steam-gradient); }}
        .platform-badge.epic-games {{ background: var(--epic-gradient); }}
        .platform-badge.gog {{ background: var(--gog-gradient); }}
        .platform-badge.itch-io {{ background: var(--itch-gradient); }}
        .platform-badge.others {{ background: var(--generic-gradient); }}

        .type-badge {{
            position: absolute;
            top: 1rem;
            left: 1rem;
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 800;
            background: rgba(15, 17, 26, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            backdrop-filter: blur(5px);
        }}

        .content {{
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }}

        .title {{
            font-size: 1.25rem;
            font-weight: 700;
            line-height: 1.3;
            margin-bottom: 0.75rem;
            min-height: 2.6rem;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        .description {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            line-height: 1.5;
            margin-bottom: 1.5rem;
            flex-grow: 1;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            min-height: 4rem;
        }}

        .meta-info {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--border-color);
            padding-top: 1rem;
            margin-bottom: 1.2rem;
            font-size: 0.85rem;
        }}

        .original-price {{
            text-decoration: line-through;
            color: var(--text-secondary);
            font-weight: 600;
        }}

        .price-badge {{
            background: rgba(0, 229, 255, 0.12);
            color: var(--accent-secondary);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-weight: 700;
        }}

        .duration {{
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }}

        .action-button {{
            width: 100%;
            background: linear-gradient(135deg, var(--accent-primary) 0%, #512da8 100%);
            color: #fff;
            border: none;
            padding: 0.75rem;
            border-radius: 10px;
            font-weight: 700;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            box-shadow: 0 4px 15px rgba(124, 77, 255, 0.2);
        }}

        .action-button:hover {{
            background: linear-gradient(135deg, #9575cd 0%, var(--accent-primary) 100%);
            box-shadow: 0 6px 20px rgba(124, 77, 255, 0.4);
            transform: translateY(-1px);
        }}

        .action-button.upcoming {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            cursor: not-allowed;
            box-shadow: none;
        }}

        .action-button.upcoming:hover {{
            transform: none;
            box-shadow: none;
        }}

        /* Empty State */
        .empty-state {{
            grid-column: 1 / -1;
            text-align: center;
            padding: 4rem 2rem;
            background: rgba(255, 255, 255, 0.01);
            border: 1px dashed var(--border-color);
            border-radius: 16px;
        }}

        .empty-state i {{
            font-size: 3rem;
            color: var(--text-secondary);
            margin-bottom: 1rem;
        }}

        .empty-state p {{
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}

        /* Footer */
        footer {{
            text-align: center;
            padding-top: 2rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}

        footer a {{
            color: var(--accent-secondary);
            text-decoration: none;
            font-weight: 600;
        }}

        footer a:hover {{
            text-decoration: underline;
        }}

        /* Web Search Links Section */
        .web-links-list {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 1rem;
            margin-bottom: 2.5rem;
        }}

        @media (min-width: 768px) {{
            .web-links-list {{
                grid-template-columns: 1fr 1fr;
            }}
        }}

        .web-link-card {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.2rem;
            backdrop-filter: blur(10px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}

        .web-link-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 3px;
            height: 100%;
            background: linear-gradient(180deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
            opacity: 0.8;
        }}

        .web-link-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(0, 229, 255, 0.3);
            background: rgba(30, 33, 50, 0.6);
            box-shadow: 0 10px 20px -10px rgba(0, 229, 255, 0.15);
        }}

        .web-link-details {{
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            padding-right: 1rem;
            flex: 1;
        }}

        .web-link-title {{
            font-size: 1.05rem;
            font-weight: 600;
            color: var(--text-primary);
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        .web-link-meta {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            align-items: center;
        }}

        .web-link-meta span {{
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }}

        .web-link-meta span i {{
            color: var(--accent-secondary);
        }}

        .web-link-meta .source-badge {{
            background: rgba(124, 77, 255, 0.15);
            color: #d1c4e9;
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            border: 1px solid rgba(124, 77, 255, 0.3);
        }}

        .web-link-meta .source-badge.bing {{
            background: rgba(0, 229, 255, 0.1);
            color: #b2ebf2;
            border-color: rgba(0, 229, 255, 0.2);
        }}

        .web-link-btn {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.6rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            white-space: nowrap;
        }}

        .web-link-btn:hover {{
            background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
            border-color: transparent;
            color: #0f111a;
            box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
        }}

        /* Responsive adjustments */
        @media (max-width: 768px) {{
            h1 {{ font-size: 2.2rem; }}
            .controls {{ flex-direction: column; align-items: stretch; }}
            .search-box {{ min-width: 100%; }}
        }}

        /* Collapsible Requirements styling */
        .requirements-details {{
            margin-top: 1rem;
            border-top: 1px dashed var(--border-color);
            padding-top: 0.8rem;
        }}

        .requirements-summary {{
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--accent-secondary);
            cursor: pointer;
            list-style: none;
            display: flex;
            align-items: center;
            gap: 0.35rem;
            outline: none;
            user-select: none;
            transition: color 0.2s;
        }}

        .requirements-summary:hover {{
            color: var(--text-primary);
        }}

        .requirements-summary::-webkit-details-marker {{
            display: none;
        }}

        .requirements-summary::after {{
            content: '\\f107'; /* Chevron down */
            font-family: 'Font Awesome 6 Free';
            font-weight: 900;
            margin-left: auto;
            font-size: 0.8rem;
            transition: transform 0.2s ease;
        }}

        .requirements-details[open] .requirements-summary::after {{
            transform: rotate(180deg);
        }}

        .requirements-content {{
            margin-top: 0.6rem;
            font-size: 0.8rem;
            color: var(--text-secondary);
            line-height: 1.4;
            background: rgba(255, 255, 255, 0.02);
            padding: 0.8rem;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            white-space: pre-line;
            max-height: 200px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>

    <div class="container">
        <header>
            <h1><i class="fa-solid fa-gamepad"></i> Monitor de Jogos Grátis</h1>
            <p class="subtitle">Encontre e resgate as melhores ofertas de jogos gratuitos da atualidade</p>
            <div class="last-update">
                <i class="fa-solid fa-arrows-rotate"></i>
                Última atualização: <span>{now_str}</span>
            </div>
        </header>

        <div class="controls">
            <div class="filter-buttons">
                <button class="filter-btn active" onclick="filterPlatform('all')">Todos</button>
                <button class="filter-btn" onclick="filterPlatform('steam')"><i class="fa-brands fa-steam"></i> Steam</button>
                <button class="filter-btn" onclick="filterPlatform('epic games')"><i class="fa-solid fa-circle"></i> Epic Games</button>
                <button class="filter-btn" onclick="filterPlatform('gog')"><i class="fa-solid fa-g"></i> GOG</button>
                <button class="filter-btn" onclick="filterPlatform('others')">Outros</button>
            </div>
            <div style="display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; flex-grow: 1; justify-content: flex-end;">
                <select class="type-select" id="type-select" onchange="filterType()">
                    <option value="all">Todos os Tipos</option>
                    <option value="jogo" selected>Apenas Jogos</option>
                    <option value="dlc">Apenas DLCs & Extras</option>
                </select>
                <div class="search-box">
                    <i class="fa-solid fa-magnifying-glass"></i>
                    <input type="text" class="search-input" id="search-input" placeholder="Pesquisar jogo..." oninput="filterSearch()">
                </div>
            </div>
        </div>

        <main>
            <!-- JOGOS DISPONÍVEIS AGORA -->
            <section>
                <h2 class="section-title"><i class="fa-solid fa-fire"></i> Disponíveis Agora</h2>
                <div class="grid" id="active-grid">
        """
        
    if not current_games:
        html_content += """
                    <div class="empty-state">
                        <i class="fa-solid fa-face-frown"></i>
                        <p>Nenhum jogo gratuito disponível no momento. Volte mais tarde!</p>
                    </div>
        """
    else:
        for game in current_games:
            platform_class = game['platform'].lower().replace(" ", "-")
            if platform_class not in ['steam', 'epic-games', 'gog', 'itch-io']:
                platform_class = 'others'
                
            original_price = game['original_price']
            price_display = f'<span class="original-price">{original_price}</span> <span class="price-badge">Grátis</span>'
            
            image_url = game['image'] or 'https://images.unsplash.com/photo-1538481199705-c710c4e965fc?q=80&w=600&auto=format&fit=crop'
            
            reqs_html = ""
            if game.get('requirements'):
                reqs_html = f"""
                            <details class="requirements-details">
                                <summary class="requirements-summary"><i class="fa-solid fa-microchip"></i> Requisitos Mínimos</summary>
                                <div class="requirements-content">{game['requirements']}</div>
                            </details>
                """

            html_content += f"""
                    <div class="card" data-platform="{game['platform'].lower()}" data-title="{game['title'].lower()}" data-type="{game.get('type', 'Jogo').lower()}">
                        <div class="image-container">
                            <img src="{image_url}" alt="{game['title']}">
                            <div class="platform-badge {platform_class}">
                                <i class="{get_platform_icon(game['platform'])}"></i> {game['platform']}
                            </div>
                            <div class="type-badge">{game['type']}</div>
                        </div>
                        <div class="content">
                            <h3 class="title">{game['title']}</h3>
                            <p class="description">{game['description']}</p>
                            <div class="meta-info">
                                <div class="price">
                                    {price_display}
                                </div>
                                <div class="duration" title="Disponível até">
                                    <i class="fa-solid fa-clock"></i> <span>{game['end_date']}</span>
                                </div>
                            </div>
                            {reqs_html}
                            <a href="{game['url']}" target="_blank" class="action-button" style="margin-top: 1rem;">
                                <i class="fa-solid fa-download"></i> Resgatar Jogo
                            </a>
                        </div>
                    </div>
            """
            
    html_content += """
                </div>
            </section>

            <!-- LINKS INDEXADOS VIA WEB SEARCH -->
            <section>
                <h2 class="section-title"><i class="fa-solid fa-globe"></i> Links Indexados da Web (Google & Bing)</h2>
                <div class="web-links-list">
    """
    
    if not web_search_links:
        html_content += """
                    <div class="empty-state" style="grid-column: 1 / -1;">
                        <i class="fa-solid fa-circle-notch fa-spin"></i>
                        <p>Nenhum link indexado por busca na web ainda. Aguardando a próxima execução das 13:01.</p>
                    </div>
        """
    else:
        for link in web_search_links:
            source_class = "bing" if link['source'].lower() == 'bing' else "google"
            html_content += f"""
                    <div class="web-link-card">
                        <div class="web-link-details">
                            <div class="web-link-title" title="{link['title']}">{link['title']}</div>
                            <div class="web-link-meta">
                                <span class="source-badge {source_class}">
                                    <i class="fa-solid fa-magnifying-glass"></i> {link['source']}
                                </span>
                                <span><i class="fa-solid fa-calendar-days"></i> Indexado: {link['discovered_at']}</span>
                            </div>
                        </div>
                        <a href="{link['url']}" target="_blank" class="web-link-btn">
                            <i class="fa-solid fa-arrow-up-right-from-square"></i> Acessar
                        </a>
                    </div>
            """
            
    html_content += """
                </div>
            </section>

            <!-- PRÓXIMOS JOGOS (EXCLUSIVOS EPIC) -->
            <section>
                <h2 class="section-title"><i class="fa-solid fa-calendar-days"></i> Em Breve (Próximos)</h2>
                <div class="grid" id="upcoming-grid">
    """
    
    if not upcoming_games:
        html_content += """
                    <div class="empty-state">
                        <i class="fa-solid fa-circle-info"></i>
                        <p>Nenhuma promoção agendada para os próximos dias.</p>
                    </div>
        """
    else:
        for game in upcoming_games:
            platform_class = game['platform'].lower().replace(" ", "-")
            if platform_class not in ['steam', 'epic-games', 'gog', 'itch-io']:
                platform_class = 'others'
                
            image_url = game['image'] or 'https://images.unsplash.com/photo-1538481199705-c710c4e965fc?q=80&w=600&auto=format&fit=crop'
            
            reqs_html = ""
            if game.get('requirements'):
                reqs_html = f"""
                            <details class="requirements-details">
                                <summary class="requirements-summary"><i class="fa-solid fa-microchip"></i> Requisitos Mínimos</summary>
                                <div class="requirements-content">{game['requirements']}</div>
                            </details>
                """

            html_content += f"""
                    <div class="card" data-platform="{game['platform'].lower()}" data-title="{game['title'].lower()}" data-type="{game.get('type', 'Jogo').lower()}">
                        <div class="image-container">
                            <img src="{image_url}" alt="{game['title']}">
                            <div class="platform-badge {platform_class}">
                                <i class="{get_platform_icon(game['platform'])}"></i> {game['platform']}
                            </div>
                            <div class="type-badge">{game['type']}</div>
                        </div>
                        <div class="content">
                            <h3 class="title">{game['title']}</h3>
                            <p class="description">{game['description']}</p>
                            <div class="meta-info" style="margin-bottom: 1.5rem;">
                                <div class="duration" style="width: 100%; justify-content: space-between;">
                                    <span><i class="fa-solid fa-calendar-play"></i> Inicia: {game['start_date']}</span>
                                </div>
                            </div>
                            {reqs_html}
                            <button class="action-button upcoming" disabled style="margin-top: 1rem;">
                                <i class="fa-solid fa-hourglass-start"></i> Indisponível ainda
                            </button>
                        </div>
                    </div>
            """
            
    html_content += """
                </div>
            </section>
        </main>

        <footer>
            <p>Criado por <a href="https://github.com/yuriluna85" target="_blank">Yuri Almeida</a> | <a href="https://github.com/yuriluna85/games-for-free" target="_blank"><i class="fa-brands fa-github"></i> Repositório do Projeto</a> | 2026</p>
        </footer>
    </div>

    <script>
        let currentFilter = 'all';
        let currentTypeFilter = 'jogo';

        function filterPlatform(platform) {
            currentFilter = platform;
            
            // Update active button state
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            const clickedBtn = Array.from(buttons).find(btn => 
                btn.textContent.toLowerCase().includes(platform) || 
                (platform === 'all' && btn.textContent.toLowerCase() === 'todos') ||
                (platform === 'others' && btn.textContent.toLowerCase() === 'outros')
            );
            if (clickedBtn) clickedBtn.classList.add('active');

            applyFilters();
        }

        function filterType() {
            currentTypeFilter = document.getElementById('type-select').value;
            applyFilters();
        }

        function filterSearch() {
            applyFilters();
        }

        function applyFilters() {
            const searchQuery = document.getElementById('search-input').value.toLowerCase();
            const cards = document.querySelectorAll('.card');

            cards.forEach(card => {
                const cardPlatform = card.getAttribute('data-platform');
                const cardTitle = card.getAttribute('data-title');
                const cardType = card.getAttribute('data-type') || 'jogo';
                
                let matchesPlatform = false;
                if (currentFilter === 'all') {
                    matchesPlatform = true;
                } else if (currentFilter === 'others') {
                    matchesPlatform = !['steam', 'epic games', 'gog'].includes(cardPlatform);
                } else {
                    matchesPlatform = cardPlatform === currentFilter;
                }

                let matchesType = false;
                if (currentTypeFilter === 'all') {
                    matchesType = true;
                } else if (currentTypeFilter === 'jogo') {
                    matchesType = cardType.includes('jogo');
                } else if (currentTypeFilter === 'dlc') {
                    matchesType = cardType.includes('dlc') || cardType.includes('extra');
                } else if (currentTypeFilter === 'nuvem') {
                    matchesType = cardType.includes('nuvem') || cardType.includes('cloud') || cardType.includes('jogar na nuvem');
                }

                const matchesSearch = cardTitle.includes(searchQuery);

                if (matchesPlatform && matchesType && matchesSearch) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });
        }

        // Aplicar filtros inicialmente ao carregar a página
        applyFilters();
    </script>
</body>
</html>
"""
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Successfully generated HTML Dashboard at: {OUTPUT_FILE}")

# Get FontAwesome/Bootstrap platform icons
def get_platform_icon(platform):
    p = platform.lower()
    if 'steam' in p:
        return 'fa-brands fa-steam'
    elif 'epic' in p:
        return 'fa-solid fa-circle'
    elif 'gog' in p:
        return 'fa-solid fa-g'
    elif 'itch' in p:
        return 'fa-brands fa-itch-io'
    elif 'playstation' in p:
        return 'fa-brands fa-playstation'
    elif 'xbox' in p:
        return 'fa-brands fa-xbox'
    elif 'luna' in p:
        return 'fa-solid fa-cloud'
    elif 'amazon' in p or 'prime' in p:
        return 'fa-brands fa-amazon'
    else:
        return 'fa-solid fa-gamepad'

# Generate CSV and JSON metrics
def generate_csv_and_metrics(current_games, upcoming_games, web_search_links):
    # 1. Generate CSV
    csv_file = os.path.join(OUTPUT_DIR, "games_data.csv")
    print(f"Gerando arquivo CSV em: {csv_file}...")
    try:
        with open(csv_file, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Source', 'Platform', 'Title', 'Type', 'Original Price', 'Start/Discovery Date', 'End Date', 'URL'])
            
            for g in current_games:
                writer.writerow([
                    'API (Ativo)',
                    g.get('platform', 'N/A'),
                    g.get('title', 'N/A'),
                    g.get('type', 'Jogo'),
                    g.get('original_price', 'Grátis'),
                    'Disponível',
                    g.get('end_date', 'N/A'),
                    g.get('url', 'N/A')
                ])
                
            for g in upcoming_games:
                writer.writerow([
                    'API (Agendado)',
                    g.get('platform', 'N/A'),
                    g.get('title', 'N/A'),
                    g.get('type', 'Jogo'),
                    g.get('original_price', 'Grátis'),
                    g.get('start_date', 'N/A'),
                    g.get('end_date', 'N/A'),
                    g.get('url', 'N/A')
                ])
                
            for l in web_search_links:
                writer.writerow([
                    f"Web Search ({l.get('source', 'Google/Bing')})",
                    'Múltiplas',
                    l.get('title', 'N/A'),
                    'Portal / Oferta',
                    'Grátis / Desconto',
                    l.get('discovered_at', 'N/A'),
                    'Enquanto durar o estoque',
                    l.get('url', 'N/A')
                ])
    except Exception as e:
        print(f"Erro ao salvar CSV: {e}", file=sys.stderr)

    # 2. Generate JSON Metrics
    metrics_file = os.path.join(OUTPUT_DIR, "games_metrics.json")
    print(f"Gerando métricas em: {metrics_file}...")
    try:
        platforms = {}
        for g in current_games:
            p = g.get('platform', 'Outros')
            platforms[p] = platforms.get(p, 0) + 1
            
        metrics = {
            "last_updated": datetime.now().isoformat(),
            "metrics": {
                "total_active_free_games": len(current_games),
                "total_upcoming_promotions": len(upcoming_games),
                "total_indexed_web_search_links": len(web_search_links),
                "total_records": len(current_games) + len(upcoming_games) + len(web_search_links)
            },
            "platform_distribution": platforms,
            "sources_scraped": {
                "epic_games_api": "OK",
                "gamerpower_api": "OK",
                "amazon_luna_api": "OK",
                "google_bing_search": "OK" if len(web_search_links) > 0 else "Sem novos links"
            }
        }
        
        with open(metrics_file, mode='w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar métricas JSON: {e}", file=sys.stderr)

def main():
    print("Starting Free Games Monitor...")
    
    # Load environment variables
    load_env_file()
    
    # 1. Fetch from Epic Games Store
    print("Fetching Epic Games Store promotions...")
    epic_current, epic_upcoming = get_epic_games()
    print(f"Found {len(epic_current)} active and {len(epic_upcoming)} upcoming Epic games.")
    
    # 2. Fetch from GamerPower (GOG, Steam, itch.io, etc.)
    # Exclude games we already found on Epic
    existing_titles = [g['title'] for g in epic_current] + [g['title'] for g in epic_upcoming]
    
    print("Fetching other PC giveaways from GamerPower...")
    other_games = get_gamerpower_giveaways(existing_titles)
    print(f"Found {len(other_games)} other giveaways after de-duplication.")
    
    # 2.5 Fetch from Amazon Prime Gaming Claims
    luna_games = get_luna_games()
    print(f"Found {len(luna_games)} Prime Gaming claimable games.")
    
    # 3. Combine active games
    all_current = epic_current + other_games + luna_games
    
    # Load requirements cache
    req_cache = load_requirements_cache()
    
    # Enrich current games with translation and requirements
    print("Traduzindo e buscando requisitos para os jogos atuais...")
    for game in all_current:
        enrich_game_requirements_and_translation(game, req_cache)
        
    # Enrich upcoming games
    print("Traduzindo e buscando requisitos para os jogos futuros...")
    for game in epic_upcoming:
        enrich_game_requirements_and_translation(game, req_cache)
        
    # Save requirements cache back to file
    save_requirements_cache(req_cache)
    
    # Sort games by platform and then by title
    all_current.sort(key=lambda x: (x['platform'], x['title']))
    epic_upcoming.sort(key=lambda x: x['title'])
    
    # 4. Web Search Indexation (Google & Bing)
    print("Running Google & Bing search indexation...")
    new_web_links = index_web_search()
    web_search_links = update_search_history(new_web_links)
    
    # 5. Generate HTML
    generate_html(all_current, epic_upcoming, web_search_links)
    
    # 6. Generate CSV and JSON Metrics
    generate_csv_and_metrics(all_current, epic_upcoming, web_search_links)
    
    print("Free Games Monitor execution completed.")

if __name__ == "__main__":
    main()
