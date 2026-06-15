from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.user import User
from models.product import Product
from models.supplier import Supplier
from models.invoice import Invoice, InvoiceItem
from models.ejournal import EJournalEntry, XReading, ZReading
from models.audit_log import AuditLog
