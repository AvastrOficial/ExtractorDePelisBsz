import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os

def extract_data(page_url):
    response = requests.get(page_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    img_tag = soup.find('img', class_='lazy')
    img_url = urljoin(page_url, img_tag.get('data-src')) if img_tag else None

    iframe_tag = soup.find('iframe', class_='no-you')
    iframe_url = iframe_tag.get('data-src') if iframe_tag else None

    # Extraer el nombre desde la URL para usar como título
    title_from_url = page_url.strip('/').split('/')[-1].replace('-', ' ').title()

    return img_url, iframe_url, title_from_url

def download_image(img_url, folder_path, filename):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    response = requests.get(img_url, stream=True)
    response.raise_for_status()

    file_path = os.path.join(folder_path, filename)
    with open(file_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

def save_to_json(data, filename):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def create_movie_block(data):
    movie_block = f"""
    <div class="movie" onclick="openMovie('{data['iframe_url']}')">
        <img src="{data['image_url']}" alt="Película">
        <h2>{data['title']}</h2>
    </div>
    """
    return movie_block

def save_html_block(html_block, filename):
    with open(filename, 'a') as file:  # Usar 'a' para agregar contenido al archivo existente
        file.write(html_block)

# Solicitar al usuario las URLs de las páginas
page_urls = input("Introduce las URLs de las páginas a analizar, separadas por comas: ")

# Contadores
movie_count = 0
block_number = 1

# Abrir el primer bloque
html_block = f'<div id="linea-{block_number}" class="movies-grid">\n'

# Procesar cada URL por separado
for page_url in page_urls.split(','):
    page_url = page_url.strip()  # Eliminar espacios en blanco alrededor de la URL

    # Extraer la URL de la imagen, del iframe y el título
    img_url, iframe_url, title = extract_data(page_url)

    if img_url and iframe_url and title:
        movie_count += 1

        data = {
            'image_url': img_url,
            'iframe_url': iframe_url,
            'title': title
        }

        movie_block = create_movie_block(data)
        html_block += movie_block

        # Cada 15 películas, cerrar el bloque actual y abrir uno nuevo
        if movie_count % 15 == 0:
            html_block += '\n</div>\n'
            save_html_block(html_block, 'code.txt')

            block_number += 1
            html_block = f'<div id="linea-{block_number}" class="movies-grid">\n'

# Cerrar el último bloque si no está cerrado
if movie_count % 15 != 0:
    html_block += '\n</div>\n'
    save_html_block(html_block, 'code.txt')
