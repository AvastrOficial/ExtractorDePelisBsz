import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

BASE_URL = "https://ww9.cuevana3.to"

def extract_data(page_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(page_url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a {page_url}: {e}")
        return None, None, None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Buscar imagen
    img_tag = soup.find('img', class_='lazy')
    if not img_tag:
        img_tag = soup.find('img', {'loading': 'lazy'})
    if not img_tag:
        img_tag = soup.find('img', {'data-src': True})
    
    img_url = urljoin(page_url, img_tag.get('data-src')) if img_tag and img_tag.get('data-src') else None
    if not img_url and img_tag:
        img_url = urljoin(page_url, img_tag.get('src')) if img_tag.get('src') else None

    # Buscar iframe
    iframe_tag = soup.find('iframe', class_='no-you')
    if not iframe_tag:
        iframe_tag = soup.find('iframe', {'data-src': True})
    
    iframe_url = iframe_tag.get('data-src') if iframe_tag and iframe_tag.get('data-src') else None
    if not iframe_url and iframe_tag:
        iframe_url = iframe_tag.get('src') if iframe_tag.get('src') else None

    # Extraer título
    title = None
    title_tag = soup.find('h1')
    if title_tag:
        title = title_tag.get_text(strip=True)
    
    if not title:
        title = page_url.strip('/').split('/')[-1].replace('-', ' ').title()
    
    return img_url, iframe_url, title

def extract_links_from_category(category_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(category_url.strip(), headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a la URL: {category_url}. {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    movie_links = []

    # Buscar la lista de películas
    movie_list_container = soup.find('ul', class_='MovieList Rows AX A06 B04 C03 E20')
    
    if not movie_list_container:
        # Intentar otras posibles clases
        movie_list_container = soup.find('div', class_='MovieList')
    
    if not movie_list_container:
        print(f"No se encontró la lista de películas en {category_url}")
        return movie_links

    # Buscar elementos de película
    movie_tags = movie_list_container.find_all('li', class_='xxx TPostMv')
    
    if not movie_tags:
        # Intentar otras clases
        movie_tags = movie_list_container.find_all(class_='TPostMv')
    
    if not movie_tags:
        # Buscar todos los enlaces dentro del contenedor
        all_links = movie_list_container.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            if href and ('/pelicula/' in href or '/serie/' in href):
                full_link = urljoin(BASE_URL, href)
                movie_links.append(full_link)
        return movie_links
    
    for tag in movie_tags:
        link_tag = tag.find('a')
        if link_tag:
            href = link_tag.get('href')
            if href:
                full_link = urljoin(BASE_URL, href)
                movie_links.append(full_link)

    return movie_links

def create_movie_block(data):
    if not data['iframe_url'] or not data['image_url']:
        return ""
    
    # Escapar comillas
    iframe_url = data['iframe_url'].replace("'", "\\'") if data['iframe_url'] else ''
    image_url = data['image_url'].replace("'", "\\'") if data['image_url'] else ''
    title = data['title'].replace("'", "\\'") if data['title'] else 'Sin título'
    
    movie_block = f"""
    <div class="movie" onclick="openMovie('{iframe_url}')">
        <img src="{image_url}" alt="{title}">
        <h2>{title}</h2>
    </div>
    """
    return movie_block

def save_html_block(html_block, filename):
    with open(filename, 'a', encoding='utf-8') as file:
        file.write(html_block)

def parse_urls_input(urls_input):
    """Parsea correctamente las URLs separadas por comas, incluyendo multilínea"""
    # Reemplazar saltos de línea por comas y luego dividir
    urls_input = urls_input.replace('\n', ',')
    
    urls = []
    for url in urls_input.split(','):
        url = url.strip()
        if url and url.startswith('http'):
            urls.append(url)
    
    return urls

def main():
    print("=" * 60)
    print("EXTRACTOR DE PELÍCULAS CUEVANA")
    print("=" * 60)
    
    while True:
        print("\n" + "-" * 40)
        print("Seleccione una opción:")
        print("1. Ejecutar con URLs de películas individuales")
        print("2. Ejecutar con URLs de categorías/páginas de listado")
        print("3. Probar extracción de categorías")
        print("0. Salir")
        print("-" * 40)
        
        try:
            choice = input("Opción: ").strip()
        except KeyboardInterrupt:
            print("\n\nSaliendo...")
            break
        except:
            print("Error de entrada")
            continue

        if choice == "1":
            print("\n" + "=" * 40)
            print("EXTRACCIÓN DE PELÍCULAS INDIVIDUALES")
            print("=" * 40)
            
            page_urls_input = input("\nIntroduce las URLs de películas, separadas por comas:\n> ")
            urls_list = parse_urls_input(page_urls_input)
            
            print(f"\nURLs parseadas: {len(urls_list)}")
            for i, url in enumerate(urls_list, 1):
                print(f"  {i}. {url}")
            
            if not urls_list:
                print("No se encontraron URLs válidas.")
                continue
            
            # Limpiar archivo de salida
            open('code.txt', 'w', encoding='utf-8').close()
            
            movie_count = 0
            block_number = 1
            html_block = f'<div id="linea-{block_number}" class="movies-grid">\n'
            
            print(f"\nProcesando {len(urls_list)} URLs...")
            
            for i, page_url in enumerate(urls_list, 1):
                print(f"\n[{i}/{len(urls_list)}] Procesando: {page_url}")
                
                img_url, iframe_url, title = extract_data(page_url)
                
                print(f"  Imagen: {'✓' if img_url else '✗'}")
                print(f"  Iframe: {'✓' if iframe_url else '✗'}")
                print(f"  Título: {title[:50]}{'...' if len(title) > 50 else ''}")

                if img_url and iframe_url and title:
                    movie_count += 1
                    data = {
                        'image_url': img_url,
                        'iframe_url': iframe_url,
                        'title': title
                    }

                    movie_block = create_movie_block(data)
                    if movie_block:
                        html_block += movie_block

                        if movie_count % 15 == 0:
                            html_block += '\n</div>\n'
                            save_html_block(html_block, 'code.txt')
                            block_number += 1
                            html_block = f'<div id="linea-{block_number}" class="movies-grid">\n'
                        
                        print(f"  ✓ Película {movie_count} agregada")
                    else:
                        print(f"  ✗ No se pudo crear bloque")
                else:
                    print(f"  ✗ Datos incompletos, se omite")
                
                time.sleep(0.5)

            if movie_count > 0 and movie_count % 15 != 0:
                html_block += '\n</div>\n'
                save_html_block(html_block, 'code.txt')

            print(f"\n{'='*40}")
            print(f"PROCESO COMPLETADO")
            print(f"Películas procesadas exitosamente: {movie_count}/{len(urls_list)}")
            print("Datos guardados en 'code.txt'")

        elif choice == "2":
            print("\n" + "=" * 40)
            print("EXTRACCIÓN DESDE CATEGORÍAS")
            print("=" * 40)
            
            print("\nIntroduce las URLs de categorías, separadas por comas:")
            print("(Puedes pegar múltiples líneas, presiona Enter dos veces para terminar)")
            print("-" * 60)
            
            # Leer múltiples líneas de entrada
            lines = []
            while True:
                try:
                    line = input()
                    if line.strip() == "":
                        # Si se presiona Enter dos veces seguidas, terminar
                        if not lines or lines[-1].strip() == "":
                            break
                    lines.append(line)
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\nEntrada cancelada")
                    return
            
            # Unir todas las líneas
            category_urls_input = ','.join(lines)
            
            urls_list = parse_urls_input(category_urls_input)
            
            print(f"\nURLs parseadas: {len(urls_list)}")
            for i, url in enumerate(urls_list, 1):
                print(f"  {i}. {url}")
            
            if not urls_list:
                print("No se encontraron URLs válidas.")
                continue
            
            # Limpiar archivo de salida
            open('code.txt', 'w', encoding='utf-8').close()
            
            movie_count = 0
            block_number = 1
            total_movies_found = 0
            html_block = f'<div id="linea-{block_number}" class="movies-grid">\n'
            
            print(f"\nProcesando {len(urls_list)} categorías...")
            
            for cat_index, category_url in enumerate(urls_list, 1):
                print(f"\n{'='*60}")
                print(f"[CATEGORÍA {cat_index}/{len(urls_list)}]")
                print(f"URL: {category_url}")
                print('='*60)

                movie_links = extract_links_from_category(category_url)
                print(f"\nPelículas encontradas en esta categoría: {len(movie_links)}")
                total_movies_found += len(movie_links)
                
                if not movie_links:
                    print("  No se encontraron películas, se salta esta categoría")
                    continue
                
                print(f"\nProcesando {len(movie_links)} películas de esta categoría...")
                
                for i, movie_url in enumerate(movie_links, 1):
                    if i % 10 == 0 or i == 1 or i == len(movie_links):
                        print(f"  [{i}/{len(movie_links)}] Procesando película...")
                    
                    img_url, iframe_url, title = extract_data(movie_url)

                    if img_url and iframe_url and title:
                        movie_count += 1
                        data = {
                            'image_url': img_url,
                            'iframe_url': iframe_url,
                            'title': title
                        }

                        movie_block = create_movie_block(data)
                        if movie_block:
                            html_block += movie_block

                            if movie_count % 15 == 0:
                                html_block += '\n</div>\n'
                                save_html_block(html_block, 'code.txt')
                                block_number += 1
                                html_block = f'<div id="linea-{block_number}" class="movies-grid">\n'
                            
                            if i % 10 == 0 or i == 1 or i == len(movie_links):
                                print(f"    ✓ Película {movie_count} agregada: {title[:40]}...")
                        else:
                            if i % 10 == 0 or i == 1 or i == len(movie_links):
                                print(f"    ✗ No se pudo crear bloque para: {title[:40]}...")
                    else:
                        if i % 10 == 0 or i == 1 or i == len(movie_links):
                            print(f"    ✗ Datos incompletos, se omite")
                    
                    time.sleep(0.3)
                
                print(f"\nCategoría {cat_index} completada: {len(movie_links)} películas procesadas")
                time.sleep(1)

            if movie_count > 0 and movie_count % 15 != 0:
                html_block += '\n</div>\n'
                save_html_block(html_block, 'code.txt')

            print(f"\n{'='*60}")
            print(f"RESUMEN FINAL")
            print('='*60)
            print(f"Categorías procesadas: {len(urls_list)}")
            print(f"Enlaces de películas encontrados: {total_movies_found}")
            print(f"Películas procesadas exitosamente: {movie_count}")
            print(f"Películas no procesadas: {total_movies_found - movie_count}")
            print(f"Bloques creados: {block_number}")
            print("="*60)
            print("Datos guardados en 'code.txt'")

        elif choice == "3":
            print("\n" + "=" * 40)
            print("PRUEBA DE EXTRACCIÓN DE CATEGORÍAS")
            print("=" * 40)
            
            test_url = input("\nIntroduce una URL de categoría para probar:\n> ").strip()
            
            if test_url:
                print(f"\nProcesando URL: {test_url}")
                print("-" * 40)
                
                links = extract_links_from_category(test_url)
                print(f"\nPelículas encontradas: {len(links)}")
                
                if links:
                    print("\nPrimeras 10 películas encontradas:")
                    for j, link in enumerate(links[:10], 1):
                        print(f"  {j}. {link}")
                    
                    if len(links) > 10:
                        print(f"  ... y {len(links)-10} más")
                    
                    # Probar extraer datos de la primera película
                    if links:
                        print(f"\nProbando extracción de la primera película:")
                        print(f"URL: {links[0]}")
                        img_url, iframe_url, title = extract_data(links[0])
                        print(f"  Título: {title}")
                        print(f"  Imagen: {'✓' if img_url else '✗'}")
                        print(f"  Iframe: {'✓' if iframe_url else '✗'}")
                else:
                    print("No se encontraron películas en esta categoría.")

        elif choice == "0":
            print("\nSaliendo del programa...")
            break
        else:
            print("Opción no válida. Por favor, intente de nuevo.")

if __name__ == "__main__":
    main()
