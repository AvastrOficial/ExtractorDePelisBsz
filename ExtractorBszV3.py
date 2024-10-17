import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://ww8.cuevana3.to"

def extract_data(page_url):
    response = requests.get(page_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    img_tag = soup.find('img', class_='lazy')
    img_url = urljoin(page_url, img_tag.get('data-src')) if img_tag else None

    iframe_tag = soup.find('iframe', class_='no-you')
    iframe_url = iframe_tag.get('data-src') if iframe_tag else None

    title_from_url = page_url.strip('/').split('/')[-1].replace('-', ' ').title()

    return img_url, iframe_url, title_from_url

def extract_links_from_category(category_url):
    response = requests.get(category_url.strip())
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    movie_links = []

    # Buscar la lista de películas dentro de la clase de contenedor
    movie_list_container = soup.find('ul', class_='MovieList Rows AX A06 B04 C03 E20')
    if not movie_list_container:
        print(f"No se encontró la lista de películas en {category_url}")
        return movie_links

    movie_tags = movie_list_container.find_all('li', class_='xxx TPostMv')
    for tag in movie_tags:
        href = tag.find('a').get('href')
        if href:
            full_link = urljoin(BASE_URL, href)
            movie_links.append(full_link)

    return movie_links

def create_movie_block(data):
    movie_block = f"""
    <div class="movie" onclick="openMovie('{data['iframe_url']}')">
        <img src="{data['image_url']}" alt="Película">
        <h2>{data['title']}</h2>
    </div>
    """
    return movie_block

def save_html_block(html_block, filename):
    # Abrir el archivo en modo 'append' para agregar contenido
    with open(filename, 'a', encoding='utf-8') as file:
        file.write(html_block)

def generate_category_urls(base_url, category_name, page_count):
    urls = []
    for page in range(1, page_count + 1):
        # Construir la URL con el número de página
        url = f"{base_url}/{category_name}/page/{page}"
        urls.append(url)
    return urls

def main():
    while True:
        print("Seleccione una opción:")
        print("1. Ejecutar la herramienta con URLs de películas")
        print("2. Ejecutar la herramienta con URLs de categorías")
        print("3. Generar URLs de categorías")
        print("0. Salir")
        choice = input("Opción: ").strip()

        if choice == "1":
            page_urls = input("Introduce las URLs de las páginas a analizar, separadas por comas: ")
            movie_count = 0
            block_number = 1
            html_block = f'<div id="linea-{block_number}" class="movies-grid">\n'

            for page_url in page_urls.split(','):
                page_url = page_url.strip()

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

                    if movie_count % 15 == 0:
                        html_block += '\n</div>\n'
                        save_html_block(html_block, 'code.txt')
                        block_number += 1
                        html_block = f'<div id="linea-{block_number}" class="movies-grid">\n'

            if movie_count % 15 != 0:
                html_block += '\n</div>\n'
                save_html_block(html_block, 'code.txt')

            print("Proceso completado. Los datos han sido guardados en 'code.txt'.")

        elif choice == "2":
            category_urls = input("Introduce las URLs de las categorías a analizar, separadas por comas: ")
            movie_count = 0
            block_number = 1
            html_block = f'<div id="linea-{block_number}" class="movies-grid">\n'

            for category_url in category_urls.split(','):
                category_url = category_url.strip()

                # Verifica que la URL no esté vacía
                if not category_url:
                    continue

                try:
                    movie_links = extract_links_from_category(category_url)
                except requests.exceptions.RequestException as e:
                    print(f"Error al acceder a la URL: {category_url}. {e}")
                    continue

                for movie_url in movie_links:
                    img_url, iframe_url, title = extract_data(movie_url)

                    if img_url and iframe_url and title:
                        movie_count += 1
                        data = {
                            'image_url': img_url,
                            'iframe_url': iframe_url,
                            'title': title
                        }

                        movie_block = create_movie_block(data)
                        html_block += movie_block

                        if movie_count % 15 == 0:
                            html_block += '\n</div>\n'
                            save_html_block(html_block, 'code.txt')
                            block_number += 1
                            html_block = f'<div id="linea-{block_number}" class="movies-grid">\n'

            if movie_count > 0 and movie_count % 15 != 0:
                html_block += '\n</div>\n'
                save_html_block(html_block, 'code.txt')

            print("Proceso completado. Los datos han sido guardados en 'code.txt'.")

        elif choice == "3":
            base_url = input("Ingrese la URL base de la categoría (ejemplo: https://ww8.cuevana3.to/category): ").strip()
            category_name = input("Ingrese el nombre de la categoría (ejemplo: guerra): ").strip()
            page_count = int(input("Ingrese el número de páginas a generar: ").strip())

            # Generar las URLs
            generated_urls = generate_category_urls(base_url, category_name, page_count)
            formatted_urls = ", ".join(generated_urls)

            # Guardar las URLs en un archivo
            with open('url_generados.txt', 'w', encoding='utf-8') as file:
                file.write(formatted_urls)

            print(f"URLs generados y guardados en 'url_generados.txt': {formatted_urls}")

        elif choice == "0":
            print("Saliendo...")
            break
        else:
            print("Opción no válida. Por favor, intente de nuevo.")

if __name__ == "__main__":
    main()
