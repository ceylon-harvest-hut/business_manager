from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from sqlalchemy import func
from datetime import datetime
from datetime import date
from sqlalchemy import Table, Column, Integer, String, Float, Date, MetaData
from sqlalchemy import event
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///entities.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- Entity Model ---
class Entity(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Unique ID
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=True)  # New attribut

    def __repr__(self):
        return f"<Entity {self.name}>"

class RelationshipType(db.Model):
    __tablename__ = "relationship_type"
    id = db.Column(db.Integer, primary_key=True)  # Unique ID
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(250), nullable=True)

    def __repr__(self):
        return f"<RelationshipType {self.name}>"

class Relationship(db.Model):
    __tablename__ = "relationship"
    id = db.Column(db.Integer, primary_key=True)  # Unique ID
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'), nullable=False)
    relationship_type_id = db.Column(db.Integer, db.ForeignKey('relationship_type.id'), nullable=False)

    entity = db.relationship('Entity', backref='relationships')
    relationship_type = db.relationship('RelationshipType')

    def __repr__(self):
        return f"<Relationship {self.entity.name} - {self.relationship_type.name}>"

# --- TransactionType Model ---
class TransactionType(db.Model):
    __tablename__ = "transaction_type"
    id = db.Column(db.Integer, primary_key=True)  # Unique ID
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(250), nullable=True)

    def __repr__(self):
        return f"<TransactionType {self.name}>"

class Transaction(db.Model):
    __tablename__ = "transaction"
    id = db.Column(db.Integer, primary_key=True)  # Unique ID
    transaction_type_id = db.Column(db.Integer, db.ForeignKey('transaction_type.id'), nullable=False)
    relationship_id = db.Column(db.Integer, db.ForeignKey('relationship.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(250), nullable=True)

    # Relationships
    transaction_type = db.relationship('TransactionType')
    relationship = db.relationship('Relationship')
    payrolls = db.relationship("Payroll", backref="parent_transaction", lazy=True)

    def __repr__(self):
        return f"<Transaction {self.id} - {self.transaction_type.name} - {self.amount}>"

class WorkType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(250))
    pay_type = db.Column(db.String(20), nullable=False)  # Hourly, Daily, Weekly, Monthly
    rate = db.Column(db.Float, nullable=False, default=0.0)

class WorkLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    work_type_id = db.Column(db.Integer, db.ForeignKey('work_type.id'), nullable=False)
    relationship_id = db.Column(db.Integer, db.ForeignKey('relationship.id'), nullable=False)  
    work_units = db.Column(db.Float, nullable=False)
    due_payment = db.Column(db.Float, nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=True)
    is_paid = db.Column(db.Boolean, default=False)
    description = db.Column(db.String(250)) 

    work_type = db.relationship("WorkType", backref="work_logs")
    relationship = db.relationship("Relationship", backref="work_logs")
    #transaction = db.relationship("Transaction", backref="work_logs")
    #payrolls = db.relationship("Payroll", backref="worklog", lazy=True)

    def calculate_due_payment(self):
        if self.work_type:
            return self.work_units * self.work_type.rate
        return 0.0

class SupplyType(db.Model):
    __tablename__ = "supply_type"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("supply_type.id", name="fk_supplytype_parent"),
        nullable=True
    )
    parent = db.relationship("SupplyType", remote_side=[id], backref="children")

    def __repr__(self):
        return f"<SupplyType {self.name}>"

class SupplyLog(db.Model):
    __tablename__ = "supply_log"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)

    supplier_id = db.Column(db.Integer, db.ForeignKey("relationship.id"), nullable=False)
    supplier = db.relationship("Relationship", backref="supply_logs")

    supply_type_id = db.Column(db.Integer, db.ForeignKey("supply_type.id"), nullable=False)
    supply_type = db.relationship("SupplyType", backref="supply_logs")

    unit_price = db.Column(db.Float, nullable=False)
    units = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Many-to-one: each SupplyLog belongs to one SupplyPayment
    payment_id = db.Column(db.Integer, db.ForeignKey("supply_payment.id"), nullable=True)
    payment = db.relationship("SupplyPayment", back_populates="supply_logs")


