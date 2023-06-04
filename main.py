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


@app.teardown_appcontext
def close_connection(exception):
    # Close the database connection when the app context is torn down
    connection = getattr(db_local, 'cogit nnection', None)
    if connection is not None:
        connection.close()


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

if __name__ == '__main__':
    app.run()
