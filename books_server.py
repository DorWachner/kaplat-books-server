import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

# Global variables to store books and book ID counter
books = []
book_id_counter = 1

ALLOWED_GENRES = ["SCI_FI", "NOVEL", "HISTORY", "MANGA", "ROMANCE", "PROFESSIONAL"]

class BookStoreHandler(BaseHTTPRequestHandler):

    def _send_response(self, response_code, response_data):
        self.send_response(response_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode())

    def do_GET(self):
        if self.path == '/books/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        elif self.path.startswith('/books/total'):
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            self._handle_get_total_books(query_components)
        elif self.path.startswith('/books'):
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            self._handle_get_books_data(query_components)
        elif self.path.startswith('/book'):
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            self._handle_get_single_book_data(query_components)
        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        if self.path == '/book':
            global book_id_counter
            content_length = int(self.headers['Content-Length'])
            if content_length == 0:
                self._send_response(400, {"errorMessage": "Error: Request body is empty"})
                return
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            title = data.get('title')
            author = data.get('author')
            year = data.get('year')
            price = data.get('price')
            genres = data.get('genres', [])

            if title is not None:
                title = title.strip()
            if author is not None:
                author = author.strip()

            # Validation
            if not title or not author or not year or not price or not genres:
                self._send_response(400, {"errorMessage": "Error: Missing required book information"})
                return

            if not (1940 <= year <= 2100):
                self._send_response(409, {"errorMessage": f"Error: Canג€™t create new Book that its year [{year}] is not in the accepted range [1940 -> 2100]"})
                return

            if price <= 0:
                self._send_response(409, {"errorMessage": "Error: Canג€™t create new Book with negative price"})
                return

            # Check for duplicate title
            for book in books:
                if book['title'].lower() == title.lower():
                    self._send_response(409, {"errorMessage": f"Error: Book with the title [{title}] already exists in the system"})
                    return

            # Validate genres
            if not all(genre in ALLOWED_GENRES for genre in genres):
                self._send_response(400, {"errorMessage": "Error: Invalid genre in the list"})
                return

            # Create and store the new book
            new_book = {
                'id': book_id_counter,
                'title': title,
                'author': author,
                'year': year,
                'price': price,
                'genres': genres
            }
            books.append(new_book)
            book_id_counter += 1  # Increment the book ID counter for the next book

            self._send_response(200, {"result": book_id_counter - 1})
        else:
            self.send_error(404, "Endpoint not found")

    def do_PUT(self):
        if self.path.startswith('/book'):
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            self._handle_update_book_price(query_components)
        else:
            self.send_error(404, "Endpoint not found")

    def do_DELETE(self):
        if self.path.startswith('/book'):
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            self._handle_delete_book(query_components)
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_get_total_books(self, query_components):
        filtered_books = self._apply_filters(query_components)
        self._send_response(200, {"result": len(filtered_books)})

    def _handle_get_books_data(self, query_components):
        filtered_books = self._apply_filters(query_components)
        # Sort books by title
        sorted_books = sorted(filtered_books, key=lambda book: book['title'].lower())
        self._send_response(200, {"result":sorted_books})

    def _handle_get_single_book_data(self, query_components):
        if 'id' in query_components:
            try:
                book_id = int(query_components['id'][0])
                book = next((book for book in books if book['id'] == book_id), None)
                if book:
                    self._send_response(200, {"result":book})
                else:
                    self._send_response(404, {"errorMessage": f"Error: no such Book with id {book_id}"})
            except ValueError:
                self._send_response(400, {"errorMessage": "Error: Invalid book id"})
        else:
            self._send_response(400, {"errorMessage": "Error: Missing book id"})

    def _handle_update_book_price(self, query_components):
        if 'id' in query_components and 'price' in query_components:
            try:
                book_id = int(query_components['id'][0])
                new_price = int(query_components['price'][0])
                book_index = next((index for index, book in enumerate(books) if book['id'] == book_id), None)
                if book_index is not None:
                    if new_price <= 0:
                        self._send_response(409, {
                            "errorMessage": f"Error: price update for book [{book_id}] must be a positive integer"})
                    else:
                        old_price = books[book_index]['price']
                        books[book_index]['price'] = new_price
                        self._send_response(200, {"result": old_price})
                else:
                    self._send_response(404, {"errorMessage": f"Error: no such Book with id {book_id}"})
            except ValueError:
                self._send_response(400, {"errorMessage": "Error: Invalid book id or price"})
        else:
            self._send_response(400, {"errorMessage": "Error: Missing book id or price"})

    def _handle_delete_book(self, query_components):
        if 'id' in query_components:
            try:
                book_id = int(query_components['id'][0])
                book_index = next((index for index, book in enumerate(books) if book['id'] == book_id), None)
                if book_index is not None:
                    del books[book_index]
                    self._send_response(200, {"result": len(books)})
                else:
                    self._send_response(404, {"errorMessage": f"Error: no such Book with id {book_id}"})
            except ValueError:
                self._send_response(400, {"errorMessage": "Error: Invalid book id"})
        else:
            self._send_response(400, {"errorMessage": "Error: Missing book id"})

    def _apply_filters(self, query_components):
        filtered_books = books

        # Apply filters
        if 'author' in query_components:
            author = query_components['author'][0].strip().lower()
            filtered_books = [book for book in filtered_books if book['author'].strip().lower() == author]

        if 'price-bigger-than' in query_components:
            price_bigger_than = int(query_components['price-bigger-than'][0])
            filtered_books = [book for book in filtered_books if book['price'] >= price_bigger_than]

        if 'price-less-than' in query_components:
            price_less_than = int(query_components['price-less-than'][0])
            filtered_books = [book for book in filtered_books if book['price'] <= price_less_than]

        if 'year-bigger-than' in query_components:
            year_bigger_than = int(query_components['year-bigger-than'][0])
            filtered_books = [book for book in filtered_books if book['year'] >= year_bigger_than]

        if 'year-less-than' in query_components:
            year_less_than = int(query_components['year-less-than'][0])
            filtered_books = [book for book in filtered_books if book['year'] <= year_less_than]

        if 'genres' in query_components:
            genres = query_components['genres'][0].split(',')
            if not all(genre in ALLOWED_GENRES for genre in genres):
                self._send_response(400, {"errorMessage": "Error: Invalid genre in the list"})
                return []
            filtered_books = [book for book in filtered_books if any(genre in book['genres'] for genre in genres)]

        return filtered_books

def run_server():
    server_address = ('', 80)
    httpd = HTTPServer(server_address, BookStoreHandler)
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
