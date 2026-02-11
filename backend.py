<<<<<<< HEAD
from flask import Flask, jsonify 
from flask_cors import CORS 
import mysql.connector 
from dotenv import load_dotenv
import os

app = Flask(__name__)
CORS(app)

load_dotenv()

def get_database(): 
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=os.getenv("MYSQL_PORT"), 
        user=os.getenv("MYSQL_USER"), 
        password=os.getenv("MYSQL_PASSWORD"), 
        database=os.getenv("MYSQL_DB")
    )

#top 5 rented films 
@app.get("/api/top-5-films")
def top_films():
    database = get_database()
    cur = database.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            f.film_id,
            f.title, 
            c.name AS category, 
            COUNT(r.rental_id) AS rented 
        FROM film f 
        JOIN inventory i ON i.film_id = f.film_id 
        JOIN rental r ON r.inventory_id = i.inventory_id 
        JOIN film_category fc ON fc.film_id = f.film_id
        JOIN category c ON c.category_id = fc.category_id
        GROUP BY f.film_id, f.title, c.name
        ORDER BY rented DESC 
        LIMIT 5;
    """)

    rows = cur.fetchall()
    cur.close()
    database.close()
    return jsonify(rows)

#film details
@app.get("/api/films/<int:film_id>")
def film_Details(film_id):
    database = get_database()
    cur = database.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            f.film_id,
            f.title, 
            f.description, 
            f.release_year,
            f.rating, 
            c.name AS genre, 
            COUNT(DISTINCT r.rental_id) AS rented 
        FROM film f 
        JOIN film_category fc ON fc.film_id = f.film_id
        JOIN category c ON c.category_id = fc.category_id
        LEFT JOIN inventory i on i.film_id = f.film_id 
        LEFT JOIN rental r ON r.inventory_id = i.inventory_id
        WHERE f.film_id = %s 
        GROUP BY f.film_id, f.title, f.description, f.release_year, f.rating, c.name;
    """, (film_id,))

    row = cur.fetchone()
    cur.close()
    database.close()
    return jsonify(row)

#top 5 actors of rentails of their films in store 
@app.get("/api/top-5-actors")
def top_5_actors():
    database = get_database()
    cur = database.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            a.actor_id, 
            CONCAT(a.first_name, ' ', a.last_name) AS name,
            COUNT(DISTINCT fa.film_id) AS movies 
        FROM actor a 
        JOIN film_actor fa ON fa.actor_id = a.actor_id
        JOIN inventory i on i.film_id = fa.film_id 
        GROUP BY a.actor_id, a.first_name, a.last_name 
        ORDER BY movies DESC 
        LIMIT 5; 
    """)

    rows = cur.fetchall()
    cur.close()
    database.close()
    return jsonify(rows)

#actor details + their top 5 rented films
@app.get("/api/actors/<int:actor_id>")
def actor_Details(actor_id):
    database = get_database()
    cur = database.cursor(dictionary=True)

    #actor info 
    cur.execute("""
        SELECT actor_id, first_name, last_name
        FROM actor 
        WHERE actor_id = %s; 
    """, (actor_id,))
    actor = cur.fetchone()

#actor top 5 films 
    cur.execute("""
        SELECT 
            f.film_id,
            f.title,
            COUNT(DISTINCT r.rental_id) AS rented 
        FROM film f 
        JOIN film_actor fa ON fa.film_id = f.film_id 
        JOIN inventory i ON i.film_id = f.film_id
        JOIN rental r on r.inventory_id = i.inventory_id 
        WHERE fa.actor_id = %s 
        GROUP BY f.film_id, f.title 
        ORDER BY rented DESC 
        LIMIT 5
    """, (actor_id,))
    top_films = cur.fetchall()

    cur.close()
    database.close()
    return jsonify({
        "actor": actor, 
        "top_films":top_films
    })

if __name__ == "__main__": 
    app.run(port=5000, debug=True)
=======
from flask import Flask, jsonify 
from flask_cors import CORS 
import mysql.connector 
from dotenv import load_dotenv
import os

app = Flask(__name__)
CORS(app)

load_dotenv()

def get_database(): 
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=os.getenv("MYSQL_PORT"), 
        user=os.getenv("MYSQL_USER"), 
        password=os.getenv("MYSQL_PASSWORD"), 
        database=os.getenv("MYSQL_DB")
    )

#top 5 rented films 
@app.get("/api/top-5-films")
def top_films():
    database = get_database()
    cur = database.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            f.film_id,
            f.title, 
            c.name AS category, 
            COUNT(r.rental_id) AS rented 
        FROM film f 
        JOIN inventory i ON i.film_id = f.film_id 
        JOIN rental r ON r.inventory_id = i.inventory_id 
        JOIN film_category fc ON fc.film_id = f.film_id
        JOIN category c ON c.category_id = fc.category_id
        GROUP BY f.film_id, f.title, c.name
        ORDER BY rented DESC 
        LIMIT 5;
    """)

    rows = cur.fetchall()
    cur.close()
    database.close()
    return jsonify(rows)

#film details
@app.get("/api/films/<int:film_id>")
def film_Details(film_id):
    database = get_database()
    cur = database.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            f.film_id,
            f.title, 
            c.name AS category, 
            COUNT(r.rental_id) AS rented 
        FROM film f 
        JOIN film_category fc ON fc.film_id = f.film_id
        JOIN category c ON c.category_id = fc.category_id
        LEFT JOIN inventory i on i.film_id = f.film_id 
        LEFT JOIN rental r ON r.inventory_id = i.inventory_id
        WHERE f.film_id = %s 
        GROUP BY f.film_id, f.title, c.name;
    """, (film_id,))

    row = cur.fetchone()
    cur.close()
    database.close()
    return jsonify(row)

#top 5 actors of rentails of their films in store 
@app.get("/api/top-5-actors")
def top_5_actors():
    database = get_database()
    cur = database.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            a.actor_id, 
            CONCAT(a.first_name, ' ', a.last_name) AS name,
            COUNT(DISTINCT fa.film_id) AS movies 
        FROM actor a 
        JOIN film_actor fa ON fa.actor_id = a.actor_id
        JOIN inventory i on i.film_id = fa.film_id 
        GROUP BY a.actor_id, a.first_name, a.last_name 
        ORDER BY movies DESC 
        LIMIT 5; 
    """)

    rows = cur.fetchall()
    cur.close()
    database.close()
    return jsonify(rows)

#actor details + their top 5 rented films
@app.get("/api/actors/<int:actor_id>")
def actor_Details(actor_id):
    database = get_database()
    cur = database.cursor(dictionary=True)

    #actor info 
    cur.execute("""
        SELECT actor_id, first_name, last_name
        FROM actor 
        WHERE actor_id = %s; 
    """, (actor_id,))
    actor = cur.fetchone()

#actor top 5 films 
    cur.execute("""
        SELECT 
            f.film_id,
            f.title,
            COUNT(DISTINCT r.rental_id) AS rented 
        FROM film f 
        JOIN film_actor fa ON fa.film_id = f.film_id 
        JOIN inventory i ON i.film_id = f.film_id
        JOIN rental r on r.inventory_id = i.inventory_id 
        WHERE fa.actor_id = %s 
        GROUP BY f.film_id, f.title 
        ORDER BY rented DESC 
        LIMIT 5
    """, (actor_id,))
    top_films = cur.fetchall()

    cur.close()
    database.close()
    return jsonify({
        "actor": actor, 
        "top_films":top_films
    })

if __name__ == "__main__": 
    app.run(port=5000, debug=True)

    
>>>>>>> bbbf5e474ceec896cd43d179bbcc34a05038e2bc
