from flask import Flask, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')

# Database configuration
db_config = {
    'user': 'root',
    'password': '',
    'host': '127.0.0.1',
    'database': 'lastnani_db',
}

def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

def initialize_session():
    if 'sent_messages_count' not in session:
        session['sent_messages_count'] = 0
    if 'received_messages_count' not in session:
        session['received_messages_count'] = 0
    if 'sent_messages' not in session:
        session['sent_messages'] = []

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user'] = {'email': user['email'], 'name': user['name']}
            initialize_session()
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'danger')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        if user:
            flash('Email already registered', 'danger')
            conn.close()
            return render_template('register.html')
        hashed_password = generate_password_hash(password)
        cursor.execute('INSERT INTO users (email, password, name) VALUES (%s, %s, %s)',
                       (email, hashed_password, name))
        conn.commit()
        conn.close()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'user' in session:
        initialize_session()
        if request.method == 'POST':
            recipient = request.form['recipient']
            subject = request.form['subject']
            message = request.form['message']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO messages (sender, recipient, subject, message) VALUES (%s, %s, %s, %s)',
                           (session['user']['email'], recipient, subject, message))
            conn.commit()
            conn.close()
            session['sent_messages_count'] += 1
            flash('Message sent!', 'success')
            return redirect(url_for('home'))
        return render_template('homepage.html', user=session['user'],
                               sent_messages_count=session['sent_messages_count'],
                               received_messages_count=session['received_messages_count'],
                               sent_messages=session['sent_messages'])
    else:
        return redirect(url_for('login'))

@app.route('/view', methods=['GET'])
def view_messages():
    if 'user' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM messages WHERE sender = %s', (session['user']['email'],))
        sent_messages = cursor.fetchall()
        conn.close()
        return render_template('view.html', sent_messages=sent_messages)
    else:
        return redirect(url_for('login'))

@app.route('/edit/<int:message_id>', methods=['GET', 'POST'])
def edit_message(message_id):
    if 'user' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM messages WHERE id = %s', (message_id,))
        message = cursor.fetchone()
        if message:
            if request.method == 'POST':
                recipient = request.form['recipient']
                subject = request.form['subject']
                content = request.form['message']
                cursor.execute('UPDATE messages SET recipient = %s, subject = %s, message = %s WHERE id = %s',
                               (recipient, subject, content, message_id))
                conn.commit()
                conn.close()
                flash('Message updated successfully!', 'success')
                return redirect(url_for('view_messages'))
            return render_template('edit_message.html', message=message)
        else:
            conn.close()
            flash('Message not found', 'danger')
            return redirect(url_for('view_messages'))
    return redirect(url_for('login'))

@app.route('/delete/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    if 'user' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        # First, delete the associated comments
        cursor.execute('DELETE FROM comments WHERE message_id = %s', (message_id,))
        # Then, delete the message
        cursor.execute('DELETE FROM messages WHERE id = %s', (message_id,))
        conn.commit()
        conn.close()
        session['sent_messages_count'] -= 1
        flash('Message deleted successfully!', 'success')
        return redirect(url_for('view_messages'))
    else:
        return redirect(url_for('login'))

@app.route('/like/<int:message_id>', methods=['POST'])
def like_message(message_id):
    if 'user' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE messages SET likes = likes + 1 WHERE id = %s', (message_id,))
        conn.commit()
        conn.close()
        flash('Liked message!', 'success')
        return redirect(url_for('view_messages'))
    else:
        flash('You must be logged in to like a message', 'danger')
        return redirect(url_for('login'))

@app.route('/comment/<int:message_id>', methods=['POST'])
def add_comment(message_id):
    if 'user' in session:
        comment = request.form['comment']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO comments (message_id, comment) VALUES (%s, %s)', (message_id, comment))
        conn.commit()
        conn.close()
        flash('Comment added successfully!', 'success')
        return redirect(url_for('view_messages'))
    else:
        flash('You must be logged in to comment on a message', 'danger')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
