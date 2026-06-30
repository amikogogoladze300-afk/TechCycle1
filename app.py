import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///techcycle.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- მონაცემთა ბაზის მოდელები ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    os = db.Column(db.String(50), default="ცნობილი არ არის")
    display = db.Column(db.String(50), default="ცნობილი არ არის")
    camera = db.Column(db.String(50), default="ცნობილი არ არის")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ფორმები (WTForms) ---
class LoginForm(FlaskForm):
    email = StringField('ელ-ფოსტა', validators=[DataRequired(), Email()])
    password = PasswordField('პაროლი', validators=[DataRequired()])
    submit = SubmitField('შესვლა')

class RegisterForm(FlaskForm):
    username = StringField('მომხმარებელი', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('ელ-ფოსტა', validators=[DataRequired(), Email()])
    password = PasswordField('პაროლი', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('გაიმეორეთ პაროლი', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('რეგისტრაცია')

class ProductForm(FlaskForm):
    title = StringField('დასახელება', validators=[DataRequired()])
    price = IntegerField('ფასი', validators=[DataRequired()])
    condition = SelectField('მდგომარეობა', choices=[('ახალივით', 'ახალივით'), ('განახლებული', 'განახლებული'), ('მეორადი', 'მეორადი')], validators=[DataRequired()])
    image_url = StringField('სურათის URL', validators=[DataRequired()])
    os = StringField('ოპერაციული სისტემა')
    display = StringField('ეკრანი')
    camera = StringField('კამერა')
    submit = SubmitField('ჩაბარება')

# --- ბაზის ინიციალიზაცია (ავტომატური შექმნა Render-ისთვის) ---
def init_db():
    with app.app_context():
        db.create_all()
        
        # ადმინის შექმნა
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@techcycle.ge', 
                              password=generate_password_hash('admin123'), is_admin=True)
            db.session.add(admin_user)
            db.session.commit()
            
        # საწყისი პროდუქტების ჩაყრა Zoommer-ის ლინკებით
        if Product.query.count() == 0:
            sample_products = [
                Product(
                    title="Apple iPhone 14 Pro 128GB Space Black", price=1850, condition="ახალივით",
                    image_url="https://zoommer.ge/_next/image?url=https%3A%2F%2Fs3.zoommer.ge%2Fzoommer-images%2F9b7b9f56-6a54-4f81-9985-2c8c4a9a0eb5.jpeg&w=384&q=75",
                    os="iOS 16", display="6.1\" Super Retina XDR", camera="48 MP + 12 MP + 12 MP"
                ),
                Product(
                    title="Samsung Galaxy S23 Ultra 5G 12/256GB Phantom Black", price=1999, condition="განახლებული",
                    image_url="https://zoommer.ge/_next/image?url=https%3A%2F%2Fs3.zoommer.ge%2Fzoommer-images%2F09a90967-ef3d-4235-9057-a16dfb776264.png&w=384&q=75",
                    os="Android 13", display="6.8\" Dynamic AMOLED 2X", camera="200 MP + 10 MP + 10 MP + 12 MP"
                ),
                Product(
                    title="Apple MacBook Air 13\" M2 8/256GB Midnight", price=2450, condition="მეორადი",
                    image_url="https://zoommer.ge/_next/image?url=https%3A%2F%2Fs3.zoommer.ge%2Fzoommer-images%2F904f47ef-1b20-4e4b-97da-4e78dbf14546.jpeg&w=384&q=75",
                    os="macOS Ventura", display="13.6\" Liquid Retina", camera="1080p FaceTime HD"
                ),
                Product(
                    title="Sony PlayStation 5 Slim Digital Edition", price=1249, condition="ახალივით",
                    image_url="https://zoommer.ge/_next/image?url=https%3A%2F%2Fs3.zoommer.ge%2Fzoommer-images%2Fccf6f1c7-c7ba-4b08-8df0-10170a44288b.png&w=384&q=75",
                    os="PS5 OS", display="4K 120Hz Output", camera="არ აქვს"
                )
            ]
            db.session.bulk_save_objects(sample_products)
            db.session.commit()

# აქ ვუშვებთ, რომ სერვერის ჩართვისას ბაზა მომენტალურად მზად იყოს
init_db()

# --- საიტის როუტები (Routes) ---
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/product/<int=product_id>')
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('წარმატებით შეხვედით სისტემაში!', 'success')
            return redirect(url_for('index'))
        flash('არასწორი ელ-ფოსტა ან პაროლი.', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('რეგისტრაცია წარმატებით დასრულდა! შეგიძლიათ შეხვიდეთ.', 'success')
            return redirect(url_for('login'))
        except:
            db.session.rollback()
            flash('ეს მომხმარებელი ან ელ-ფოსტა უკვე დაკავებულია.', 'danger')
    return render_template('register.html', form=form)

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        new_product = Product(
            title=form.title.data, price=form.price.data, condition=form.condition.data,
            image_url=form.image_url.data, os=form.os.data or "ცნობილი არ არის",
            display=form.display.data or "ცნობილი არ არის", camera=form.camera.data or "ცნობილი არ არის"
        )
        db.session.add(new_product)
        db.session.commit()
        flash('პროდუქტი წარმატებით დაემატა კატალოგში!', 'success')
        return redirect(url_for('index'))
    return render_template('add_product.html', form=form)

@app.route('/delete_product/<int:product_id>')
@login_required
def delete_product(product_id):
    if not current_user.is_admin:
        flash('ამ მოქმედების უფლება მხოლოდ ადმინს აქვს.', 'danger')
        return redirect(url_for('index'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('პროდუქტი წარმატებით წაიშალა.', 'success')
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('თქვენ გამოხვედით სისტემიდან.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)