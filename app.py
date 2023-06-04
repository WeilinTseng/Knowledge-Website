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
    for article in articles:
        if article['id'] == article_id:
            return article
    return None  # Return None if the article is not found


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
    cursor.execute('''CREATE TABLE articles
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       title TEXT NOT NULL,
                       content TEXT NOT NULL,
                       likes INTEGER DEFAULT 0)''')
    get_db().commit()


@app.route('/')
def index():
    cursor = get_cursor()
    cursor.execute('SELECT id, title, likes FROM articles')
    articles = cursor.fetchall()
    liked_articles = session.get('liked_articles', [])
    return render_template('index.html', articles=articles, liked_articles=liked_articles)


@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cursor = get_cursor()
        cursor.execute('INSERT INTO articles (title, content) VALUES (?, ?)', (title, content))
        get_db().commit()
        return redirect('/')
    return render_template('create.html')


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
    cursor = get_cursor()
    cursor.execute('SELECT title, content FROM articles WHERE id = ?', (article_id,))
    result = cursor.fetchone()
    article = {'title': result['title'], 'content': result['content']}
    return render_template('article.html', article=article)


@app.route('/edit/<int:article_id>', methods=['GET', 'POST'])
def edit_article(article_id):
    if request.method == 'POST':
        # Handle the form submission to update the article
        title = request.form['title']
        content = request.form['content']
        cursor = get_cursor()
        cursor.execute('UPDATE articles SET title = ?, content = ? WHERE id = ?', (title, content, article_id))
        get_db().commit()
        return redirect(url_for('index'))
    else:
        # Retrieve the article from your data store using the provided article_id
        article = get_article_by_id(article_id)  # Replace with your logic to fetch the article
        return render_template('edit.html', article=article)


@app.teardown_appcontext
def close_connection(exception):
    connection = getattr(db_local, 'connection', None)
    if connection is not None:
        connection.close()
        db_local.connection = None  # Reset the connection attribute


if __name__ == '__main__':
    create_articles_table()
    app.run()
