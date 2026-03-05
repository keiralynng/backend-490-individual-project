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
        LEFT JOIN film_actor fa ON f.film_id = fa.film_id
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

    db.commit()
    cur.close()
    db.close()
    return jsonify({"message": "Film rented!"}), 200

    
#list of all customers
#includes search and pagination
@app.get("/api/customers")
def getCustomers(): 
    db = get_database()
    cur = db.cursor(dictionary=True)
    search = request.args.get("search")

    #making pages again
    page = request.args.get("page", default=1, type=int)
    limit = 18 #18 customers per page
    offset = (page - 1) * limit

    from_query = """
        FROM customer
     """

    where_query = ""

    param = []

    if search:
        where_query += """
            WHERE first_name LIKE %s
            OR last_name LIKE %s
        """
        like_term = f"%{search}%"
        param.extend([like_term, like_term])

        if search.isdigit():
            where_query += "OR customer_id = %s"
            param.append(int(search))

    # first query for total count
    total_query = "SELECT COUNT(*) as total " + from_query + where_query
    cur.execute(total_query, tuple(param))
    total = cur.fetchone()["total"]

    # second query for data
    data_query = """
        SELECT
            customer_id,
            first_name,
            last_name,
            email,
            active,
            create_date
    """ + from_query + where_query + """
            ORDER BY last_name, first_name
            LIMIT %s OFFSET %s
    """

    cur.execute(data_query, tuple(param + [limit, offset]))
    customers = cur.fetchall()

    cur.close()
    db.close()
    return jsonify({
        "customers": customers,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    })

#get customer details and rental history 
@app.get("/api/customers/<int:customer_id>")
def get_customer_details(customer_id): 
    db = get_database()
    cur = db.cursor(dictionary=True)

    #customer info 
    cur.execute("""
        SELECT customer_id, first_name, last_name, email, active, create_date
        FROM customer
        WHERE customer_id = %s
        """, (customer_id,)) 
    customer = cur.fetchone()

    if not customer: 
        cur.close()
        db.close()
        return jsonify({"error": "Customer was not found"}), 404

    #rental history
    cur.execute("""
        SELECT
            r.rental_id, 
            r.rental_date, 
            r.return_date, 
            f.film_id,
            f.title
        FROM rental r 
        JOIN inventory i ON i.inventory_id = r.inventory_id 
        JOIN film f ON f.film_id = i.film_id 
        WHERE r.customer_id = %s 
        ORDER by r.rental_date DESC 
                """, (customer_id,))
    rentals = cur.fetchall()

    cur.close()
    db.close()
    return jsonify({"customer": customer, "rentals": rentals})

#rental must be marked as returned 
@app.patch("/api/rentals/<int:rental_id>/return")
def return_rental(rental_id):
    db = get_database()
    cur = db.cursor(dictionary=True)
    
    cur.execute("""
        SELECT rental_id
        FROM rental
        WHERE rental_id = %s AND return_date is NULL
        """, (rental_id,))
    rental = cur.fetchone()

    if not rental: 
        cur.close()
        db.close()
        return jsonify({"error:" "Rental is not found or is already returned."}), 404
    
    cur.execute("""
        UPDATE rental
        SET return_date = NOW()
        WHERE rental_id = %s
        """, (rental_id,))
    db.commit()

    cur.close()
    db.close()
    return jsonify({"message:" "Rental marked as returned"}), 200

#delete customer and data from data 
@app.delete("/api/customers/<int:customer_id>")
def delete_customer(customer_id):
    db = get_database()
    cur = db.cursor(dictionary=True)

    #if customer doesnt exist
    cur.execute("SELECT customer_id FROM customer WHERE customer_id = %s", (customer_id,))
    if not cur.fetchone(): 
        cur.close()
        db.close()
        return jsonify({"Error": "Customer not found."}), 404


    cur.execute("DELETE FROM payment WHERE customer_id = %s", (customer_id,))
    cur.execute("DELETE FROM rental WHERE customer_id = %s", (customer_id,))
    cur.execute("DELETE FROM customer WHERE customer_id = %s", (customer_id,))
    db.commit()

    cur.close()
    db.close()
    return jsonify({"message:" "Customer deleted."}), 200

@app.post("/api/customers")
def add_customer():
    db = get_database()
    cur = db.cursor(dictionary=True)
    data = request.json

    #just validating if everything is filled out
    if not data.get("first_name") or not data.get("last_name") or not data.get("email"):
        return jsonify({"error": "Missing required files"}), 400
    
    query = """
        INSERT INTO customer
        (first_name, last_name, email, active, create_date, store_id, address_id)
        VALUES (%s, %s, %s, %s, NOW(), 1, 1)
    """
    
    cur.execute(query, (
        data["first_name"],
        data["last_name"],
        data["email"],
        data.get("active", 1)
    ))

    db.commit()

    new_id = cur.lastrowid

    cur.close()
    db.close()

    return jsonify({
        "message": "Customer created successfully",
        "customer_id": new_id
    }), 201


@app.put("/api/customers/<int:customer_id>")
def update_customer(customer_id):
    db = get_database()
    cur = db.cursor()
    data = request.get_json()

    first_name = data.get("first_name") or None
    last_name = data.get("last_name") or None
    email = data.get("email") or None

    post_query = """
        UPDATE customer
        SET first_name = COALESCE(%s, first_name),
            last_name = COALESCE(%s, last_name),
            email = COALESCE(%s, email)
        WHERE customer_id = %s
    """

    cur.execute(post_query, (first_name, last_name, email, customer_id))
    db.commit()

    cur.close()
    db.close()
    return jsonify({"message": "Customer Updated"})

if __name__ == "__main__": 
    app.run(port=5000, debug=True)

