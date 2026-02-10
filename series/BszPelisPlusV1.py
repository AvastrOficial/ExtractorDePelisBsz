import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os
import time

def extract_series_data(series_url):
    """Extrae información básica de una serie"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(series_url, headers=headers)
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

def extract_seasons_and_episodes(series_url):
    """Extrae temporadas y episodios de una serie"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(series_url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Buscar selector de temporadas
        season_select = soup.find('select', id='select-season')
        seasons_data = {}

        if season_select:
            # Extraer todas las temporadas
            season_options = season_select.find_all('option')
            print(f"  Encontradas {len(season_options)} temporadas")

            for option in season_options:
                season_value = option.get('value', '').strip()
                if season_value:
                    season_id = f"season-{season_value}"
                    episodes = extract_episodes_for_season(soup, season_id, series_url)
                    if episodes:
                        seasons_data[season_id] = episodes
                        print(f"    Temporada {season_value}: {len(episodes)} episodios")
        else:
            # Si no hay selector, buscar episodios directamente
            episodes_list = soup.find('ul', class_='all-episodes')
            if episodes_list:
                episodes = extract_episodes_from_list(episodes_list, series_url)
                seasons_data['season-1'] = episodes
                print(f"  Encontrados {len(episodes)} episodios")

        return seasons_data

    except Exception as e:
        print(f"  Error extrayendo episodios: {e}")
        return {}

def extract_episodes_for_season(soup, season_id, base_url):
    """Extrae episodios de una temporada específica"""
    episodes = []

    # Buscar la lista de episodios para esta temporada
    episodes_list = soup.find('ul', id=season_id, class_='all-episodes')

    if episodes_list:
        episodes = extract_episodes_from_list(episodes_list, base_url)

    return episodes

def extract_episodes_from_list(episodes_list, base_url):
    """Extrae episodios de una lista HTML"""
    episodes = []

    episode_items = episodes_list.find_all('li', class_='TPostMv')

    for item in episode_items:
        try:
            # Extraer enlace del episodio
            link_tag = item.find('a')
            if not link_tag:
                continue

            episode_path = link_tag.get('href', '')
            episode_url = urljoin(base_url, episode_path)

            # Extraer título
            title_tag = item.find('h2', class_='Title')
            episode_title = title_tag.text.strip() if title_tag else ""

            # Extraer número de episodio
            episode_num_tag = item.find('span', class_='Year')
            episode_num = episode_num_tag.text.strip() if episode_num_tag else ""

            # Extraer imagen del episodio
            img_tag = item.find('img', class_='lazy')
            episode_img = ""
            if img_tag:
                img_src = img_tag.get('data-src') or img_tag.get('src')
                if img_src:
                    episode_img = urljoin(base_url, img_src)

            episodes.append({
                'title': episode_title,
                'episode_number': episode_num,
                'url': episode_url,
                'image_url': episode_img
            })

        except Exception as e:
            print(f"    Error procesando episodio: {e}")
            continue

    return episodes

def save_to_json(data, filename):
    """Guarda datos en formato JSON"""
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def create_series_block(series_data, with_episodes=False):
    """Crea un bloque HTML para una serie"""
    if with_episodes and 'episodes' in series_data:
        # Bloque con episodios
        episodes_html = ""
        for season_id, episodes in series_data['episodes'].items():
            episodes_html += f'<div class="season"><h3>{season_id}</h3><ul>'
            for episode in episodes:
                episodes_html += f'<li><a href="{episode["url"]}" target="_blank">{episode["episode_number"]} - {episode["title"]}</a></li>'
            episodes_html += '</ul></div>'

        block = f"""
    <div class="series" onclick="toggleEpisodes(this)">
        <div class="series-header">
            <img src="{series_data.get('image_url', '')}" alt="{series_data['title']}">
            <div class="series-info">
                <h2>{series_data['title']}</h2>
                <p>Año: {series_data.get('year', 'N/A')} | Rating: {series_data.get('rating', 'N/A')}</p>
            </div>
        </div>
        <div class="episodes-container" style="display: none;">
            {episodes_html}
        </div>
    </div>
    """
    else:
        # Bloque simple
        block = f"""
    <div class="series">
        <a href="{series_data['url']}" target="_blank">
            <img src="{series_data.get('image_url', '')}" alt="{series_data['title']}">
            <h2>{series_data['title']}</h2>
            <p>{series_data.get('year', '')} | {series_data.get('rating', '')}</p>
        </a>
    </div>
    """

    return block

