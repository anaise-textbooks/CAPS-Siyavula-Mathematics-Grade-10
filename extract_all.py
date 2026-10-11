import os
import sys
import json
import re
import time
import urllib.request
import http.cookiejar
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup, NavigableString, Tag

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
MAX_WORKERS = 8

def get_opener():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    return opener

def fetch_html(url, opener=None, retries=3):
    if opener is None:
        opener = get_opener()
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    for attempt in range(retries):
        try:
            with opener.open(req, timeout=30) as resp:
                return resp.read().decode('utf-8')
        except Exception as e:
            if attempt == retries - 1:
                raise e
            time.sleep(1.5 * (attempt + 1))

def fetch_interactive_embed(opener, section_url, exercise_id, retries=2):
    # Call Siyavula's internal fetch-embed API to fetch the interactive question
    api_url = 'https://www.siyavula.com/api/interactive-textbook/v1/fetch-embed'
    path = '/' + '/'.join(section_url.split('/')[3:])
    payload = json.dumps({
        "current_path": path,
        "section_exercise_id": exercise_id
    }).encode('utf-8')

    headers = {
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json',
        'Referer': section_url,
        'Accept': 'application/json, text/plain, */*'
    }

    req = urllib.request.Request(api_url, data=payload, headers=headers)
    for attempt in range(retries):
        try:
            with opener.open(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data
        except Exception as e:
            if attempt == retries - 1:
                return None
            time.sleep(1.0)
def fetch_solution_and_answer(opener, section_url, exercise_id, template_id=1, q_body_html=''):
    # Probe submit-answer to reveal the verified answer and step-by-step solution
    submit_url = 'https://www.siyavula.com/api/interactive-textbook/v1/submit-answer'
    path = '/' + '/'.join(section_url.split('/')[3:])
    
    # Dynamically extract all input/select names from the question HTML so the probe succeeds
    user_responses = {}
    if q_body_html:
        try:
            q_soup = BeautifulSoup(q_body_html, 'html.parser')
            for el in q_soup.find_all(['input', 'select']):
                name = el.get('name')
                el_type = el.get('type', '')
                if name and el_type not in ['submit', 'button', 'reset', 'checkbox']:
                    user_responses[name] = '1'
        except Exception:
            pass
    if not user_responses:
        user_responses = {'question1a': '1'}

    payload = json.dumps({
        'current_path': path,
        'section_exercise_id': exercise_id,
        'activity_template_id': template_id,
        'response_id': None,
        'response_index': 0,
        'duration': 5,
        'response_hash': None,
        'repeat_attempt': False,
        'user_responses': user_responses
    }).encode('utf-8')

    headers = {
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json',
        'Referer': section_url,
        'Accept': 'application/json, text/plain, */*'
    }

    try:
        req = urllib.request.Request(submit_url, data=payload, headers=headers)
        with opener.open(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            template = data.get('data', {}).get('activity_template', {})
            
            # Extract correct answers across all response groups
            correct_ans_list = []
            for resp_key, resp_val in template.get('responses', {}).items():
                c_resps = resp_val.get('correct_responses', [])
                if c_resps:
                    correct_ans_list.extend(c_resps)
            
            correct_ans = ", ".join(correct_ans_list) if correct_ans_list else ''

            body_html = template.get('question', {}).get('body', '')
            sol_text = ''
            if body_html:
                soup = BeautifulSoup(body_html, 'html.parser')
                sol_body = soup.find(class_='response-solution__body')
                if sol_body:
                    # Clean solution body text
                    sol_text = sol_body.get_text(' ', strip=True)

            return correct_ans, sol_text
    except Exception:
        return '', ''

def download_image(img_url, local_path, retries=3):
    if os.path.exists(local_path):
        return
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    req = urllib.request.Request(img_url, headers={'User-Agent': USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp, open(local_path, 'wb') as f:
                f.write(resp.read())
            return
        except Exception as e:
            if attempt == retries - 1:
                print(f"Warning: Failed to download image {img_url}: {e}", file=sys.stderr)
            time.sleep(1.0)

class MDXConverter:
    def __init__(self, base_url, assets_dir, opener=None):
        self.base_url = base_url
        self.assets_dir = assets_dir
        self.opener = opener or get_opener()

    def convert_element(self, node):
        if node is None:
            return ""
        if isinstance(node, NavigableString):
            return str(node)

        if not isinstance(node, Tag):
            return ""

        tag_name = node.name.lower()
        classes = node.get('class', [])
        if isinstance(classes, str):
            classes = [classes]

        # Ignore banners and script tags
        if tag_name in ['script', 'style', 'noscript']:
            return ""
        if any(c in ['sv-book-banner', 'sv-panel--page-toc'] for c in classes):
            return ""

        # Siyavula Interactive Exercises!
        if 'interactive_questions' in classes:
            # If it has a problemset child, let standard problemset handling process it
            if node.find(class_='problemset'):
                return "".join(self.convert_element(c) for c in node.children)

            # Dynamic Interactive Exercise
            ex_id = node.get('data-section-exercise-id') or node.get('id')
            ex_num = node.get('data-exercise-number') or ''
            title = f"Interactive Exercise {ex_num}".strip()

            if ex_id:
                embed_data = fetch_interactive_embed(self.opener, self.base_url, ex_id)
                if embed_data and embed_data.get('data', {}).get('activity_templates'):
                    out_cards = []
                    for tmpl in embed_data['data']['activity_templates']:
                        q_data = tmpl.get('question', {})
                        body_html = q_data.get('body', '')
                        if body_html:
                            q_soup = BeautifulSoup(body_html, 'html.parser')
                            prob_div = q_soup.find(class_='problem')
                            prob_text = prob_div.get_text(' ', strip=True) if prob_div else ''
                            # extract select options if multiple choice
                            options = []
                            for sel in q_soup.find_all('select'):
                                for opt in sel.find_all('option'):
                                    val = opt.get('value', '').strip()
                                    txt = opt.get_text(strip=True)
                                    if val and txt and txt.lower() != 'select':
                                        options.append(txt)

                            # extract hint from how-to-write
                            htw = q_soup.find(class_='how-to-write__body')
                            hint_text = htw.get_text(' ', strip=True) if htw else ''

                            # fetch verified answer & full solution
                            tmpl_id = tmpl.get('id', 1)
                            ans_str, sol_str = fetch_solution_and_answer(self.opener, self.base_url, ex_id, tmpl_id, body_html)

                            # If answer is an index into options (e.g. '1' for multiple choice), map it to option text
                            if options and ans_str.isdigit():
                                idx_ans = int(ans_str)
                                if idx_ans < len(options):
                                    ans_str = options[idx_ans]

                            # Clean escaped strings
                            clean_q = prob_text.replace('"', '\\"').replace('\n', ' ')
                            clean_hint = hint_text.replace('"', '\\"').replace('\n', ' ')
                            clean_sol = sol_str.replace('"', '\\"').replace('\n', ' ')
                            clean_ans = ans_str.replace('"', '\\"')

                            opts_json = json.dumps(options)
                            card_tag = f'<QuizCard id="{ex_id}" title="{title}" question="{clean_q}" options={opts_json} answer="{clean_ans}" hint="{clean_hint}" explanation="{clean_sol}" />'
                            out_cards.append(card_tag)

                    if out_cards:
                        return "\n\n" + "\n\n".join(out_cards) + "\n\n"

            return ""

        # Headings
        if tag_name == 'h1':
            title_text = node.get_text(' ', strip=True)
            return f"\n\n# {title_text}\n\n" if title_text else ""
        elif tag_name == 'h2':
            title_text = node.get_text(' ', strip=True)
            return f"\n\n## {title_text}\n\n" if title_text else ""
        elif tag_name == 'h3':
            title_text = node.get_text(' ', strip=True)
            return f"\n\n### {title_text}\n\n" if title_text else ""
        elif tag_name == 'h4':
            title_text = node.get_text(' ', strip=True)
            return f"\n\n#### {title_text}\n\n" if title_text else ""

        # Paragraphs & Embedded Videos
        elif tag_name == 'p':
            if 'video' in classes:
                a = node.find('a', href=True)
                if a:
                    v_url = a['href']
                    v_title = a.get_text(strip=True)
                    return f"\n\n<VideoPlayer src=\"{v_url}\" title=\"{v_title}\" />\n\n"
            content = "".join(self.convert_element(c) for c in node.children).strip()
            return f"\n\n{content}\n\n" if content else ""

        # Images
        elif tag_name == 'img':
            src = node.get('src', '')
            alt = node.get('alt', 'Figure')
            if src:
                full_img_url = urljoin(self.base_url, src)
                filename = os.path.basename(src)
                local_asset_path = os.path.join(self.assets_dir, filename)
                download_image(full_img_url, local_asset_path)
                return f"\n\n![{alt}](../../assets/images/{filename})\n\n"
            return ""

        # Lists with line continuation integrity
        elif tag_name == 'ul':
            items = []
            for li in node.find_all('li', recursive=False):
                li_str = "".join(self.convert_element(c) for c in li.children).strip()
                if li_str:
                    # Clean internal newlines to keep single list item continuous
                    clean_li = " ".join(li_str.split())
                    items.append(f"- {clean_li}")
            return ("\n\n" + "\n".join(items) + "\n\n") if items else ""

        elif tag_name == 'ol':
            items = []
            for i, li in enumerate(node.find_all('li', recursive=False), 1):
                li_str = "".join(self.convert_element(c) for c in li.children).strip()
                if li_str:
                    clean_li = " ".join(li_str.split())
                    items.append(f"{i}. {clean_li}")
            return ("\n\n" + "\n".join(items) + "\n\n") if items else ""

        # Definition lists
        elif tag_name == 'dl' and 'definition' in classes:
            dt = node.find('dt')
            dd = node.find('dd')
            dt_title = dt.get_text(' ', strip=True) if dt else 'Definition'
            dd_content = "".join(self.convert_element(c) for c in dd.children).strip() if dd else ''
            return f"\n\n<Callout type=\"info\" title=\"Definition: {dt_title}\">\n{dd_content}\n</Callout>\n\n"

        # Notes / Callouts
        elif 'note' in classes:
            c_type = 'note'
            title = 'Note'
            if 'visit' in classes:
                c_type = 'tip'
                title = 'Multimedia & Video'
            inner = "".join(self.convert_element(c) for c in node.children).strip()
            return f"\n\n<Callout type=\"{c_type}\" title=\"{title}\">\n{inner}\n</Callout>\n\n"

        # Worked examples
        elif 'worked_example' in classes:
            title_node = node.find(['h2', 'h3'], class_='title')
            title_str = title_node.get_text(' ', strip=True) if title_node else 'Worked Example'
            inner_parts = []
            for c in node.children:
                if c == title_node:
                    continue
                inner_parts.append(self.convert_element(c))
            inner = "".join(inner_parts).strip()
            return f"\n\n<Callout type=\"tip\" title=\"{title_str}\">\n{inner}\n</Callout>\n\n"

        # Worksteps
        elif 'workstep' in classes:
            step_header = node.find(['h3', 'h4'], class_='title')
            header_str = step_header.get_text(' ', strip=True) if step_header else 'Step'
            body_parts = []
            for c in node.children:
                if c == step_header:
                    continue
                body_parts.append(self.convert_element(c))
            body_str = "".join(body_parts).strip()
            return f"\n\n**{header_str}:**\n{body_str}\n\n"

        # Question / Problem / Solution
        elif 'question' in classes:
            q_str = "".join(self.convert_element(c) for c in node.children).strip()
            return f"\n\n**Question:**\n{q_str}\n\n"
        elif 'problem' in classes:
            p_str = "".join(self.convert_element(c) for c in node.children).strip()
            return f"\n\n**Problem:**\n{p_str}\n\n"
        elif 'solution' in classes:
            s_str = "".join(self.convert_element(c) for c in node.children).strip()
            return f"\n\n**Solution:**\n{s_str}\n\n"

        elif 'exerciseTitle' in classes:
            return f"\n\n### {node.get_text(' ', strip=True)}\n\n"

        # HTML Tables
        elif tag_name == 'table':
            rows = node.find_all('tr')
            if not rows:
                return ""
            md_table = []
            for r_idx, row in enumerate(rows):
                cols = [c.get_text(' ', strip=True) for c in row.find_all(['th', 'td'])]
                if not any(cols):
                    continue
                md_table.append("| " + " | ".join(cols) + " |")
                if r_idx == 0:
                    md_table.append("| " + " | ".join(["---"] * len(cols)) + " |")
            return ("\n\n" + "\n".join(md_table) + "\n\n") if md_table else ""

        # Default recursive traversal
        return "".join(self.convert_element(c) for c in node.children)

def clean_mdx_content(text, fallback_title=""):
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [l.rstrip() for l in text.split('\n')]
    cleaned = '\n'.join(lines).strip()
    if not cleaned.startswith('#'):
        cleaned = f"# {fallback_title}\n\n" + cleaned
    return cleaned + '\n'

def extract_section_to_mdx(section_info, out_dir, assets_dir):
    url = section_info['url']
    opener = get_opener()
    raw_html = fetch_html(url, opener=opener)

    pos1 = raw_html.find('nav-buttons')
    if pos1 != -1:
        pos1_close = raw_html.find('</table>', pos1) + len('</table>')
        pos2 = raw_html.find('nav-buttons', pos1_close)
        if pos2 != -1:
            pos2_table = raw_html.rfind('<table', pos1_close, pos2)
            content_html = raw_html[pos1_close:pos2_table]
        else:
            content_html = raw_html[pos1_close:]
    else:
        content_html = raw_html

    soup = BeautifulSoup(content_html, 'html.parser')
    converter = MDXConverter(url, assets_dir, opener=opener)
    mdx_body = converter.convert_element(soup)
    full_mdx = clean_mdx_content(mdx_body, fallback_title=section_info['title'])

    out_file = os.path.join(out_dir, f"{section_info['slug']}.mdx")
    os.makedirs(out_dir, exist_ok=True)
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(full_mdx)
    return out_file

def estimate_reading_time(word_count):
    minutes = max(5, round(word_count / 160))
    return minutes

def run_extraction():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    assets_dir = os.path.join(base_dir, 'assets', 'images')
    chapters_dir = os.path.join(base_dir, 'chapters')
    os.makedirs(assets_dir, exist_ok=True)
    os.makedirs(chapters_dir, exist_ok=True)

    # Load TOC from Siyavula
    toc_url = 'https://www.siyavula.com/read/za/mathematics/grade-10'
    opener = get_opener()
    soup = BeautifulSoup(fetch_html(toc_url, opener=opener), 'html.parser')
    main = soup.find('main')
    links = main.find_all('a', href=True)

    chapters = []
    curr_ch = None

    for a in links:
        href = a['href']
        text = a.get_text(strip=True)
        if not href.startswith('/read/za/mathematics/grade-10/'):
            continue
        parts = href.strip('/').split('/')
        if len(parts) == 5:
            slug = parts[4]
            if slug == 'image-attributions':
                continue
            curr_ch = {
                'slug': slug,
                'title': text,
                'url': 'https://www.siyavula.com' + href,
                'sections': []
            }
            chapters.append(curr_ch)
        elif len(parts) == 6:
            sec_slug = parts[5]
            if curr_ch:
                curr_ch['sections'].append({
                    'slug': sec_slug,
                    'title': text,
                    'url': 'https://www.siyavula.com' + href
                })

    manifest_toc = []
    tasks = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for ch_idx, ch in enumerate(chapters, 1):
            ch_num_str = f"{ch_idx:02d}"
            ch_dir_name = f"{ch_num_str}-{ch['slug']}"
            ch_out_dir = os.path.join(chapters_dir, ch_dir_name)

            ch_manifest = {
                "id": f"ch{ch_num_str}",
                "title": ch['title'],
                "sections": []
            }

            for sec_idx, sec in enumerate(ch['sections'], 1):
                sec_path = f"chapters/{ch_dir_name}/{sec['slug']}.mdx"
                sec_manifest_entry = {
                    "id": f"sec-{ch_num_str}-{sec_idx:02d}-{sec['slug']}",
                    "title": sec['title'],
                    "path": sec_path,
                    "estimatedMinutes": 15
                }
                ch_manifest["sections"].append(sec_manifest_entry)
                tasks.append(executor.submit(extract_section_to_mdx, sec, ch_out_dir, assets_dir))

            manifest_toc.append(ch_manifest)

        print(f"Dispatched {len(tasks)} section extraction tasks with interactive questions...")
        completed = 0
        for future in as_completed(tasks):
            try:
                out_path = future.result()
                completed += 1
                if completed % 10 == 0 or completed == len(tasks):
                    print(f"Progress: [{completed}/{len(tasks)}] sections extracted.")
            except Exception as e:
                print(f"Error processing section: {e}", file=sys.stderr)

    # Calculate word count & estimatedMinutes
    for ch in manifest_toc:
        for sec in ch["sections"]:
            full_sec_path = os.path.join(base_dir, sec["path"].replace('/', os.sep))
            if os.path.exists(full_sec_path):
                with open(full_sec_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                words = len(content.split())
                sec["estimatedMinutes"] = estimate_reading_time(words)

    manifest = {
        "$schema": "https://anaise.org/schemas/book.v1.json",
        "id": "book-caps-siyavula-math-grade-10",
        "title": "Mathematics Grade 10 (CAPS)",
        "subtitle": "Complete CAPS-aligned digital textbook for Grade 10 Mathematics by Siyavula Education.",
        "version": "1.1.0",
        "authors": [
            {
                "name": "Siyavula Education",
                "affiliation": "Siyavula Open Textbooks Project"
            }
        ],
        "license": "CC-BY-4.0",
        "toc": manifest_toc
    }

    manifest_path = os.path.join(base_dir, 'book.manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nSuccessfully generated book.manifest.json with {len(manifest_toc)} chapters and {len(tasks)} sections!")

if __name__ == '__main__':
    run_extraction()
