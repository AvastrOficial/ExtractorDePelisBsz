import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os
import time
import re

def extract_series_data(series_url):
    """Extrae información básica de una serie"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(series_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extraer imagen principal
        img_tag = soup.find('img', class_='lazy')
        img_url = urljoin(series_url, img_tag.get('data-src')) if img_tag else None

        # Extraer título
        title_tag = soup.find('h1', class_='Title') or soup.find('h1')
        title = title_tag.text.strip() if title_tag else series_url.split('/')[-1].replace('-', ' ').title()

        # Extraer año
        year_tag = soup.find('span', class_='Date')
        year = year_tag.text.strip() if year_tag else ""

        # Extraer rating
        rating_tag = soup.find('span', class_='Vote')
        rating = rating_tag.text.strip() if rating_tag else ""

        # Extraer descripción
        desc_tag = soup.find('div', class_='Description')
        description = ""
        if desc_tag:
            p_tags = desc_tag.find_all('p')
            for p in p_tags:
                if p.text and not p.find('span'):
                    description = p.text.strip()
                    break

        # Extraer género
        genre_tag = soup.find('p', class_='Genre')
        genre = []
        if genre_tag:
            genre_text = genre_tag.text.replace('Género:', '').replace('Genre:', '').strip()
            if genre_text:
                genre = [g.strip() for g in genre_text.split(',')]

        return {
            'title': title,
            'year': year,
            'rating': rating,
            'description': description,
            'genre': genre,
            'image_url': img_url,
            'url': series_url
        }

    except Exception as e:
        print(f"Error extrayendo datos de {series_url}: {e}")
        return None

def extract_video_sources(episode_url):
    """Extrae las fuentes de video de un episodio"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(episode_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        video_sources = []

        # Buscar todos los iframes con clase 'no-you'
        iframes = soup.find_all('iframe', class_='no-you')

        for iframe in iframes:
            data_src = iframe.get('data-src', '')
            src = iframe.get('src', '')

            # Preferir data-src, sino src
            video_url = data_src if data_src else src

            if video_url and video_url.startswith('http'):
                # Extraer el dominio para identificar el servicio
                domain_match = re.search(r'https?://([^/]+)', video_url)
                domain = domain_match.group(1) if domain_match else 'unknown'

                # Limpiar el dominio para nombre más legible
                clean_domain = domain.replace('www.', '').replace('.com', '').replace('.to', '').replace('.sx', '').replace('.net', '')

                video_sources.append({
                    'service': clean_domain,
                    'url': video_url,
                    'domain': domain
                })

        # Si no hay iframes, buscar otros reproductores
        if not video_sources:
            # Buscar divs de reproductor
            player_divs = soup.find_all('div', class_='TPlayerTb')
            for player in player_divs:
                iframe = player.find('iframe')
                if iframe:
                    data_src = iframe.get('data-src', '')
                    src = iframe.get('src', '')
                    video_url = data_src if data_src else src

                    if video_url and video_url.startswith('http'):
                        domain_match = re.search(r'https?://([^/]+)', video_url)
                        domain = domain_match.group(1) if domain_match else 'unknown'
                        clean_domain = domain.replace('www.', '').replace('.com', '').replace('.to', '').replace('.sx', '').replace('.net', '')

                        video_sources.append({
                            'service': clean_domain,
                            'url': video_url,
                            'domain': domain
                        })

        return video_sources

    except Exception as e:
        print(f"  ❌ Error extrayendo fuentes de video: {e}")
        return []