def extract_series_from_page(page_url):
    """Extrae todas las series de una página de listado"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(page_url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        series_list = []

        # Buscar todos los enlaces a series
        series_links = []

        # Buscar en contenedores TPost
        series_containers = soup.find_all('div', class_='TPost')
        for container in series_containers:
            link_tag = container.find('a')
            if link_tag and link_tag.get('href'):
                series_url = urljoin(page_url, link_tag['href'])
                if series_url not in series_links:
                    series_links.append(series_url)

        # También buscar directamente enlaces que contengan /serie/
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/serie/' in href and href not in series_links:
                series_url = urljoin(page_url, href)
                series_links.append(series_url)

        print(f"  Encontrados {len(series_links)} enlaces de series")

        # Procesar cada serie
        for idx, series_url in enumerate(series_links, 1):
            print(f"    Procesando serie {idx}/{len(series_links)}: {series_url}")

            # Extraer datos básicos
            series_data = extract_series_data(series_url)
            if series_data:
                # Extraer episodios si se solicita
                if extract_episodes_option:
                    episodes = extract_seasons_and_episodes(series_url)
                    series_data['episodes'] = episodes

                series_list.append(series_data)

            # Pausa para no sobrecargar
            time.sleep(1)

        return series_list

    except Exception as e:
        print(f"  Error extrayendo series: {e}")
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
    sorted_years = sorted(organized.keys(), reverse=True, 
                         key=lambda x: int(x) if x.isdigit() else 0)

    return {year: organized[year] for year in sorted_years}

# ============ PROGRAMA PRINCIPAL ============
print("=" * 60)
print("EXTRACTOR DE SERIES CUEVANA")
print("=" * 60)

# Preguntar qué extraer
print("\n¿Qué deseas extraer?")
print("1. Series de páginas de listado (ej: /serie/, /serie/page/2)")
print("2. Episodios de series específicas (URLs directas a series)")
print("3. Ambos (series y sus episodios)")

option = input("\nSelecciona una opción (1-3): ").strip()

# Preguntar si extraer episodios
extract_episodes_option = False
if option in ['2', '3']:
    extract_episodes_option = True

# Solicitar URLs
if option == '1':
    print("\nIntroduce URLs de páginas de listado (separadas por comas):")
    print("Ejemplo: https://ww9.cuevana3.to/serie/, https://ww9.cuevana3.to/serie/page/2")
else:
    print("\nIntroduce URLs de series específicas (separadas por comas):")
    print("Ejemplo: https://ww9.cuevana3.to/serie/wonder-man")

urls_input = input("\nURLs: ")

# Configurar archivos de salida
html_filename = 'series_catalog.html'
all_series_data = []  # Para el archivo JSON combinado
individual_files = []  # Para rastrear archivos individuales

# Iniciar HTML
html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Catálogo de Series</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: white;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #00b4d8;
            margin-bottom: 30px;
        }
        .url-section {
            background: #2a2a2a;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            border-left: 5px solid #00b4d8;
        }
        .url-title {
            color: #90e0ef;
            margin-top: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .url-title .json-link {
            font-size: 14px;
            background: #00b4d8;
            padding: 3px 10px;
            border-radius: 15px;
            text-decoration: none;
            color: white;
        }
        .url-title .json-link:hover {
            background: #0093b3;
        }
        .series-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .series {
            background: #333;
            border-radius: 10px;
            overflow: hidden;
            transition: transform 0.3s;
            border: 1px solid #444;
        }
        .series:hover {
            transform: translateY(-5px);
            border-color: #00b4d8;
        }
        .series img {
            width: 100%;
            height: 350px;
            object-fit: cover;
        }
        .series h2 {
            padding: 15px;
            margin: 0;
            font-size: 16px;
            height: 50px;
            overflow: hidden;
        }
        .series p {
            padding: 0 15px 15px;
            margin: 0;
            color: #aaa;
            font-size: 14px;
        }
        .series a {
            text-decoration: none;
            color: inherit;
            display: block;
        }
        .season {
            background: #444;
            margin: 10px;
            padding: 10px;
            border-radius: 5px;
        }
        .season h3 {
            margin: 0 0 10px 0;
            color: #00b4d8;
        }
        .season ul {
            margin: 0;
            padding-left: 20px;
        }
        .season li {
            margin: 5px 0;
        }
        .season a {
            color: #90e0ef;
            text-decoration: none;
        }
        .season a:hover {
            text-decoration: underline;
        }
        .episodes-container {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }
        .year-section {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #444;
        }
        .year-title {
            color: #00b4d8;
            margin-bottom: 15px;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        .stat-box {
            background: #00b4d8;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            font-size: 14px;
        }
        .stat-box .number {
            font-size: 18px;
            font-weight: bold;
        }
        @media (max-width: 768px) {
            .series-grid {
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            }
            .stats {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Catálogo de Series</h1>
"""

