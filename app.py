from flask import Flask, render_template, request, redirect
import sqlite3
import threading

app = Flask(__name__)

DATABASE = 'articles.db'
# Create a thread-local storage for the database connection
db_local = threading.local()


def get_db():
    # Check if the database connection is already stored in the thread-local storage
    if not hasattr(db_local, 'connection'):
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
    cursor.execute('SELECT * FROM articles')
    articles = cursor.fetchall()
    return render_template('index.html', articles=articles)


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
    cursor = get_cursor()
    cursor.execute('UPDATE articles SET likes = likes + 1 WHERE id = ?', (article_id,))
    get_db().commit()
    return redirect('/')


@app.teardown_appcontext
def close_connection(exception):
    connection = getattr(db_local, 'connection', None)
    if connection is not None:
        connection.close()


if __name__ == '__main__':
    create_articles_table()
    app.run()