def extract_episodes_from_series(series_url, extract_videos=False):
    """Extrae episodios de una serie específica"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(series_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        episodes_data = {}

        # Buscar selector de temporadas
        season_select = soup.find('select', id='select-season')

        if season_select:
            # Extraer todas las temporadas
            season_options = season_select.find_all('option')
            print(f"  ⏳ Encontradas {len(season_options)} temporadas")

            for option in season_options:
                season_value = option.get('value', '').strip()
                if season_value:
                    season_id = f"season-{season_value}"

                    # Buscar la lista de episodios para esta temporada
                    episodes_list = soup.find('ul', id=season_id, class_='all-episodes')

                    if episodes_list:
                        episodes = extract_episodes_from_ul(episodes_list, series_url, extract_videos)
                        if episodes:
                            episodes_data[season_id] = episodes
                            print(f"    ✅ Temporada {season_value}: {len(episodes)} episodios")
                    else:
                        # Intentar buscar cualquier lista con episodios
                        all_lists = soup.find_all('ul', class_='all-episodes')
                        if all_lists:
                            season_num = int(season_value) if season_value.isdigit() else 1
                            if len(all_lists) >= season_num:
                                episodes = extract_episodes_from_ul(all_lists[season_num-1], series_url, extract_videos)
                                if episodes:
                                    episodes_data[season_id] = episodes
                                    print(f"    ✅ Temporada {season_value}: {len(episodes)} episodios")
        else:
            # Si no hay selector, buscar episodios directamente
            episodes_list = soup.find('ul', class_='all-episodes')
            if not episodes_list:
                # Intentar con otra clase
                episodes_list = soup.find('ul', class_='episodes')

            if episodes_list:
                episodes = extract_episodes_from_ul(episodes_list, series_url, extract_videos)
                if episodes:
                    episodes_data['season-1'] = episodes
                    print(f"  ✅ Encontrados {len(episodes)} episodios")
            else:
                print(f"  ⚠️ No se encontró lista de episodios")

        return episodes_data

    except Exception as e:
        print(f"  ❌ Error extrayendo episodios: {e}")
        return {}

def extract_episodes_from_ul(episodes_list, base_url, extract_videos=False):
    """Extrae episodios de una lista UL"""
    episodes = []

    # Buscar todos los items de episodio
    episode_items = episodes_list.find_all('li', class_=lambda x: x and 'TPost' in x)

    if not episode_items:
        # Intentar con cualquier li
        episode_items = episodes_list.find_all('li')

    print(f"    Encontrados {len(episode_items)} items de episodio")

    for idx, item in enumerate(episode_items, 1):
        try:
            # Extraer enlace del episodio
            link_tag = item.find('a')
            if not link_tag:
                continue

            episode_path = link_tag.get('href', '')
            if not episode_path:
                continue

            # Completar la URL si es relativa
            episode_url = urljoin(base_url, episode_path)

            # Extraer título
            title_tag = item.find('h2', class_='Title')
            if not title_tag:
                title_tag = item.find('h2')

            episode_title = title_tag.text.strip() if title_tag else ""

            # Extraer número de episodio
            episode_num_tag = item.find('span', class_='Year')
            episode_num = episode_num_tag.text.strip() if episode_num_tag else ""

            # Si no hay número, intentar extraer del título
            if not episode_num and episode_title:
                # Buscar patrones como 1x1, 1x2, etc.
                match = re.search(r'(\d+x\d+)', episode_title)
                if match:
                    episode_num = match.group(1)

            # Extraer imagen del episodio
            img_tag = item.find('img', class_='lazy')
            episode_img = ""
            if img_tag:
                img_src = img_tag.get('data-src') or img_tag.get('src')
                if img_src:
                    episode_img = urljoin(base_url, img_src)

            # Estructura básica del episodio
            episode_data = {
                'title': episode_title,
                'episode_number': episode_num,
                'url': episode_url,
                'image_url': episode_img
            }

            # Extraer fuentes de video si se solicita
            if extract_videos:
                print(f"      [{idx}/{len(episode_items)}] Extrayendo fuentes de video...")
                video_sources = extract_video_sources(episode_url)
                if video_sources:
                    episode_data['video_sources'] = video_sources
                    print(f"      ✅ {len(video_sources)} fuentes encontradas")
                else:
                    print(f"      ⚠️ Sin fuentes de video")

                # Pequeña pausa entre episodios
                time.sleep(0.5)

            episodes.append(episode_data)

        except Exception as e:
            print(f"      ❌ Error procesando episodio: {e}")
            continue

    return episodes

def save_to_json(data, filename):
    """Guarda datos en formato JSON"""
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def extract_series_from_listing_page(page_url, extract_episodes=False, extract_videos=False):
    """Extrae todas las series de una página de listado"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(page_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        series_list = []
        series_links = []

        # Buscar en contenedores TPost (que contienen series)
        series_containers = soup.find_all('div', class_='TPost')

        for container in series_containers:
            try:
                link_tag = container.find('a')
                if link_tag and link_tag.get('href'):
                    href = link_tag['href']
                    if '/serie/' in href and href not in series_links:
                        series_url = urljoin(page_url, href)
                        series_links.append(series_url)
            except:
                continue

        print(f"  📄 Encontrados {len(series_links)} enlaces de series")

        # Procesar cada serie
        for idx, series_url in enumerate(series_links, 1):
            print(f"\n    [{idx}/{len(series_links)}] Procesando serie...")

            try:
                # Extraer datos básicos
                series_data = extract_series_data(series_url)
                if series_data:
                    print(f"      ✅ '{series_data['title'][:30]}...' encontrada")

                    # Extraer episodios si se solicita
                    if extract_episodes:
                        print(f"      ⏳ Extrayendo episodios...")
                        episodes = extract_episodes_from_series(series_url, extract_videos)
                        if episodes:
                            series_data['episodes'] = episodes
                            total_episodes = sum(len(eps) for eps in episodes.values())
                            print(f"      ✅ {total_episodes} episodios extraídos")
                        else:
                            print(f"      ⚠️ No se encontraron episodios")

                    series_list.append(series_data)
                else:
                    print(f"      ❌ Error extrayendo datos de la serie")

            except Exception as e:
                print(f"      ❌ Error procesando serie: {e}")
                continue

            # Pausa para no sobrecargar
            time.sleep(1)

        return series_list

    except Exception as e:
        print(f"  ❌ Error extrayendo series de {page_url}: {e}")
        return []

