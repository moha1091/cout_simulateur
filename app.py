from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from io import TextIOWrapper
import csv
from datetime import datetime
from config import Config
import pandas as pd
import json
import logging


app = Flask(__name__, static_url_path='/static')
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    family = db.Column(db.String(50))
    unit = db.Column(db.String(20))
    price = db.Column(db.Float)

class FinalProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    client = db.Column(db.String(100), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    pallet_weight = db.Column(db.Float, nullable=False)
    packaging_cost_per_kg = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    articles = db.relationship('FinalProductArticle', backref='final_product', lazy=True)

class FinalProductArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    final_product_id = db.Column(db.Integer, db.ForeignKey('final_product.id'), nullable=False)
    article_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/cost_simulator', methods=['GET', 'POST'])
def cost_simulator():
    result = None
    if request.method == 'POST':
        try:
            emb_kg = float(request.form['emb_kg'])
            MO_kg = float(request.form['MO_kg'])
            Transport_kg = float(request.form['Transport_kg'])
            Douane_kg = float(request.form['Douane_kg'])
            autre_kg = float(request.form['autre_kg'])
            production_kg = float(request.form['production_kg'])
            prix_vente = float(request.form['prix_vente'])

            Cou_kg_total = emb_kg + MO_kg + Transport_kg + Douane_kg + autre_kg + production_kg
            Cou_kg_sansprod = emb_kg + MO_kg + Transport_kg + Douane_kg + autre_kg
            marge_prod = prix_vente - Cou_kg_sansprod

            result = {
                'Cou_kg_total': Cou_kg_total,
                'Cou_kg_sansprod': Cou_kg_sansprod,
                'marge_prod': marge_prod,
                'message': "La marge est positive, bonne affaire" if marge_prod > production_kg else "Le prix proposé par le client ne couvre pas le coût de production. Il faut renégocier le prix.",
                'input_data': {
                    'emb_kg': emb_kg,
                    'MO_kg': MO_kg,
                    'Transport_kg': Transport_kg,
                    'Douane_kg': Douane_kg,
                    'autre_kg': autre_kg,
                    'production_kg': production_kg,
                    'prix_vente': prix_vente
                }
            }

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(result)

        except ValueError as e:
            result = {'error': f"Veuillez entrer des valeurs numériques valides. Erreur: {str(e)}"}
        except Exception as e:
            result = {'error': f"Une erreur s'est produite: {str(e)}"}

    # Always return the rendered template, whether it's a GET or POST request
    return render_template('cost_simulator.html', result=result)

@app.route('/converter', methods=['GET', 'POST'])
def currency_converter():
    conversion_result = None
    if request.method == 'POST':
        amount = float(request.form['amount'])
        rate = float(request.form['rate'])
        conversion_result = amount * rate
    return render_template('currency_converter.html', conversion_result=conversion_result)

@app.route('/articles', methods=['GET', 'POST'])
def manage_articles():
    if request.method == 'POST':
        action = request.form.get('action')
        article_id = request.form.get('id')
        try:
            if action == 'add':
                # Adding a new article
                new_article = Article(
                    code=request.form['code'],
                    name=request.form['name'],
                    family=request.form['family'],
                    unit=request.form['unit'],
                    price=float(request.form['price'])
                )
                db.session.add(new_article)
                db.session.commit()
                flash('Article ajouté avec succès.', 'success')

            elif action == 'edit':
                # Editing an existing article
                article = Article.query.get(article_id)
                if article:
                    article.code = request.form['code']
                    article.name = request.form['name']
                    article.family = request.form['family']
                    article.unit = request.form['unit']
                    article.price = float(request.form['price'])
                    db.session.commit()
                    flash('Article modifié avec succès.', 'success')
                else:
                    flash("L'article n'existe pas.", 'danger')

            elif action == 'delete':
                # Deleting an article
                article = Article.query.get(article_id)
                if article:
                    db.session.delete(article)
                    db.session.commit()
                    flash('Article supprimé avec succès.', 'success')
                else:
                    flash("L'article n'existe pas.", 'danger')

        except Exception as e:
            db.session.rollback()
            flash(f"Une erreur est survenue : {str(e)}", 'danger')

        return redirect(url_for('manage_articles'))

    # Fetch all articles to display
    articles = Article.query.all()
    return render_template('articles.html', articles=articles)
@app.route('/import_articles', methods=['GET', 'POST'])
def import_articles():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and file.filename.endswith('.csv'):
            csvfile = TextIOWrapper(file, encoding='utf-8')
            csv_reader = csv.DictReader(csvfile)
            for row in csv_reader:
                new_article = Article(
                    code=row['code'],
                    name=row['name'],
                    family=row['family'],
                    unit=row['unit'],
                    price=float(row['price'])
                )
                db.session.add(new_article)
            db.session.commit()
            flash('Articles imported successfully')
            return redirect(url_for('manage_articles'))
    return render_template('import_articles.html')

@app.route('/packaging_simulator', methods=['GET', 'POST'])
def packaging_simulator():
    articles = Article.query.all()
    articles_data = [{'id': a.id, 'name': a.name, 'unit': a.unit, 'price': a.price} for a in articles]
    result = None

    if request.method == 'POST':
        total_amount = 0
        selected_articles = []
        for key, value in request.form.items():
            if key.startswith('quantity_') and value:
                article_id = int(key.split('_')[1])
                article = Article.query.get(article_id)
                quantity = float(value)
                amount = quantity * article.price
                total_amount += amount
                selected_articles.append({
                    'name': article.name,
                    'unit': article.unit,
                    'quantity': quantity,
                    'price': article.price,
                    'amount': amount
                })

        pallet_weight = float(request.form['pallet_weight'])
        packaging_cost_per_kg = total_amount / pallet_weight if pallet_weight > 0 else 0

        result = {
            'selected_articles': selected_articles,
            'total_amount': total_amount,
            'pallet_weight': pallet_weight,
            'packaging_cost_per_kg': packaging_cost_per_kg
        }

    return render_template('packaging_simulator.html', articles=articles_data, result=result)

@app.route('/get_article/<int:article_id>')
def get_article(article_id):
    article = Article.query.get_or_404(article_id)
    return jsonify({
        'id': article.id,
        'name': article.name,
        'unit': article.unit,
        'price': article.price
    })

@app.route('/save_final_product', methods=['POST'])
def save_final_product():
    code = request.form['code']
    name = request.form['name']
    client = request.form['client']
    total_amount = float(request.form['total_amount'])
    pallet_weight = float(request.form['pallet_weight'])
    packaging_cost_per_kg = float(request.form['packaging_cost_per_kg'])

    final_product = FinalProduct(code=code, name=name, client=client,
                                 total_amount=total_amount, pallet_weight=pallet_weight,
                                 packaging_cost_per_kg=packaging_cost_per_kg)
    db.session.add(final_product)
    db.session.flush()

    articles = request.form.getlist('articles')
    for article_data in articles:
        name, quantity, unit, price = article_data.split(',')
        final_product_article = FinalProductArticle(
            final_product_id=final_product.id,
            article_name=name,
            quantity=float(quantity),
            unit=unit,
            price=float(price)
        )
        db.session.add(final_product_article)

    db.session.commit()
    flash('Produit fini enregistré avec succès')
    return redirect(url_for('final_products'))

@app.route('/final_products', methods=['GET'])
def final_products():
    search = request.args.get('search', '')
    products = FinalProduct.query.filter(
        (FinalProduct.code.contains(search)) |
        (FinalProduct.name.contains(search)) |
        (FinalProduct.client.contains(search))
    ).all()
    return render_template('final_products.html', products=products, search=search)


import pandas as pd
import json
from flask import flash, redirect, url_for, request, render_template
import logging


@app.route('/import_final_products', methods=['GET', 'POST'])
def import_final_products():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        if file and file.filename.endswith('.xlsx'):
            try:
                df = pd.read_excel(file, engine='openpyxl')

                # Print out the columns that were actually read
                print(f"Columns in the Excel file: {df.columns.tolist()}")
                logging.info(f"Columns in the Excel file: {df.columns.tolist()}")

                required_columns = ['code', 'name', 'client', 'total_amount', 'pallet_weight', 'packaging_cost_per_kg',
                                    'articles']

                # Check if all required columns are present
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    flash(f"Missing columns in Excel file: {', '.join(missing_columns)}", 'error')
                    return redirect(request.url)

                # If we get here, all required columns are present
                flash('File uploaded successfully. Processing data...', 'info')

                for _, row in df.iterrows():
                    try:
                        articles = json.loads(row['articles'])

                        final_product = FinalProduct(
                            code=row['code'],
                            name=row['name'],
                            client=row['client'],
                            total_amount=float(row['total_amount']),
                            pallet_weight=float(row['pallet_weight']),
                            packaging_cost_per_kg=float(row['packaging_cost_per_kg'])
                        )
                        db.session.add(final_product)
                        db.session.flush()

                        for article in articles:
                            final_product_article = FinalProductArticle(
                                final_product_id=final_product.id,
                                article_name=article['name'],
                                quantity=float(article['quantity']),
                                unit=article['unit'],
                                price=float(article['price'])
                            )
                            db.session.add(final_product_article)

                    except json.JSONDecodeError:
                        flash(f"Invalid JSON in 'articles' column for row with code {row['code']}", 'error')
                    except KeyError as e:
                        flash(f"Missing key in row data: {str(e)}", 'error')
                    except ValueError as e:
                        flash(f"Invalid value in row data: {str(e)}", 'error')

                db.session.commit()
                flash('Final products imported successfully', 'success')
                return redirect(url_for('final_products'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error importing final products: {str(e)}', 'error')
                logging.error(f'Error importing final products: {str(e)}', exc_info=True)
                return redirect(request.url)
        else:
            flash('Invalid file type. Please upload an Excel file (.xlsx)', 'error')
            return redirect(request.url)
    return render_template('import_final_products.html')

@app.route('/edit_final_product/<int:product_id>', methods=['GET', 'POST'])
def edit_final_product(product_id):
    product = FinalProduct.query.get_or_404(product_id)
    all_articles = Article.query.all()

    if request.method == 'POST':
        try:
            product.name = request.form['name']
            product.client = request.form['client']
            product.total_amount = float(request.form['total_amount'])
            product.pallet_weight = float(request.form['pallet_weight'])
            product.packaging_cost_per_kg = float(request.form['packaging_cost_per_kg'])

            # Update existing articles
            for article in product.articles:
                article_id = str(article.id)
                if f'quantity_{article_id}' in request.form:
                    article.quantity = float(request.form[f'quantity_{article_id}'])
                    article.price = float(request.form[f'price_{article_id}'])
                else:
                    db.session.delete(article)

            # Add new articles
            new_article_ids = request.form.getlist('new_article_name[]')
            new_article_quantities = request.form.getlist('new_article_quantity[]')

            for article_id, quantity in zip(new_article_ids, new_article_quantities):
                if article_id and quantity:
                    article = Article.query.get(int(article_id))
                    new_article = FinalProductArticle(
                        final_product_id=product.id,
                        article_name=article.name,
                        quantity=float(quantity),
                        unit=article.unit,
                        price=article.price
                    )
                    db.session.add(new_article)

            db.session.commit()
            flash('Final product updated successfully')
            return redirect(url_for('final_products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating final product: {str(e)}')

    return render_template('edit_final_product.html', product=product,
                           all_articles=[{'id': a.id, 'name': a.name, 'unit': a.unit, 'price': a.price} for a in
                                         all_articles])

@app.route('/delete_final_product/<int:product_id>', methods=['POST'])
def delete_final_product(product_id):
    product = FinalProduct.query.get_or_404(product_id)

    try:
        # Delete associated articles first
        FinalProductArticle.query.filter_by(final_product_id=product_id).delete()

        # Then delete the product
        db.session.delete(product)
        db.session.commit()
        return jsonify({"success": True, "message": "Produit supprimé avec succès"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)