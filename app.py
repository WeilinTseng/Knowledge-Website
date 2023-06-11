from flask import Flask, render_template, redirect, url_for, request, session, jsonify
import sqlite3
import threading
import os
import shutil
import datetime
import subprocess
import atexit
from git import Repo
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# SQLite database file path
db_path = 'articles.db'

# Backup directory
backup_dir = 'backup/'

# Git repository configuration
repo_url = 'https://github.com/WeilinTseng/Knowledge-Website.git'
repo_dir = '/opt/render/project/src/new'  # Replace with the desired directory path on Render

# GitHub authentication credentials
github_token = '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'


def restore_database_from_backup():
    # Retrieve the most recent backup file
    backup_files = os.listdir(backup_dir)
    backup_files.sort(reverse=True)  # Sort files in descending order

    if len(backup_files) > 0:
        latest_backup_file = os.path.join(backup_dir, backup_files[0])
        shutil.copyfile(latest_backup_file, db_path)
        logger.info(f'Database restored from backup: {latest_backup_file}')
    else:
        logger.warning('No backup files found.')


# Call the restore_database_from_backup() function at startup
restore_database_from_backup()


def backup_database():
    try:
        if os.path.exists(repo_dir):
            # Repository already exists, perform git pull to update
            repo = Repo(repo_dir)
            origin = repo.remote(name='origin')
            origin.pull()
            logger.info('Repository updated')
        else:
            # Repository doesn't exist, clone it
            repo = Repo.clone_from(repo_url, repo_dir)
            logger.info(f'Repository cloned: {repo_dir}')

        # Create a timestamp for the backup file
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        # Create the backup file name
        backup_file = f'backup_{timestamp}.db'

        # Create the full backup file path
        backup_path = os.path.join(backup_dir, backup_file)

        # Copy the database file to the backup location
        print(f"Database file path: {db_path}")
        shutil.copyfile(db_path, backup_path)

        logger.info(f'Backup file path: {backup_path}')

        # Add the backup file to the index
        repo.index.add([backup_path])
        logger.info('Backup file added to index')

        # Commit the backup file
        repo.index.commit('Add backup file')
        logger.info('Backup file committed')

        # Push the changes to the remote repository
        origin = repo.remote(name='origin')
        origin.push(refspec='master', force=True)
        logger.info('Changes pushed to remote repository')

        logger.info(f'Backup created: {backup_path}')
    except FileNotFoundError:
        logger.error('File not found error occurred while creating backup.')
    except Exception as e:
        logger.error(f'Error occurred: {str(e)}')


# Generate a secret key
secret_key = os.urandom(24)

# Set the secret key in your Flask app
app = Flask(__name__)
app.secret_key = secret_key

DATABASE = 'articles.db'


# Create a thread-local storage for the database connection
db_local = threading.local()


@app.before_request
def backup_on_request():
    backup_thread = threading.Thread(target=backup_database)
    backup_thread.start()


@app.teardown_request
def backup_on_teardown(exception=None):
    backup_thread = threading.Thread(target=backup_database)
    backup_thread.start()


@atexit.register
def backup_on_exit():
    backup_database()


@app.route('/backup', methods=['POST'])
def trigger_backup():
    backup_thread = threading.Thread(target=backup_database)
    backup_thread.start()
    return jsonify({'message': 'Backup triggered.'}), 200


def get_db():
    # Check if the database connection is already stored in the thread-local storage
    if not hasattr(db_local, 'connection') or db_local.connection is None:
        # If not, create a new connection and store it
        db_local.connection = sqlite3.connect(DATABASE)
        db_local.connection.row_factory = sqlite3.Row
    return db_local.connection


def close_db(exception):
    connection = getattr(db_local, 'connection', None)
    if connection is not None:
        connection.close()
        db_local.connection = None  # Reset the connection attribute

    # Perform any other necessary cleanup or backup operations here


def backup_on_exit():
    backup_database()


@app.teardown_appcontext
def teardown_appcontext(exception):
    close_db(exception)


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


def get_cursor():
    return get_db().cursor()


def get_categories():
    cursor = get_cursor()
    cursor.execute('SELECT id, name FROM categories')
    categories = cursor.fetchall()
    return categories


def delete_category(category_id):
    cursor = get_cursor()
    cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    get_db().commit()


def has_associated_posts(category_id):
    cursor = get_cursor()
    cursor.execute('SELECT COUNT(*) FROM articles WHERE category_id = ?', (category_id,))
    count = cursor.fetchone()[0]
    return count > 0


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


@app.route('/delete_category', methods=['GET', 'POST'])
def delete_category():
    if request.method == 'POST':
        category_id = request.form['category']

        # Check if the category has associated posts
        if has_associated_posts(category_id):
            error_message = "Cannot delete the category as it has associated posts."
            categories = get_categories()
            return render_template('delete_category.html', categories=categories, error_message=error_message)

        # Delete the category from the database
        delete_category_from_database(category_id)

        return redirect('/')

    categories = get_categories()
    return render_template('delete_category.html', categories=categories)


@app.route('/delete_category', methods=['POST'])
def delete_category_route():
    if request.method == 'POST':
        category_id = request.form['category']

        # Check if the category has associated posts
        if has_associated_posts(category_id):
            error_message = "Cannot delete the category as it has associated posts."
            categories = get_categories()
            return render_template('delete_category.html', categories=categories, error_message=error_message)

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
        delete_category_from_database(category_id)
        return redirect('/')
    categories = get_categories()
    return render_template('delete_category.html', categories=categories)


if __name__ == '__main__':
    # Register the backup function to run on exit
    atexit.register(backup_on_exit)

    # Start the Flask development server
    app.run(debug=True)