def organize_by_year(series_list):
    """Organiza series por año"""
    organized = {}

    for series in series_list:
        year = series.get('year', 'Sin año')
        if year not in organized:
            organized[year] = []
        organized[year].append(series)

    # Ordenar años
    sorted_years = sorted(
        organized.keys(), 
        reverse=True, 
        key=lambda x: (0, int(x)) if x.isdigit() else (1, x)
    )

    return {year: organized[year] for year in sorted_years}

# ============ PROGRAMA PRINCIPAL ============
print("=" * 60)
print("EXTRACTOR COMPLETO DE SERIES CUEVANA")
print("=" * 60)

# Preguntar qué extraer
print("\n¿Qué deseas extraer?")
print("1. Series de páginas de listado (ej: /serie/, /serie/page/2)")
print("2. Series específicas")
print("3. Solo información básica de series")

option = input("\nSelecciona una opción (1-3): ").strip()

# Configurar opciones de extracción
extract_episodes_option = False
extract_videos_option = False

if option == '1':
    print("\n📺 ¿Deseas extraer también los episodios de cada serie?")
    episodes_choice = input("   ¿Extraer episodios? (s/n): ").strip().lower()

    if episodes_choice == 's':
        extract_episodes_option = True

        print("\n🎬 ¿Deseas extraer también las fuentes de video de cada episodio?")
        print("   Esto tomará MUCHO más tiempo pero obtendrás los enlaces directos a los videos.")
        videos_choice = input("   ¿Extraer fuentes de video? (s/n): ").strip().lower()

        if videos_choice == 's':
            extract_videos_option = True
            print("\n   ⚠️  ADVERTENCIA: Extraer fuentes de video puede tomar MUCHO tiempo.")
            print("   Se recomienda procesar solo 1 página con pocas series.")
            confirm = input("   ¿Continuar? (s/n): ").strip().lower()
            if confirm != 's':
                extract_videos_option = False
                print("   ✅ Solo se extraerán episodios sin fuentes de video.")
        else:
            print("   ✅ Solo se extraerán episodios sin fuentes de video.")

    else:
        print("   ✅ Solo se extraerá información básica de series.")

elif option == '2':
    extract_episodes_option = True

    print("\n🎬 ¿Deseas extraer también las fuentes de video de cada episodio?")
    videos_choice = input("   ¿Extraer fuentes de video? (s/n): ").strip().lower()

    if videos_choice == 's':
        extract_videos_option = True
        print("   ⚠️  Se extraerán fuentes de video de cada episodio.")

# Solicitar URLs
if option == '1':
    print("\n📥 Introduce URLs de páginas de listado (separadas por comas):")
    print("   Ejemplo: https://ww9.cuevana3.to/serie/")
    print("            https://ww9.cuevana3.to/serie/page/2")

    if extract_videos_option:
        print("\n   💡 CONSEJO EXTREMO: Con fuentes de video, procesa solo 1 página.")
    elif extract_episodes_option:
        print("\n   💡 CONSEJO: Procesa solo 1-2 páginas para no sobrecargar.")
