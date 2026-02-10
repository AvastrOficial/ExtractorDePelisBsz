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

def extract_episodes_from_series(series_url):
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
                        episodes = extract_episodes_from_ul(episodes_list, series_url)
                        if episodes:
                            episodes_data[season_id] = episodes
                            print(f"    ✅ Temporada {season_value}: {len(episodes)} episodios")
                    else:
                        # Intentar buscar cualquier lista con episodios
                        all_lists = soup.find_all('ul', class_='all-episodes')
                        if all_lists:
                            season_num = int(season_value) if season_value.isdigit() else 1
                            if len(all_lists) >= season_num:
                                episodes = extract_episodes_from_ul(all_lists[season_num-1], series_url)
                                if episodes:
                                    episodes_data[season_id] = episodes
                                    print(f"    ✅ Temporada {season_value}: {len(episodes)} episodios (por índice)")
        else:
            # Si no hay selector, buscar episodios directamente
            episodes_list = soup.find('ul', class_='all-episodes')
            if not episodes_list:
                # Intentar con otra clase
                episodes_list = soup.find('ul', class_='episodes')

            if episodes_list:
                episodes = extract_episodes_from_ul(episodes_list, series_url)
                if episodes:
                    episodes_data['season-1'] = episodes
                    print(f"  ✅ Encontrados {len(episodes)} episodios")
            else:
                print(f"  ⚠️ No se encontró lista de episodios")

        return episodes_data

    except Exception as e:
        print(f"  ❌ Error extrayendo episodios: {e}")
        return {}

def extract_episodes_from_ul(episodes_list, base_url):
    """Extrae episodios de una lista UL"""
    episodes = []

    # Buscar todos los items de episodio
    episode_items = episodes_list.find_all('li', class_=lambda x: x and 'TPost' in x)

    if not episode_items:
        # Intentar con cualquier li
        episode_items = episodes_list.find_all('li')

    print(f"    Encontrados {len(episode_items)} items de episodio")

    for item in episode_items:
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

            episodes.append({
                'title': episode_title,
                'episode_number': episode_num,
                'url': episode_url,
                'image_url': episode_img
            })

        except Exception as e:
            continue

    return episodes

def save_to_json(data, filename):
    """Guarda datos en formato JSON"""
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def extract_series_from_listing_page(page_url, extract_episodes=False):
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
            print(f"    [{idx}/{len(series_links)}] Procesando serie...")

            try:
                # Extraer datos básicos
                series_data = extract_series_data(series_url)
                if series_data:
                    # Extraer episodios si se solicita
                    if extract_episodes:
                        print(f"      ⏳ Extrayendo episodios...")
                        episodes = extract_episodes_from_series(series_url)
                        if episodes:
                            series_data['episodes'] = episodes
                            print(f"      ✅ {sum(len(eps) for eps in episodes.values())} episodios extraídos")
                        else:
                            print(f"      ⚠️ No se encontraron episodios")

                    series_list.append(series_data)
                    print(f"      ✅ '{series_data['title'][:30]}...' extraída")
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
print("EXTRACTOR DE SERIES CUEVANA")
print("=" * 60)

# Preguntar qué extraer
print("\n¿Qué deseas extraer?")
print("1. Series de páginas de listado (ej: /serie/, /serie/page/2)")
print("2. Series específicas con episodios")
print("3. Solo información básica de series")

option = input("\nSelecciona una opción (1-3): ").strip()

# Preguntar si extraer episodios para opción 1
extract_episodes_option = False
if option == '2':
    extract_episodes_option = True
elif option == '1':
    print("\n📺 ¿Deseas extraer también los episodios de cada serie?")
    print("   Esto tomará MUCHO más tiempo (1-2 segundos por serie)")
    print("   pero obtendrás la información completa de temporadas y episodios.")

    episodes_choice = input("   ¿Extraer episodios? (s/n): ").strip().lower()
    if episodes_choice == 's':
        extract_episodes_option = True
        print("   ⚠️  ADVERTENCIA: Esto puede tomar varios minutos dependiendo de la cantidad de series.")
        print("   Se recomienda procesar pocas series a la vez (máximo 10).")
        confirm = input("   ¿Continuar? (s/n): ").strip().lower()
        if confirm != 's':
            extract_episodes_option = False
            print("   ✅ Solo se extraerá información básica de series.")

# Solicitar URLs
if option == '1':
    print("\n📥 Introduce URLs de páginas de listado (separadas por comas):")
    print("   Ejemplo: https://ww9.cuevana3.to/serie/")
    print("            https://ww9.cuevana3.to/serie/page/2")

    if extract_episodes_option:
        print("\n   💡 CONSEJO: Procesa solo 1-2 páginas para no sobrecargar el servidor.")