# Procesar cada URL individualmente
urls_list = [url.strip() for url in urls_input.split(',') if url.strip()]
total_series_count = 0

for url_index, url in enumerate(urls_list, 1):
    print(f"\n{'='*50}")
    print(f"PROCESANDO URL {url_index}/{len(urls_list)}")
    print(f"URL: {url}")
    print('='*50)
    
    url_series_data = []
    
    if option == '1':
        # Extraer series de páginas de listado
        series_from_page = extract_series_from_page(url)
        if series_from_page:
            url_series_data.extend(series_from_page)
            print(f"✓ {len(series_from_page)} series extraídas de esta página")
    else:
        # Extraer serie específica
        series_data = extract_series_data(url)
        if series_data:
            if extract_episodes_option:
                episodes = extract_seasons_and_episodes(url)
                series_data['episodes'] = episodes
            
            url_series_data.append(series_data)
            print(f"✓ Serie '{series_data['title']}' extraída")
    
    # Si se extrajeron series de esta URL, guardar archivo individual
    if url_series_data:
        # Organizar por año para esta URL específica
        url_series_by_year = organize_by_year(url_series_data)
        
        # Guardar archivo JSON individual
        json_filename = f"{url_index}.json"
        save_to_json(url_series_by_year, json_filename)
        individual_files.append(json_filename)
        
        print(f"✓ Datos guardados en: {json_filename}")
        
        # Agregar al total combinado
        all_series_data.extend(url_series_data)
        total_series_count += len(url_series_data)
        
        # Agregar al HTML
        html_content += f'<div class="url-section">\n'
        html_content += f'<h2 class="url-title">\n'
        html_content += f'  🔗 Fuente {url_index}: {url[:50]}...\n'
        html_content += f'  <a href="{json_filename}" class="json-link" target="_blank">Descargar JSON ({json_filename})</a>\n'
        html_content += f'</h2>\n'
        
        # Estadísticas de esta URL
        total_url_series = len(url_series_data)
        total_url_years = len(url_series_by_year)
        
        html_content += f'<div class="stats">\n'
        html_content += f'  <div class="stat-box"><span class="number">{total_url_series}</span> series</div>\n'
        html_content += f'  <div class="stat-box"><span class="number">{total_url_years}</span> años</div>\n'
        html_content += f'</div>\n'
        
        # Mostrar series organizadas por año
        for year, year_series in url_series_by_year.items():
            html_content += f'<div class="year-section">\n'
            html_content += f'<h3 class="year-title">Año {year} ({len(year_series)} series)</h3>\n'
            html_content += f'<div class="series-grid">\n'
            
            for series in year_series:
                series_block = create_series_block(series, extract_episodes_option)
                html_content += series_block
            
            html_content += '</div>\n</div>\n'
        
        html_content += '</div>\n'  # Cerrar url-section
    
    else:
        print(f"⚠️ No se encontraron series en esta URL")
        html_content += f'<div class="url-section">\n'
        html_content += f'<h2 class="url-title">🔗 Fuente {url_index}: {url[:50]}...</h2>\n'
        html_content += f'<p style="color: #ff6b6b;">⚠️ No se encontraron series en esta URL</p>\n'
        html_content += '</div>\n'
    
    # Pequeña pausa entre URLs
    if url_index < len(urls_list):
        print(f"Esperando 2 segundos antes de la próxima URL...")
        time.sleep(2)