class SupplyPayment(db.Model):
    __tablename__ = "supply_payment"

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transaction.id"), nullable=False)

    transaction = db.relationship("Transaction", backref="supply_payment")

    # One payment can cover multiple supply logs
    supply_logs = db.relationship("SupplyLog", back_populates="payment")




class Payroll(db.Model):
    __tablename__ = "payroll"

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transaction.id"), nullable=False)
    worklog_id = db.Column(db.Integer, db.ForeignKey("work_log.id"), nullable=False)

    transaction = db.relationship("Transaction", backref="payroll_entries")
    worklog = db.relationship("WorkLog", backref="payroll_entries")


@app.route("/")
def home():
    return render_template("index.html", title="Home")

@app.route("/entities")
def entities():
    all_entities = Entity.query.all()
    return render_template("entities.html", title="Entities", entities=all_entities)

@app.route("/add_entity", methods=["POST"])
def add_entity():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form.get('address')  # New field
    new_entity = Entity(name=name, email=email, phone=phone, address=address)
    db.session.add(new_entity)
    db.session.commit()
    return redirect(url_for('entities'))

@app.route("/entity_info/<int:entity_id>")
def entity_info(entity_id):
    entity = Entity.query.get_or_404(entity_id)

    # Get all relationships for this entity
    relationships = Relationship.query.filter_by(entity_id=entity_id).all()

    # Organize by relationship type
    data = []
    for rel in relationships:
        rel_type = RelationshipType.query.get(rel.relationship_type_id)
        
        # Get transactions for this relationship
        transactions = Transaction.query.filter_by(relationship_id=rel.id).all()

        # Summarize transactions (e.g., total amount)
        total_amount = sum(t.amount for t in transactions)

        worklogs = []
        if rel_type.name.lower() == "employee":
            worklogs = WorkLog.query.filter_by(relationship_id=rel.id).all()

        data.append({
            "relationship_type": rel_type,
            "transactions": transactions,
            "total_amount": total_amount,
            "worklogs": worklogs
        })

    return render_template(
        "entity_info.html",
        entity=entity,
        data=data,
        title=f"Entity Info - {entity.name}"
    )