else:
    print("\n📥 Introduce URLs de series específicas (separadas por comas):")
    print("   Ejemplo: https://ww9.cuevana3.to/serie/playing-gracie-darling")
    print("            https://ww9.cuevana3.to/serie/wonder-man")

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
    <title>Catálogo de Series - Cuevana</title>
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
        .url-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .url-title {
            color: #00b4d8;
            margin: 0;
        }
        .json-link {
            background: #00b4d8;
            color: white;
            padding: 8px 15px;
            border-radius: 5px;
            text-decoration: none;
            font-size: 14px;
        }
        .json-link:hover {
            background: #0093b3;
        }
        .stats {
            display: flex;
            gap: 15px;
            margin: 15px 0;
        }
        .stat {
            background: #333;
            padding: 10px 15px;
            border-radius: 5px;
            text-align: center;
        }
        .stat .number {
            font-size: 20px;
            font-weight: bold;
            color: #00b4d8;
            display: block;
        }
        .stat .label {
            font-size: 12px;
            color: #aaa;
        }
        .series-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .series-card {
            background: #333;
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #444;
        }
        .series-card:hover {
            border-color: #00b4d8;
        }
        .series-img {
            width: 100%;
            height: 400px;
            object-fit: cover;
        }
        .series-info {
            padding: 15px;
        }
        .series-title {
            font-size: 18px;
            margin: 0 0 10px 0;
            color: white;
        }
        .series-meta {
            color: #aaa;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .series-desc {
            color: #888;
            font-size: 13px;
            line-height: 1.4;
            margin-bottom: 15px;
        }
        .episodes-section {
            background: #3a3a3a;
            margin: 10px;
            padding: 15px;
            border-radius: 8px;
            display: none;
        }
        .episodes-section.show {
            display: block;
        }
        .season-title {
            color: #00b4d8;
            margin-top: 0;
            font-size: 16px;
        }
        .episode-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .episode-item {
            padding: 8px 0;
            border-bottom: 1px solid #444;
        }
        .episode-item:last-child {
            border-bottom: none;
        }
        .episode-link {
            color: #90e0ef;
            text-decoration: none;
            display: block;
        }
        .episode-link:hover {
            color: #00b4d8;
            text-decoration: underline;
        }
        .toggle-episodes {
            background: #444;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 10px;
        }
        .toggle-episodes:hover {
            background: #555;
        }
        .summary {
            background: #2a2a2a;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            margin-top: 30px;
            border: 2px solid #00b4d8;
        }
        .summary-title {
            color: #00b4d8;
            margin-top: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Catálogo de Series - Cuevana</h1>
"""

# Procesar cada URL individualmente
urls_list = [url.strip() for url in urls_input.split(',') if url.strip()]
total_series_count = 0
total_episodes_count = 0

for url_index, url in enumerate(urls_list, 1):
    print(f"\n{'='*60}")
    print(f"📁 PROCESANDO URL {url_index}/{len(urls_list)}")
    print(f"🔗 {url}")
    print('='*60)

    url_series_data = []

    if option == '1':
        # Extraer series de página de listado
        print(f"⏳ Extrayendo series de la página de listado...")
        series_from_page = extract_series_from_listing_page(url, extract_episodes_option)

        if series_from_page:
            url_series_data.extend(series_from_page)

            # Contar episodios si se extrajeron
            episodes_count = 0
            for series in series_from_page:
                if 'episodes' in series:
                    for season_episodes in series['episodes'].values():
                        episodes_count += len(season_episodes)

            if extract_episodes_option and episodes_count > 0:
                print(f"✅ {len(series_from_page)} series con {episodes_count} episodios extraídos")
            else:
                print(f"✅ {len(series_from_page)} series extraídas (sin episodios)")
    else:
        # Extraer serie específica
        print(f"⏳ Extrayendo serie específica...")
        series_data = extract_series_data(url)
        if series_data:
            if extract_episodes_option:
                print(f"⏳ Extrayendo episodios...")
                episodes = extract_episodes_from_series(url)
                if episodes:
                    series_data['episodes'] = episodes
                    episodes_count = sum(len(eps) for eps in episodes.values())
                    total_episodes_count += episodes_count
                    print(f"✅ Serie con {episodes_count} episodios extraída")
                else:
                    print(f"⚠️ Serie sin episodios encontrados")

            url_series_data.append(series_data)
            print(f"✅ Serie '{series_data['title']}' extraída")

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

        # Agregar al HTML
        html_content += f'<div class="url-section">\n'
        html_content += f'<div class="url-header">\n'
        html_content += f'<h2 class="url-title">📦 Fuente {url_index}: {url[:50]}...</h2>\n'
        html_content += f'<a href="{json_filename}" class="json-link" target="_blank">📥 Descargar JSON</a>\n'
        html_content += f'</div>\n'

        # Estadísticas de esta URL
        total_url_series = len(url_series_data)
        total_url_years = len(url_series_by_year)

        # Contar episodios para esta URL
        url_episodes_count = 0
        for series in url_series_data:
            if 'episodes' in series:
                for season_episodes in series['episodes'].values():
                    url_episodes_count += len(season_episodes)

        html_content += f'<div class="stats">\n'
        html_content += f'<div class="stat"><span class="number">{total_url_series}</span><span class="label">Series</span></div>\n'
        html_content += f'<div class="stat"><span class="number">{total_url_years}</span><span class="label">Años</span></div>\n'
        if url_episodes_count > 0:
            html_content += f'<div class="stat"><span class="number">{url_episodes_count}</span><span class="label">Episodios</span></div>\n'
        html_content += f'</div>\n'

        # Mostrar series
        html_content += f'<div class="series-grid">\n'

        for series in url_series_data:
            has_episodes = 'episodes' in series and series['episodes']

            html_content += f'<div class="series-card">\n'
            html_content += f'<img src="{series.get("image_url", "")}" alt="{series["title"]}" class="series-img" onerror="this.src=\'https://via.placeholder.com/300x400/333/fff?text=No+Image\'">\n'
            html_content += f'<div class="series-info">\n'
            html_content += f'<h3 class="series-title">{series["title"]}</h3>\n'
            html_content += f'<div class="series-meta">Año: {series.get("year", "N/A")} | Rating: {series.get("rating", "N/A")}</div>\n'

            if series.get('description'):
                html_content += f'<div class="series-desc">{series["description"][:150]}...</div>\n'

            if has_episodes:
                episodes_html = ""
                for season_id, episodes in series['episodes'].items():
                    episodes_html += f'<h4 class="season-title">{season_id}</h4>\n'
                    episodes_html += f'<ul class="episode-list">\n'
                    for episode in episodes[:5]:  # Mostrar solo 5 episodios
                        ep_title = episode["title"][:40] + "..." if len(episode["title"]) > 40 else episode["title"]
                        episodes_html += f'<li class="episode-item"><a href="{episode["url"]}" class="episode-link" target="_blank">{episode["episode_number"]} - {ep_title}</a></li>\n'

                    if len(episodes) > 5:
                        episodes_html += f'<li class="episode-item">... y {len(episodes) - 5} episodios más</li>\n'

                    episodes_html += f'</ul>\n'

                html_content += f'<button class="toggle-episodes" onclick="toggleEpisodes(this)">📺 Mostrar Episodios</button>\n'
                html_content += f'<div class="episodes-section">\n'
                html_content += episodes_html
                html_content += f'</div>\n'

            html_content += f'</div>\n'
            html_content += f'</div>\n'

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

    # Agregar resumen al HTML
    html_content += f'<div class="summary">\n'
    html_content += f'<h2 class="summary-title">📊 RESUMEN TOTAL</h2>\n'
    html_content += f'<div class="stats" style="justify-content: center;">\n'
    html_content += f'<div class="stat"><span class="number">{total_series_count}</span><span class="label">Series totales</span></div>\n'
    html_content += f'<div class="stat"><span class="number">{len(organize_by_year(all_series_data))}</span><span class="label">Años distintos</span></div>\n'
    html_content += f'<div class="stat"><span class="number">{len(urls_list)}</span><span class="label">URLs procesadas</span></div>\n'
    if total_episodes_count > 0:
        html_content += f'<div class="stat"><span class="number">{total_episodes_count}</span><span class="label">Episodios totales</span></div>\n'
    html_content += f'</div>\n'
    html_content += f'<p style="margin-top: 20px;">\n'
    html_content += f'<a href="todas_las_series.json" class="json-link" target="_blank">📦 Descargar JSON completo (todas_las_series.json)</a>\n'
    html_content += f'</p>\n'
    html_content += f'</div>\n'

# Cerrar HTML
html_content += """
    </div>
    <script>
        function toggleEpisodes(button) {
            const episodesSection = button.nextElementSibling;
            if (episodesSection.classList.contains('show')) {
                episodesSection.classList.remove('show');
                button.textContent = '📺 Mostrar Episodios';
            } else {
                episodesSection.classList.add('show');
                button.textContent = '📺 Ocultar Episodios';
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
print("📋 RESUMEN FINAL")
print("="*60)
print(f"🌐 URLs procesadas: {len(urls_list)}")
print(f"🎬 Series extraídas: {total_series_count}")

if total_episodes_count > 0:
    print(f"📺 Episodios encontrados: {total_episodes_count}")

if individual_files:
    print("\n📄 Archivos JSON generados:")
    for json_file in individual_files:
        print(f"  • {json_file}")

    if len(individual_files) > 1:
        print(f"  • todas_las_series.json (combinado)")

print(f"\n🖥️  Visualización:")
print(f"  • {html_filename} (abrir en navegador)")

print("\n" + "="*60)
print("✅ ¡Extracción completada exitosamente!")
print("="*60)
