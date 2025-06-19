from typing import Dict, Optional
from bs4 import BeautifulSoup

class ArticleExtractor:
    def __init__(self, html_content: str):
        self.html_content = html_content
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self._clean_html(self.soup)

    def _clean_html(self, soup: BeautifulSoup):
        # Remove unwanted elements (menus, nav, ads, etc.)
        unwanted_selectors = [
            "script", "style", "nav", "header", "footer", "aside", 
            "form", "button", "iframe", "noscript", "meta", "link",
            ".menu", ".navigation", ".nav", ".sidebar", ".widget",
            ".social", ".share", ".related", ".comments", ".comment",
            ".ads", ".advertisement", ".banner", ".popup",
            "#menu", "#navigation", "#nav", "#sidebar", "#social",
            "[class*='menu']", "[class*='nav']", "[class*='sidebar']",
            "[class*='widget']", "[class*='social']", "[class*='ad']"
        ]
        for selector in unwanted_selectors:
            for element in soup.select(selector):
                element.decompose()

    def get_title(self) -> Optional[str]:
        # Try og:title first
        og_title = self.soup.find('meta', attrs={'property': 'og:title'})
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        # Fallback to <title>
        title_tag = self.soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            return title.split(' - ')[0].split(' | ')[0].strip()
        # Fallback to <h1>
        h1_tag = self.soup.find('h1')
        if h1_tag:
            return h1_tag.get_text().strip()
        return None

    def get_description(self) -> Optional[str]:
        # Try og:description first
        og_desc = self.soup.find('meta', attrs={'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
        # Fallback to meta description
        meta_desc = self.soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        return None

    def get_main_content(self) -> Optional[str]:
        soup = self.soup
        content = ""
        content_found = False
        # Strategy 1: Main content selectors
        main_content_selectors = [
            'article', '[role="main"]', 'main', '.entry-content', '.post-content',
            '.article-content', '.article-body', '.content-area', '.post-body'
        ]
        for selector in main_content_selectors:
            try:
                content_elem = soup.select_one(selector)
                if content_elem:
                    for unwanted in content_elem.select('.menu, .nav, .sidebar, .widget, .social, .share, .ads, .related'):
                        unwanted.decompose()
                    content = content_elem.get_text(separator=' ', strip=True)
                    if len(content) > 200:
                        content_found = True
                        break
            except Exception:
                continue
        # Strategy 2: Substantial paragraphs
        if not content_found:
            paragraphs = soup.find_all('p')
            content_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if (len(text) > 50 and not any(skip_word in text.lower() for skip_word in [
                    'menu', 'navegação', 'compartilhar', 'redes sociais', 'copyright',
                    'todos os direitos', 'follow us', 'subscribe', 'newsletter', 'cookie'])):
                    content_parts.append(text)
            if content_parts:
                content = ' '.join(content_parts)
                content_found = True
        # Strategy 3: Longest div
        if not content_found:
            divs = soup.find_all('div')
            best_div_content = ""
            for div in divs:
                div_text = div.get_text(strip=True)
                if (200 < len(div_text) < 8000 and len(div_text) > len(best_div_content)):
                    if not any(skip_word in div_text.lower() for skip_word in [
                        'menu principal', 'navegação', 'todos os direitos', 'compartilhe',
                        'redes sociais', 'newsletter']):
                        best_div_content = div_text
            if best_div_content:
                content = best_div_content
                content_found = True
        # Fallback: title + description
        if not content_found or len(content) < 100:
            title = self.get_title()
            description = self.get_description()
            if title and description:
                content = f"{title}. {description}"
            elif title:
                content = title
        # Final cleanup
        content = ' '.join(content.split()) if content else ""
        navigation_phrases = [
            'home página inicial', 'menu principal', 'navegação',
            'compartilhe esta página', 'redes sociais', 'follow us',
            'todos os direitos reservados', 'copyright', 'newsletter',
            'assine nossa newsletter', 'receba atualizações'
        ]
        for phrase in navigation_phrases:
            content = content.replace(phrase, '')
        content = ' '.join(content.split())
        return content or None

    def get_favicon(self) -> Optional[str]:
        icon_link = self.soup.find('link', rel=lambda x: x and 'icon' in x)
        if icon_link and icon_link.get('href'):
            return icon_link['href']
        return None

    def extract_article_data(self) -> Dict[str, Optional[str]]:
        return {
            'title': self.get_title(),
            'description': self.get_description(),
            'content': self.get_main_content(),
            'favicon': self.get_favicon(),
        }