# Guardar archivo JSON combinado si hay múltiples URLs
if len(individual_files) > 1 and all_series_data:
    combined_series_by_year = organize_by_year(all_series_data)
    save_to_json(combined_series_by_year, 'todas_las_series.json')
    print(f"\n✓ Archivo combinado guardado en: todas_las_series.json")
    
    # Agregar enlace al archivo combinado en el HTML
    html_content += f'<div class="url-section" style="background: #003049; border-left-color: #ff9e00;">\n'
    html_content += f'<h2 class="url-title" style="color: #ff9e00;">📊 RESUMEN TOTAL</h2>\n'
    html_content += f'<div class="stats">\n'
    html_content += f'  <div class="stat-box" style="background: #ff9e00;"><span class="number">{total_series_count}</span> series totales</div>\n'
    html_content += f'  <div class="stat-box" style="background: #ff9e00;"><span class="number">{len(organize_by_year(all_series_data))}</span> años distintos</div>\n'
    html_content += f'  <div class="stat-box" style="background: #ff9e00;"><span class="number">{len(urls_list)}</span> URLs procesadas</div>\n'
    html_content += f'</div>\n'
    html_content += f'<p style="margin-top: 15px;">\n'
    html_content += f'  <a href="todas_las_series.json" class="json-link" style="background: #ff9e00;" target="_blank">📥 Descargar JSON combinado (todas_las_series.json)</a>\n'
    html_content += f'</p>\n'
    html_content += '</div>\n'

# Cerrar HTML
html_content += """
    </div>
    <script>
        function toggleEpisodes(element) {
            const episodesContainer = element.querySelector('.episodes-container');
            if (episodesContainer.style.maxHeight) {
                episodesContainer.style.maxHeight = null;
            } else {
                episodesContainer.style.maxHeight = episodesContainer.scrollHeight + "px";
            }
        }

        // Añadir evento click a todas las series con episodios
        document.querySelectorAll('.series').forEach(series => {
            if (series.querySelector('.episodes-container')) {
                series.addEventListener('click', function(e) {
                    // Evitar que se active cuando se hace click en un enlace
                    if (e.target.tagName !== 'A') {
                        toggleEpisodes(this);
                    }
                });
            }
        });
        
        // Mostrar notificación de archivos generados
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Catálogo de series cargado correctamente');
        });
    </script>
</body>
</html>
"""

# Guardar HTML
with open(html_filename, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n✓ Catálogo HTML guardado en: {html_filename}")

# Resumen final
print("\n" + "="*60)
print("RESUMEN FINAL:")
print("="*60)
print(f"Total de URLs procesadas: {len(urls_list)}")
print(f"Total de series extraídas: {total_series_count}")

if individual_files:
    print("\nArchivos JSON generados:")
    for json_file in individual_files:
        print(f"  • {json_file}")
    
    if len(individual_files) > 1:
        print(f"  • todas_las_series.json (combinado)")

print(f"\nArchivo HTML generado:")
print(f"  • {html_filename}")

print("\n" + "="*60)
print("✅ Extracción completada exitosamente!")
print("="*60)
