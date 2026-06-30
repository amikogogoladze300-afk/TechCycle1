from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, PasswordField, SubmitField
from wtforms.validators import DataRequired, URL, Email, EqualTo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///techcycle.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- 1. მონაცემთა ბაზის მოდელები (SQLAlchemy) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False) 

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    os = db.Column(db.String(100), default="არ აქვს")
    display = db.Column(db.String(100), default="არ აქვს")
    camera = db.Column(db.String(100), default="არ აქვს")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # <--- შესწორებულია აქ!

# --- 2. ვალიდაციის ფორმები (WTForms) ---
class RegisterForm(FlaskForm):
    username = StringField('მომხმარებლის სახელი', validators=[DataRequired()])
    email = StringField('ელ-ფოსტა', validators=[DataRequired(), Email()])
    password = PasswordField('პაროლი', validators=[DataRequired()])
    confirm_password = PasswordField('გაიმეორეთ პაროლი', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('რეგისტრაცია')

class LoginForm(FlaskForm):
    email = StringField('ელ-ფოსტა', validators=[DataRequired(), Email()])
    password = PasswordField('პაროლი', validators=[DataRequired()])
    submit = SubmitField('შესვლა')

class ProductForm(FlaskForm):
    title = StringField('პროდუქტის დასახელება', validators=[DataRequired()])
    price = IntegerField('ფასი (₾)', validators=[DataRequired()])
    condition = SelectField('მდგომარეობა', choices=[('ახალივით', 'ახალივით'), ('მეორადი', 'მეორადი'), ('განახლებული', 'განახლებული'), ('ნაწილებად', 'ნაწილებად')], validators=[DataRequired()])
    image_url = StringField('სურათის ლინკი (URL)', validators=[DataRequired(), URL()])
    os = StringField('სისტემა (OS)')
    display = StringField('ეკრანი')
    camera = StringField('კამერა / სხვა მახასიათებელი')
    submit = SubmitField('კატალოგში დამატება')

# --- 3. როუტები (Routes) ---
@app.route('/')
def index():
    products = Product.query.all() 
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = db.get_or_404(Product, product_id)  # <--- შესწორებულია აქ!
    return render_template('product.html', product=product)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('რეგისტრაცია წარმატებით გაიარეთ!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        flash('არასწორი ელ-ფოსტა ან პაროლი!', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        new_prod = Product(
            title=form.title.data, price=form.price.data, condition=form.condition.data,
            image_url=form.image_url.data, os=form.os.data or "არ აქვს",
            display=form.display.data or "არ აქვს", camera=form.camera.data or "არ აქვს"
        )
        db.session.add(new_prod)
        db.session.commit()
        flash('პროდუქტი წარმატებით დაემატა!', 'success')
        return redirect(url_for('index'))
    return render_template('add_product.html', form=form)

@app.route('/delete-product/<int:product_id>')
@login_required
def delete_product(product_id):
    if not current_user.is_admin:
        flash('ამ მოქმედების უფლება მხოლოდ ადმინისტრატორს აქვს!', 'danger')
        return redirect(url_for('index'))
    product = db.get_or_404(Product, product_id)  # <--- შესწორებულია აქაც უსაფრთხოებისთვის!
    db.session.delete(product)
    db.session.commit()
    flash('პროდუქტი წაიშალა ადმინის მიერ!', 'success')
    return redirect(url_for('index'))

def init_db():
    with app.app_context():
        db.create_all()
        
        # 1. ავტომატურად ვქმნით ადმინს (თუ არ არსებობს)
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@techcycle.ge', 
                              password=generate_password_hash('admin123'), is_admin=True)
            db.session.add(admin_user)
            db.session.commit()
            
        # 2. ავტომატურად ვამატებთ საწყის პროდუქტებს (თუ ბაზა ცარიელია)
        if Product.query.count() == 0:
            sample_products = [
                Product(
                    title="Apple iPhone 14 Pro 128GB Space Black",  
                    price=1850,
                    condition="ახალივით",
                    image_url="https://i.ebayimg.com/images/g/vNkAAeSwPpto9MCz/s-l1600.webp",
                    display="6.1\" Super Retina XDR",
                    camera="48 MP + 12 MP + 12 MP"
                ),
                Product(
                    title="Samsung Galaxy S23 Ultra 5G 12/256GB Phantom Black",
                    price=1999,
                    condition="განახლებული",
                    image_url="https://encrypted-tbn1.gstatic.com/shopping?q=tbn:ANd9GcS7x9Ifh_c_0Schq5lojB934BKcA5IeG8K2WvBawhNfVeUCx9WOALzZ9knmYx3-gye-c_uMMqHSdtHwsr3TEYfIT6biaDCgvG6kguSxTMYZoZ_i3o6-&usqp=CAc"
                    ,
                    display="6.8\" Dynamic AMOLED 2X",
                    camera="200 MP + 10 MP + 10 MP + 12 MP"
                ),
                Product(
                    title="Apple MacBook Air 13\" M2 8/256GB Midnight",
                    price=2450,
                    condition="მეორადი",
                    image_url="",
                    os="macOS Ventura",
                    display="13.6\" Liquid Retina",
                    camera="1080p FaceTime HD Camera"
                ),
                Product(
                    title="Sony PlayStation 5 Slim Digital Edition",
                    price=1249,
                    condition="ახალივით",
                    image_url="",
                    os="PS5 OS",
                    display="4K 120Hz Output",
                    camera="არ აქვს"
                )
            ]
            
            db.session.bulk_save_objects(sample_products)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
