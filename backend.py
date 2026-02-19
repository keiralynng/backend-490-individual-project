from flask import Flask, jsonify, request 
from flask_cors import CORS 
import mysql.connector 
from dotenv import load_dotenv
import os
import math

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


#get info for films page
@app.get("/api/films")
def filmsList():
    db = get_database()
    cur = db.cursor(dictionary=True)
    search = request.args.get("search")

    #make pages
    page = request.args.get("page", default=1, type=int)
    limit = 9 # 9 films per page
    offset = (page - 1) * limit

    #grabs details of the films
    query = """ 
        SELECT DISTINCT
            f.film_id,
            f.title,
            c.name,
            f.description,
            f.rating,
            f.release_year,
            f.length,
            f.rental_duration,
            f.rental_rate,
            f.replacement_cost
        FROM film f
        JOIN film_category i ON f.film_id = i.film_id
        JOIN category c ON i.category_id = c.category_id
        LEFT JOIN film_ACTOR fa ON f.film_id = fa.film_id
        LEFT JOIN actor a ON fa.actor_id = a.actor_id
        WHERE 1=1
    """

    param = []

    if search:
        query += """
            AND (
                f.title LIKE %s
                OR c.name LIKE %s
                OR CONCAT(a.first_name, ' ', a.last_name) LIKE %s 
            )
        """
        like_term = f"%{search}%"
        param.extend([like_term, like_term, like_term])

    query += f" LIMIT {limit} OFFSET {offset}"

    cur.execute(query, tuple(param))
    films = cur.fetchall()
    cur.close()
    db.close()
    return jsonify(films)


@app.route("/api/rent", methods=["POST"])
def rentFilm():
    data = request.get_json()
    film_id = data.get("film_id")
    customer_id = data.get("customer_id")

    if not film_id or not customer_id:
        return jsonify({"error": "Missing Film Id or Customer Id"}), 400

    db = get_database()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT customer_id
        FROM customer
        WHERE customer_id = %s
""", (customer_id,))
    
    customer = cur.fetchone()

    #executes if customer does not exist
    if not customer:
        cur.close()
        db.close()
        return jsonify({"error": "Customer ID does not exist."}), 404

    #Checking for duplicate rental
    cur.execute("""
        SELECT r.rental_id
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        WHERE r.customer_id = %s
        AND i.film_id = %s
        AND r.return_date IS NULL
""", (customer_id, film_id))
    
    dupe = cur.fetchone()
    if dupe:
        cur.close()
        db.close()
        return jsonify({"error": "Customer has already rented this film"}), 400

    cur.execute("""
        SELECT i.inventory_id
        FROM inventory i
        LEFT JOIN rental r
                ON i.inventory_id = r.inventory_id
                AND r.return_date IS NULL
        WHERE film_id = %s
        AND r.rental_id IS NULL
        LIMIT 1
""", (film_id,))
    
    inventory = cur.fetchone()

    #executes if film not available in inventory
    if not inventory:
        cur.close()
        db.close()
        return jsonify({"error": "No inventory available for this film"}), 400
    
    inventory_id = inventory["inventory_id"]

    #after making sure customer exists AND film is available, registers rental
    cur.execute("""
        INSERT INTO rental (rental_date, inventory_id, customer_id, staff_id)
        VALUES (NOW(), %s, %s, 1)
""", (inventory_id, customer_id))
    
    db.commit()   #uncomment if we want to permanently change the database but i dont think thats necessary for the moment
    cur.close()
    db.close()

    return jsonify({"message": "Film rented!"}), 200

if __name__ == "__main__": 
    app.run(port=5000, debug=True)

