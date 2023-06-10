from flask import Flask, render_template, redirect, url_for, request, session, jsonify
import sqlite3
import threading
import os

# Generate a secret key
secret_key = os.urandom(24)
# Set the secret key in your Flask app
app = Flask(__name__)
app.secret_key = secret_key

DATABASE = 'articles.db'
# Create a thread-local storage for the database connection
db_local = threading.local()


def get_article_by_id(article_id):
    # Replace this with your logic to fetch the article from your data store
    # Example code assuming you have a list of articles
    cursor = get_cursor()
    cursor.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
    article = cursor.fetchone()
    return article


def get_category_by_id(category_id):
    cursor = get_cursor()
    cursor.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
    category = cursor.fetchone()
    return category


def get_db():
    # Check if the database connection is already stored in the thread-local storage
    if not hasattr(db_local, 'connection') or db_local.connection is None:
        # If not, create a new connection and store it
        db_local.connection = sqlite3.connect(DATABASE)
        db_local.connection.row_factory = sqlite3.Row
    return db_local.connection


def get_cursor():
    return get_db().cursor()


def create_articles_table():
    cursor = get_cursor()
    cursor.execute('DROP TABLE IF EXISTS articles')
    cursor.execute('DROP TABLE IF EXISTS categories')
    cursor.execute('''CREATE TABLE categories
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE articles
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       category_id INTEGER,
                       title TEXT NOT NULL,
                       content TEXT NOT NULL,
                       likes INTEGER DEFAULT 0,
                       FOREIGN KEY (category_id) REFERENCES categories (id))''')
    get_db().commit()


def create_categories_table():
    cursor = get_cursor()
    cursor.execute('DROP TABLE IF EXISTS categories')
    cursor.execute('''CREATE TABLE categories
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL)''')
    get_db().commit()


def get_categories():
    cursor = get_cursor()
    cursor.execute('SELECT id, name FROM categories')
    categories = cursor.fetchall()
    return categories


def delete_category(category_id):
    cursor = get_cursor()
    cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    get_db().commit()


@app.route('/')
def index():
    cursor = get_cursor()
    cursor.execute(
        'SELECT articles.id, articles.title, articles.likes, categories.name AS category_name FROM articles JOIN categories ON articles.category_id = categories.id')
    articles = cursor.fetchall()
    liked_articles = session.get('liked_articles', [])

    cursor.execute('SELECT id, name FROM categories')
    categories = cursor.fetchall()

    return render_template('index.html', articles=articles, liked_articles=liked_articles, categories=categories)


@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category_id = request.form['category']

        # Save the article with the selected category
        cursor = get_cursor()
        cursor.execute('INSERT INTO articles (title, content, category_id) VALUES (?, ?, ?)',
                       (title, content, category_id))
        get_db().commit()

        return redirect('/')

    # Fetch the list of categories
    cursor = get_cursor()
    cursor.execute('SELECT id, name FROM categories')
    categories = cursor.fetchall()

    return render_template('create.html', categories=categories)


@app.route('/like/<int:article_id>', methods=['POST'])
def like(article_id):
    action = request.args.get('action', 'like')
    liked_articles = session.get('liked_articles', [])

    cursor = get_cursor()
    cursor.execute('SELECT likes FROM articles WHERE id = ?', (article_id,))
    result = cursor.fetchone()
    likes = result['likes']
    is_liked = article_id in liked_articles

    if action == 'like':
        if article_id not in liked_articles:
            cursor.execute('UPDATE articles SET likes = likes + 1 WHERE id = ?', (article_id,))
            liked_articles.append(article_id)
            likes += 1
            is_liked = True
    elif action == 'unlike':
        if article_id in liked_articles:
            cursor.execute('UPDATE articles SET likes = likes - 1 WHERE id = ?', (article_id,))
            liked_articles.remove(article_id)
            likes -= 1
            is_liked = False

    session['liked_articles'] = liked_articles
    get_db().commit()

    response = {'likes': likes, 'isLiked': is_liked}
    return jsonify(response)


@app.route('/check_like/<int:article_id>', methods=['GET'])
def check_like(article_id):
    liked_articles = session.get('liked_articles', [])
    is_liked = article_id in liked_articles
    return str(is_liked)


@app.route('/article/<int:article_id>')
def article(article_id):
    article = get_article_by_id(article_id)
    return render_template('article.html', article=article)


@app.route('/edit/<int:article_id>', methods=['GET', 'POST'])
def edit_article(article_id):
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category_id = request.form['category']
        cursor = get_cursor()
        cursor.execute('UPDATE articles SET title = ?, content = ?, category_id = ? WHERE id = ?',
                       (title, content, category_id, article_id))
        get_db().commit()
        return redirect(url_for('index'))
    else:
        article = get_article_by_id(article_id)
        cursor = get_cursor()
        cursor.execute('SELECT id, name FROM categories')
        categories = cursor.fetchall()
        return render_template('edit.html', article=article, categories=categories)


@app.route('/delete/<int:article_id>', methods=['POST'])
def delete_article(article_id):
    cursor = get_cursor()
    cursor.execute('DELETE FROM articles WHERE id = ?', (article_id,))
    get_db().commit()

    return redirect('/')


@app.route('/create_category', methods=['GET', 'POST'])
def create_category():
    if request.method == 'POST':
        name = request.form['name']
        cursor = get_cursor()
        cursor.execute('INSERT INTO categories (name) VALUES (?)', (name,))
        get_db().commit()
        return redirect('/')
    return render_template('create_category.html')


@app.route('/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    if request.method == 'POST':
        name = request.form['name']
        cursor = get_cursor()
        cursor.execute('UPDATE categories SET name = ? WHERE id = ?', (name, category_id))
        get_db().commit()
        return redirect(url_for('index'))
    else:
        category = get_category_by_id(category_id)
        return render_template('edit_category.html', category=category)


@app.route('/delete_category', methods=['POST'])
def delete_category():
    if request.method == 'POST':
        category_id = request.form['category']

        # Delete the category from the database
        delete_category_from_database(category_id)

        return redirect('/')

    categories = get_categories()
    return render_template('delete_category.html', categories=categories)


def delete_category_from_database(category_id):
    # Import the necessary database library and establish a connection
    import sqlite3

    # Connect to the database
    conn = sqlite3.connect('articles.db')
    cursor = conn.cursor()

    # Execute the delete query to remove the category
    cursor.execute("DELETE FROM categories WHERE id=?", (category_id,))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()


@app.route('/delete_category', methods=['GET', 'POST'])
def delete_category_page():
    if request.method == 'POST':
        category_id = request.form['category']
        delete_category(category_id)
        return redirect('/')
    categories = get_categories()
    return render_template('delete_category.html', categories=categories)


@app.route('/delete_category', methods=['POST'])
def delete_category_route():
    if request.method == 'POST':
        category_id = request.form['category']

        # Delete the category from the database
        delete_category(category_id)

        return redirect('/')

    categories = get_categories()
    return render_template('delete_category.html', categories=categories)


@app.route('/delete_category', methods=['POST'])
def delete_category_submit():
    category_id = request.form.get('category')

    # Delete the category from the database
    delete_category(category_id)

    return redirect('/')


@app.teardown_appcontext
def close_connection(exception):
    connection = getattr(db_local, 'connection', None)
    if connection is not None:
        connection.close()
        db_local.connection = None  # Reset the connection attribute


if __name__ == '__main__':
    create_articles_table()
    create_categories_table()
    app.run()