else:
    print("\n📥 Introduce URLs de series específicas (separadas por comas):")
    print("   Ejemplo: https://ww9.cuevana3.to/serie/belleza-perfecta")

urls_input = input("\n🔗 URLs: ").strip()

# Configurar archivos de salida
html_filename = 'series_catalog.html'
all_series_data = []
individual_files = []

# Iniciar HTML
html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Catálogo Completo de Series - Cuevana</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: white;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #00b4d8;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #90e0ef;
            margin-bottom: 30px;
        }
        .url-section {
            background: #2a2a2a;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 30px;
            border-left: 5px solid #00b4d8;
        }
        .url-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #444;
        }
        .url-title {
            color: #00b4d8;
            margin: 0;
            font-size: 1.3rem;
        }
        .json-link {
            background: #00b4d8;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
        }
        .json-link:hover {
            background: #0093b3;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .stat {
            background: #333;
            padding: 15px 25px;
            border-radius: 8px;
            text-align: center;
            min-width: 120px;
        }
        .stat .number {
            font-size: 24px;
            font-weight: bold;
            color: #00b4d8;
            display: block;
        }
        .stat .label {
            font-size: 14px;
            color: #aaa;
        }
        .series-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
            margin-top: 25px;
        }
        .series-card {
            background: #333;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #444;
            transition: transform 0.3s, border-color 0.3s;
        }
        .series-card:hover {
            transform: translateY(-5px);
            border-color: #00b4d8;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
        }
        .series-img {
            width: 100%;
            height: 450px;
            object-fit: cover;
        }
        .series-content {
            padding: 20px;
        }
        .series-title {
            font-size: 1.2rem;
            margin: 0 0 10px 0;
            color: white;
            line-height: 1.3;
        }
        .series-meta {
            color: #90e0ef;
            font-size: 14px;
            margin-bottom: 15px;
        }
        .series-desc {
            color: #ccc;
            font-size: 14px;
            line-height: 1.5;
            margin-bottom: 20px;
            max-height: 4.5em;
            overflow: hidden;
        }
        .series-genres {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 20px;
        }
        .genre-tag {
            background: #444;
            color: #90e0ef;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 12px;
        }
        .episodes-toggle {
            background: #444;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 15px;
            width: 100%;
            margin-top: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .episodes-toggle:hover {
            background: #555;
        }
        .episodes-container {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.5s ease-out;
        }
        .season {
            background: #3a3a3a;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }
        .season-title {
            color: #00b4d8;
            margin: 0 0 15px 0;
            font-size: 16px;
        }
        .episode {
            background: #444;
            border-radius: 6px;
            padding: 15px;
            margin: 10px 0;
        }
        .episode-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .episode-title {
            color: white;
            font-size: 15px;
            margin: 0;
        }
        .episode-number {
            background: #00b4d8;
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 13px;
            font-weight: bold;
        }
        .episode-url {
            color: #90e0ef;
            font-size: 13px;
            margin: 5px 0;
            word-break: break-all;
        }
        .video-sources {
            background: #2a2a2a;
            border-radius: 6px;
            padding: 15px;
            margin-top: 10px;
        }
        .sources-title {
            color: #00b4d8;
            font-size: 14px;
            margin: 0 0 10px 0;
        }
        .source-item {
            background: #333;
            border-radius: 4px;
            padding: 10px;
            margin: 8px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .source-service {
            color: #90e0ef;
            font-weight: bold;
            font-size: 13px;
        }
        .source-url {
            color: #aaa;
            font-size: 12px;
            word-break: break-all;
            max-width: 70%;
        }
        .summary {
            background: linear-gradient(135deg, #1a2a3a 0%, #0f172a 100%);
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            margin-top: 40px;
            border: 2px solid #00b4d8;
        }
        .summary-title {
            color: #00b4d8;
            font-size: 1.8rem;
            margin: 0 0 25px 0;
        }
        @media (max-width: 768px) {
            .series-grid {
                grid-template-columns: 1fr;
            }
            .url-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 15px;
            }
            .stat {
                min-width: 100px;
                padding: 12px 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Catálogo Completo de Series</h1>
        <div class="subtitle">Extraído de Cuevana • Incluye episodios y fuentes de video</div>
"""

# Procesar cada URL individualmente
urls_list = [url.strip() for url in urls_input.split(',') if url.strip()]
total_series_count = 0
total_episodes_count = 0
total_video_sources = 0

for url_index, url in enumerate(urls_list, 1):
    print(f"\n{'='*60}")
    print(f"📁 PROCESANDO URL {url_index}/{len(urls_list)}")
    print(f"🔗 {url}")
    print('='*60)

    url_series_data = []
    url_episodes_count = 0
    url_video_sources = 0

    if option == '1':
        # Extraer series de página de listado
        print(f"⏳ Extrayendo series de la página de listado...")
        series_from_page = extract_series_from_listing_page(
            url, 
            extract_episodes_option, 
            extract_videos_option
        )

        if series_from_page:
            url_series_data.extend(series_from_page)

            # Contar estadísticas
            for series in series_from_page:
                if 'episodes' in series:
                    for season_episodes in series['episodes'].values():
                        url_episodes_count += len(season_episodes)
                        for episode in season_episodes:
                            if 'video_sources' in episode:
                                url_video_sources += len(episode['video_sources'])

            stats_msg = f"✅ {len(series_from_page)} series extraídas"
            if url_episodes_count > 0:
                stats_msg += f", {url_episodes_count} episodios"
            if url_video_sources > 0:
                stats_msg += f", {url_video_sources} fuentes de video"

            print(stats_msg)
    else:
        # Extraer serie específica
        print(f"⏳ Extrayendo serie específica...")
        series_data = extract_series_data(url)
        if series_data:
            if extract_episodes_option:
                print(f"⏳ Extrayendo episodios...")
                episodes = extract_episodes_from_series(url, extract_videos_option)
                if episodes:
                    series_data['episodes'] = episodes
                    url_episodes_count = sum(len(eps) for eps in episodes.values())

                    # Contar fuentes de video
                    for season_episodes in episodes.values():
                        for episode in season_episodes:
                            if 'video_sources' in episode:
                                url_video_sources += len(episode['video_sources'])

                    stats_msg = f"✅ Serie con {url_episodes_count} episodios"
                    if url_video_sources > 0:
                        stats_msg += f" y {url_video_sources} fuentes de video"
                    print(stats_msg)
                else:
                    print(f"⚠️ Serie sin episodios encontrados")

            url_series_data.append(series_data)

    # Si se extrajeron series de esta URL, guardar archivo individual
    if url_series_data:
        # Organizar por año para esta URL específica
        url_series_by_year = organize_by_year(url_series_data)

        # Guardar archivo JSON individual
        json_filename = f"{url_index}.json"
        save_to_json(url_series_by_year, json_filename)
        individual_files.append(json_filename)

        print(f"💾 Datos guardados en: {json_filename}")

        # Agregar al total combinado
        all_series_data.extend(url_series_data)
        total_series_count += len(url_series_data)
        total_episodes_count += url_episodes_count
        total_video_sources += url_video_sources

        # Agregar al HTML
        html_content += f'<div class="url-section">\n'
        html_content += f'<div class="url-header">\n'
        html_content += f'<h2 class="url-title">📦 Fuente {url_index}</h2>\n'
        html_content += f'<a href="{json_filename}" class="json-link" target="_blank">📥 Descargar JSON</a>\n'
        html_content += f'</div>\n'
        html_content += f'<p style="color: #90e0ef; margin-bottom: 10px;">URL: {url}</p>\n'

        # Estadísticas de esta URL
        total_url_series = len(url_series_data)
        total_url_years = len(url_series_by_year)

        html_content += f'<div class="stats">\n'
        html_content += f'<div class="stat"><span class="number">{total_url_series}</span><span class="label">Series</span></div>\n'
        html_content += f'<div class="stat"><span class="number">{total_url_years}</span><span class="label">Años</span></div>\n'
        if url_episodes_count > 0:
            html_content += f'<div class="stat"><span class="number">{url_episodes_count}</span><span class="label">Episodios</span></div>\n'
        if url_video_sources > 0:
            html_content += f'<div class="stat"><span class="number">{url_video_sources}</span><span class="label">Fuentes Video</span></div>\n'
        html_content += f'</div>\n'

        # Mostrar series organizadas por año
        for year, year_series in url_series_by_year.items():
            html_content += f'<h3 style="color: #00b4d8; margin: 25px 0 15px 0; border-bottom: 2px solid #00b4d8; padding-bottom: 10px;">🎬 Año {year} ({len(year_series)} series)</h3>\n'
            html_content += f'<div class="series-grid">\n'

            for series in year_series:
                has_episodes = 'episodes' in series and series['episodes']
                has_video_sources = False

                if has_episodes:
                    for season_episodes in series['episodes'].values():
                        for episode in season_episodes:
                            if 'video_sources' in episode:
                                has_video_sources = True
                                break
                        if has_video_sources:
                            break

                html_content += f'<div class="series-card">\n'
                html_content += f'<img src="{series.get("image_url", "")}" alt="{series["title"]}" class="series-img" onerror="this.src=\'https://via.placeholder.com/350x450/333/fff?text=No+Image\'">\n'
                html_content += f'<div class="series-content">\n'
                html_content += f'<h3 class="series-title">{series["title"]}</h3>\n'
                html_content += f'<div class="series-meta">📅 {series.get("year", "N/A")} | ⭐ {series.get("rating", "N/A")}</div>\n'

                if series.get('genre'):
                    html_content += f'<div class="series-genres">\n'
                    for genre in series['genre'][:3]:
                        html_content += f'<span class="genre-tag">{genre}</span>\n'
                    if len(series['genre']) > 3:
                        html_content += f'<span class="genre-tag">+{len(series["genre"])-3}</span>\n'
                    html_content += f'</div>\n'

                if series.get('description'):
                    html_content += f'<div class="series-desc">{series["description"][:200]}...</div>\n'

                # Mostrar episodios si existen
                if has_episodes:
                    episodes_html = ""
                    for season_id, episodes in series['episodes'].items():
                        episodes_html += f'<div class="season">\n'
                        episodes_html += f'<h4 class="season-title">{season_id}</h4>\n'

                        for episode in episodes[:3]:  # Mostrar máximo 3 episodios por temporada
                            episodes_html += f'<div class="episode">\n'
                            episodes_html += f'<div class="episode-header">\n'
                            episodes_html += f'<h5 class="episode-title">{episode["title"][:40]}{"..." if len(episode["title"]) > 40 else ""}</h5>\n'
                            episodes_html += f'<span class="episode-number">{episode["episode_number"]}</span>\n'
                            episodes_html += f'</div>\n'
                            episodes_html += f'<div class="episode-url">🔗 <a href="{episode["url"]}" target="_blank" style="color: #90e0ef;">Ver episodio</a></div>\n'

                            # Mostrar fuentes de video si existen
                            if 'video_sources' in episode and episode['video_sources']:
                                episodes_html += f'<div class="video-sources">\n'
                                episodes_html += f'<h6 class="sources-title">🎬 Fuentes de video:</h6>\n'
                                for source in episode['video_sources'][:3]:  # Máximo 3 fuentes
                                    episodes_html += f'<div class="source-item">\n'
                                    episodes_html += f'<span class="source-service">{source["service"]}</span>\n'
                                    episodes_html += f'<a href="{source["url"]}" class="source-url" target="_blank" title="{source["url"]}">Ver video</a>\n'
                                    episodes_html += f'</div>\n'
                                if len(episode['video_sources']) > 3:
                                    episodes_html += f'<div style="color: #aaa; font-size: 12px; text-align: center;">+ {len(episode["video_sources"]) - 3} fuentes más</div>\n'
                                episodes_html += f'</div>\n'

                            episodes_html += f'</div>\n'

                        if len(episodes) > 3:
                            episodes_html += f'<div style="color: #aaa; text-align: center; padding: 10px;">... y {len(episodes) - 3} episodios más</div>\n'

                        episodes_html += f'</div>\n'

                    # Botón toggle para episodios
                    toggle_text = "📺 Mostrar Episodios"
                    if has_video_sources:
                        toggle_text = "🎬 Mostrar Episodios y Videos"

                    html_content += f'<button class="episodes-toggle" onclick="toggleEpisodes(this)">\n'
                    html_content += f'<span>{toggle_text}</span>\n'
                    html_content += f'<span>▼</span>\n'
                    html_content += f'</button>\n'
                    html_content += f'<div class="episodes-container">\n'
                    html_content += episodes_html
                    html_content += f'</div>\n'

                html_content += f'</div>\n'  # Cerrar series-content
                html_content += f'</div>\n'  # Cerrar series-card

            html_content += f'</div>\n'  # Cerrar series-grid

        html_content += f'</div>\n'  # Cerrar url-section

    else:
        print(f"❌ No se encontraron series en esta URL")
        html_content += f'<div class="url-section">\n'
        html_content += f'<h2 class="url-title">📦 Fuente {url_index} - Sin datos</h2>\n'
        html_content += f'<p style="color: #ff6b6b;">⚠️ No se encontraron series en esta URL</p>\n'
        html_content += f'</div>\n'

    # Pausa entre URLs
    if url_index < len(urls_list):
        print(f"⏳ Esperando 3 segundos...")
        time.sleep(3)

# Guardar archivo JSON combinado si hay múltiples URLs
if len(individual_files) > 1 and all_series_data:
    combined_series_by_year = organize_by_year(all_series_data)
    save_to_json(combined_series_by_year, 'todas_las_series.json')
    print(f"\n✅ Archivo combinado guardado en: todas_las_series.json")

# Agregar resumen final al HTML
html_content += f'<div class="summary">\n'
html_content += f'<h2 class="summary-title">📊 RESUMEN TOTAL DE EXTRACCIÓN</h2>\n'
html_content += f'<div class="stats" style="justify-content: center;">\n'
html_content += f'<div class="stat"><span class="number">{total_series_count}</span><span class="label">Series Totales</span></div>\n'
html_content += f'<div class="stat"><span class="number">{len(organize_by_year(all_series_data))}</span><span class="label">Años Distintos</span></div>\n'
html_content += f'<div class="stat"><span class="number">{len(urls_list)}</span><span class="label">URLs Procesadas</span></div>\n'
if total_episodes_count > 0:
    html_content += f'<div class="stat"><span class="number">{total_episodes_count}</span><span class="label">Episodios Totales</span></div>\n'
if total_video_sources > 0:
    html_content += f'<div class="stat"><span class="number">{total_video_sources}</span><span class="label">Fuentes de Video</span></div>\n'
html_content += f'</div>\n'

if len(individual_files) > 1:
    html_content += f'<p style="margin-top: 20px;">\n'
    html_content += f'<a href="todas_las_series.json" class="json-link" target="_blank" style="font-size: 1.1rem; padding: 15px 30px;">📦 Descargar JSON Completo (todas_las_series.json)</a>\n'
    html_content += f'</p>\n'

html_content += f'</div>\n'

# Cerrar HTML
html_content += """
    </div>
    <script>
        function toggleEpisodes(button) {
            const episodesContainer = button.nextElementSibling;
            const arrow = button.querySelector('span:last-child');

            if (episodesContainer.style.maxHeight) {
                episodesContainer.style.maxHeight = null;
                arrow.textContent = '▼';
                button.querySelector('span:first-child').textContent = 
                    button.querySelector('span:first-child').textContent.replace('Ocultar', 'Mostrar');
            } else {
                episodesContainer.style.maxHeight = episodesContainer.scrollHeight + 'px';
                arrow.textContent = '▲';
                button.querySelector('span:first-child').textContent = 
                    button.querySelector('span:first-child').textContent.replace('Mostrar', 'Ocultar');
            }
        }
    </script>
</body>
</html>
"""

# Guardar HTML
with open(html_filename, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n✅ Catálogo HTML guardado en: {html_filename}")

# Resumen final
print("\n" + "="*60)
print("📋 RESUMEN FINAL DE EXTRACCIÓN")
print("="*60)
print(f"🌐 URLs procesadas: {len(urls_list)}")
print(f"🎬 Series extraídas: {total_series_count}")
print(f"📺 Episodios encontrados: {total_episodes_count}")
print(f"🎬 Fuentes de video extraídas: {total_video_sources}")

if individual_files:
    print("\n📄 Archivos JSON generados:")
    for json_file in individual_files:
        print(f"  • {json_file}")

    if len(individual_files) > 1:
        print(f"  • todas_las_series.json (combinado)")

print(f"\n🖥️  Visualización completa:")
print(f"  • {html_filename} (abrir en navegador)")

print("\n" + "="*60)
print("✅ ¡Extracción COMPLETA finalizada exitosamente!")
print("="*60)