@app.route("/delete_entity/<int:entity_id>", methods=["POST"])
def delete_entity(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    # Count relationships linked to this entity
    rel_count = Relationship.query.filter_by(entity_id=entity_id).count()
    if rel_count > 0:
        return jsonify({"status": "warning", "count": rel_count})
    
    # No relationships, safe to delete
    db.session.delete(entity)
    db.session.commit()
    return jsonify({"status": "deleted"})

@app.route("/force_delete_entity/<int:entity_id>", methods=["POST"])
def force_delete_entity(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    # Delete all relationships linked to this entity
    Relationship.query.filter_by(entity_id=entity_id).delete()
    db.session.delete(entity)
    db.session.commit()
    return "", 204

@app.route("/transaction_types")
def transaction_types():
    all_types = TransactionType.query.all()
    return render_template(
        "transaction_types.html", 
        title="Transaction Types", 
        types=all_types
    )

@app.route("/add_transaction_type", methods=["POST"])
def add_transaction_type():
    name = request.form['name']
    description = request.form.get('description')
    new_type = TransactionType(name=name, description=description)
    db.session.add(new_type)
    db.session.commit()
    return redirect(url_for('transaction_types'))


@app.route("/transactions")
def transactions():
    all_transactions = Transaction.query.all()
    transaction_types = TransactionType.query.all()
    relationships = Relationship.query.all()
    return render_template(
        "transactions.html",
        title="Transactions",
        transactions=all_transactions,
        transaction_types=transaction_types,
        relationships=relationships,
        datetime=datetime
    )

#@app.route("/add_transaction", methods=["POST"])
#def add_transaction():
#    transaction_type_id = request.form['transaction_type_id']
#    relationship_id = request.form['relationship_id']
#    amount = float(request.form['amount'])
#    date = request.form['date']
#    description = request.form.get('description')
#
#    new_transaction = Transaction(
#        transaction_type_id=transaction_type_id,
#        relationship_id=relationship_id,
#        amount=amount,
#        date=date,
#        description=description
#    )
#    db.session.add(new_transaction)
#    db.session.commit()
#    return redirect(url_for('transactions'))

@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    transaction_type_id = int(request.form['transaction_type_id'])
    relationship_id = int(request.form['relationship_id'])
    description = request.form.get('description', "")
    date = datetime.utcnow()

    transaction_type = TransactionType.query.get(transaction_type_id)

    # --- Payroll case ---
    if transaction_type.name == "Payroll":
        selected_ids = request.form.getlist("worklogs")  # list of IDs
        selected_logs = WorkLog.query.filter(WorkLog.id.in_(selected_ids)).all()
        amount = sum(log.due_payment for log in selected_logs)

        transaction = Transaction(
            transaction_type_id=transaction_type.id,
            relationship_id=relationship_id,
            amount=amount,
            date=date,
            description=description
        )
        db.session.add(transaction)
        db.session.flush()  # so transaction.id is available

        for log in selected_logs:
            payroll_entry = Payroll(
                transaction_id=transaction.id,
                worklog_id=log.id
            )
            db.session.add(payroll_entry)
            log.is_paid = True
            log.transaction_id = transaction.id

    # --- Other transaction types ---
    else:
        amount = float(request.form['amount'])
        transaction = Transaction(
            transaction_type_id=transaction_type.id,
            relationship_id=relationship_id,
            amount=amount,
            date=date,
            description=description
        )
        db.session.add(transaction)

    db.session.commit()
    return redirect(url_for('transactions'))





@app.route("/relationship_types")
def relationship_types():
    all_types = RelationshipType.query.all()
    return render_template("relationship_types.html", title="Relationship Types", types=all_types)

@app.route("/add_relationship_type", methods=["POST"])
def add_relationship_type():
    name = request.form['name']
    description = request.form.get('description')
    new_type = RelationshipType(name=name, description=description)
    db.session.add(new_type)
    db.session.commit()
    return redirect(url_for('relationship_types'))

@app.route("/relationships")
def relationships():
    all_relationships = Relationship.query.all()
    entities = Entity.query.all()   # <-- this must fetch all entities
    types = RelationshipType.query.all()
    return render_template(
        "relationships.html", 
        title="Relationships", 
        relationships=all_relationships,
        entities=entities,
        types=types
    )


@app.route("/add_relationship", methods=["POST"])
def add_relationship():
    entity_id = request.form['entity_id']
    relationship_type_id = request.form['relationship_type_id']

    new_rel = Relationship(
        entity_id=entity_id,
        relationship_type_id=relationship_type_id
    )
    db.session.add(new_rel)
    db.session.commit()
    return redirect(url_for('relationships'))

@app.route("/delete_relationship_type/<int:type_id>", methods=["POST"])
def delete_relationship_type(type_id):
    r_type = RelationshipType.query.get_or_404(type_id)
    # Count relationships using this type
    rel_count = Relationship.query.filter_by(relationship_type_id=type_id).count()
    if rel_count > 0:
        return jsonify({"status": "warning", "count": rel_count})
    
    # No relationships, safe to delete
    db.session.delete(r_type)
    db.session.commit()
    return jsonify({"status": "deleted"})

@app.route("/force_delete_relationship_type/<int:type_id>", methods=["POST"])
def force_delete_relationship_type(type_id):
    r_type = RelationshipType.query.get_or_404(type_id)
    # Delete all relationships with this type first
    Relationship.query.filter_by(relationship_type_id=type_id).delete()
    db.session.delete(r_type)
    db.session.commit()
    return "", 204

#@app.route("/dashboard")
#def dashboard():
#    # Get count of entities per relationship type
#    summary = db.session.query(
#        RelationshipType.id,
#        RelationshipType.name,
#        func.count(Relationship.id)
#    ).outerjoin(Relationship).group_by(RelationshipType.id).all()
#
#    # Pass (name, count, id) to template
#    summary_list = [(name, count, type_id) for type_id, name, count in summary]
#    return render_template("dashboard.html", title="Dashboard", summary=summary_list)

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    # defaults
    start_date = end_date = date.today()

    if request.method == "POST":
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        # convert from string
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    # --- Transaction Summary ---
    transaction_summary = (
        db.session.query(
            TransactionType.name,
            db.func.sum(Transaction.amount)
        )
        .join(TransactionType, Transaction.transaction_type_id == TransactionType.id)
        .filter(Transaction.date >= start_date, Transaction.date <= end_date)
        .group_by(TransactionType.name)
        .all()
    )

    # --- Relationship Summary (already in your app) ---
    rel_summary = (
        db.session.query(RelationshipType.name, db.func.count(Relationship.id))
        .join(RelationshipType, Relationship.relationship_type_id == RelationshipType.id)
        .group_by(RelationshipType.name)
        .all()
    )

    rel_summary = (
        db.session.query(
            RelationshipType.id,
            RelationshipType.name,
            db.func.count(Relationship.id)
        )
        .outerjoin(Relationship, Relationship.relationship_type_id == RelationshipType.id)
        .group_by(RelationshipType.id, RelationshipType.name)
        .all()
    )

    # Convert to dicts for clarity
    summary_data = [
        {"id": r[0], "name": r[1], "count": r[2]} for r in rel_summary
    ]

    return render_template(
        "dashboard.html",
        title="Dashboard",
        summary=summary_data,
        transaction_summary=transaction_summary,
        start_date=start_date,
        end_date=end_date,
    )


@app.route("/entities_by_relationship/<int:type_id>")
def entities_by_relationship(type_id):
    r_type = RelationshipType.query.get_or_404(type_id)
    entities = Entity.query.join(Relationship).filter(Relationship.relationship_type_id == type_id).all()
    return render_template(
        "entities_by_relationship.html",
        title=f"Entities - {r_type.name}",
        relationship_type=r_type,
        entities=entities
    )

@app.route("/worktypes", methods=["GET", "POST"])
def worktypes():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        pay_type = request.form["pay_type"]
        rate = float(request.form["rate"])
        wt = WorkType(name=name, description=description, pay_type=pay_type, rate=rate)
        db.session.add(wt)
        db.session.commit()
        return redirect(url_for("worktypes"))
    worktypes = WorkType.query.all()
    return render_template("worktypes.html", title="Work Types", worktypes=worktypes)



@app.route("/worktypes/delete/<int:wt_id>", methods=["POST"])
def delete_worktype(wt_id):
    wt = WorkType.query.get_or_404(wt_id)
    db.session.delete(wt)
    db.session.commit()
    return redirect(url_for("worktypes"))

@app.route("/api/unpaid_worklogs/<int:relationship_id>")
def api_unpaid_worklogs(relationship_id):
    logs = WorkLog.query.filter_by(relationship_id=relationship_id, is_paid=False).all()
    return jsonify([{
        "id": log.id,
        "start_date": log.start_date.strftime("%Y-%m-%d"),
        "end_date": log.end_date.strftime("%Y-%m-%d"),
        "due_payment": log.due_payment
    } for log in logs])


@app.route('/worklogs', methods=['GET', 'POST'])
def worklogs():
    work_types = WorkType.query.all()
    current_date = datetime.today().strftime("%Y-%m-%d")
    employee_type = RelationshipType.query.filter_by(name="Employee").first()
    employees = Relationship.query.filter_by(relationship_type_id=employee_type.id).all() if employee_type else []

    if request.method == 'POST':
        work_type_id = request.form['work_type_id']
        work_units = float(request.form['work_units'])

        # Convert input strings to Python date objects
        start_date = datetime.strptime(request.form['start_date'], "%Y-%m-%d").date()
        end_date = datetime.strptime(request.form['end_date'], "%Y-%m-%d").date()

        work_type = WorkType.query.get(work_type_id)
        relationship_id = int(request.form['relationship_id'])

        # Calculate due payment
        due_payment = work_type.rate * work_units

        description = request.form.get("description", "")

        new_log = WorkLog(
            start_date=start_date,
            end_date=end_date,
            work_type_id=work_type_id,
            relationship_id=relationship_id,
            work_units=work_units,
            due_payment=due_payment,
            description=description
        )
        db.session.add(new_log)
        db.session.commit()
        return redirect(url_for('worklogs'))

    logs = WorkLog.query.all()
    return render_template('worklogs.html', work_types=work_types,employees=employees, logs=logs, current_date=current_date)

@app.route("/supply_types", methods=["GET", "POST"])
def supply_types():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        parent_id = request.form.get("parent_id")

        existing = SupplyType.query.filter_by(name=name).first()
        if existing:
            supply_types = SupplyType.query.all()
            return render_template(
                "supply_types.html",
                supply_types=supply_types,
                error="Supply Type with this name already exists!"
            )
        else:
            supply_type = SupplyType(
                name=name,
                description=description,
                parent_id=parent_id if parent_id else None
            )
            db.session.add(supply_type)
            db.session.commit()
            return redirect(url_for("supply_types"))

    supply_types = SupplyType.query.all()
    return render_template("supply_types.html", supply_types=supply_types)

@app.route("/supply_logs")
def supply_logs():
    logs = SupplyLog.query.all()
    return render_template("supply_logs.html", logs=logs, title="Supply Logs")

@app.route("/supply_logs/add", methods=["GET", "POST"])
def add_supply_log():
    suppliers = Relationship.query.filter_by(
        relationship_type_id=RelationshipType.query.filter_by(name="Supplier").first().id
    ).all()
    supply_types = SupplyType.query.all()

    if request.method == "POST":
        date = request.form["date"]
        supplier_id = request.form["supplier_id"]
        supply_type_id = request.form["supply_type"]
        unit_price = float(request.form["unit_price"])
        units = float(request.form["units"])
        amount = unit_price * units
        description = request.form.get("description")
        is_paid = "is_paid" in request.form  # checkbox

        log = SupplyLog(
            date=datetime.strptime(date, "%Y-%m-%d"),
            supplier_id=supplier_id,
            supply_type_id=supply_type_id,
            unit_price=unit_price,
            units=units,
            amount=amount,
            description=description
        )

        if is_paid:
            # 1. Find transaction type "Supply Payments"
            tx_type = TransactionType.query.filter_by(name="Supply Payments").first()

            # 2. Create Transaction
            transaction = Transaction(
                date=datetime.strptime(date, "%Y-%m-%d"),
                transaction_type_id=tx_type.id,
                relationship_id=supplier_id,
                amount=amount,
                description=f"Supply payment for {units} units @ {unit_price} (Supplier {supplier_id})"
            )

            # 3. Create SupplyPayment
            supply_payment = SupplyPayment(transaction=transaction)

            # 4. Link SupplyLog to SupplyPayment
            log.payment = supply_payment

            db.session.add(transaction)
            db.session.add(supply_payment)

        db.session.add(log)
        db.session.commit()
        return redirect(url_for("supply_logs"))

    return render_template(
        "add_supply_log.html",
        suppliers=suppliers,
        supply_types=supply_types,
        title="Add Supply Log"
    )


@app.before_first_request
def create_default_relationship_types():
    defaults = [
        {"name": "Employee", "description": "Person working for the business"},
        {"name": "Customer", "description": "Person or organization buying products/services"},
        {"name": "Supplier", "description": "Entity providing goods/services to the business"},
    ]
    for item in defaults:
        exists = RelationshipType.query.filter_by(name=item["name"]).first()
        if not exists:
            db.session.add(RelationshipType(**item))
    db.session.commit()

@app.before_first_request
def create_default_worktypes():
    defaults = [
        {"name": "Excavator Operator", "description": "Operates excavators", "pay_type": "Hourly", "rate": 500},
        {"name": "Labour", "description": "General plantation labour", "pay_type": "Daily", "rate": 2000},
        {"name": "Mason", "description": "Handles construction work", "pay_type": "Daily", "rate": 2500},
    ]
    for item in defaults:
        exists = WorkType.query.filter_by(name=item["name"]).first()
        if not exists:
            db.session.add(WorkType(**item))
    db.session.commit()


@app.before_first_request
def create_default_transactiontypes():
    predefined_types = [
        {"name": "Payroll", "description": "Payments for employee work logs"},
        {"name": "Supply Payments", "description" : "Payments for supplier done for supply log entries"}
    ]

    for t in predefined_types:
        existing = TransactionType.query.filter_by(name=t["name"]).first()
        if not existing:
            new_type = TransactionType(name=t["name"], description=t["description"])
            db.session.add(new_type)
    db.session.commit()


#@event.listens_for(WorkLog, "before_insert")
#@event.listens_for(WorkLog, "before_update")
#def set_due_payment(mapper, connection, target):
#    target.due_payment = target.calculate_due_payment()
#    print("calculated due payement : ", target.due_payment)




if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

